"""Unit tests for the ``search`` CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError

import pytest
from click.testing import CliRunner

from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.domain.search.entities import (
    FetchedItem,
    SearchQuery,
    SearchResult,
)
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.services.search_orchestrator import (
    SearchOrchestrator,
)
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.interface.cli.main import (
    build_search_for_studies_use_case,
    cli,
)

# ----------------------------------------------------------------------
# Stub adapters + factory (mirrors the use-case unit tests)
# ----------------------------------------------------------------------


class _StubAdapter(AdapterPort):
    def __init__(
        self,
        *,
        source_id: str,
        items: tuple[FetchedItem, ...],
        tier: Tier = Tier.TIER1,
    ) -> None:
        self._source_id = source_id
        self._items = items
        self._tier = tier

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_tier(self) -> Tier:
        return self._tier

    def fetch(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            source=self._source_id,
            source_tier=self._tier,
            method=Method.MOCK,
            query=query,
            items=self._items,
        )


class _ErroringAdapter(AdapterPort):
    @property
    def source_id(self) -> str:
        return "broken"

    @property
    def source_tier(self) -> Tier:
        return Tier.TIER1

    def fetch(self, query: SearchQuery) -> SearchResult:
        raise URLError("boom")


class _StubFactory(AdapterFactoryPort):
    def __init__(self, adapters: dict[str, AdapterPort]) -> None:
        self._adapters = adapters

    def create(self, source_id: str) -> AdapterPort:
        return self._adapters[source_id]


def _item(title: str, **kwargs: object) -> FetchedItem:
    base: dict[str, object] = {"title": title, "source_tier": Tier.TIER1}
    base.update(kwargs)
    return FetchedItem(**base)  # type: ignore[arg-type]


@pytest.fixture
def use_case() -> SearchForStudiesUseCase:
    factory = _StubFactory(
        {
            "arxiv": _StubAdapter(
                source_id="arxiv",
                items=(_item("Paper A", doi="10.1/a"),),
            ),
            "openalex": _StubAdapter(
                source_id="openalex",
                items=(
                    _item("Paper A", doi="10.1/a"),  # duplicate of arxiv
                    _item("Paper B", doi="10.1/b"),
                ),
            ),
            "broken": _ErroringAdapter(),
        }
    )
    return SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))


@pytest.fixture
def obj(use_case: SearchForStudiesUseCase) -> dict[str, SearchForStudiesUseCase]:
    return {"search_use_case": use_case}


class TestSearchSubcommandHelp:
    def test_help_documents_all_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        options = (
            "--text",
            "--source",
            "--year-start",
            "--year-end",
            "--language",
            "--output",
        )
        for option in options:
            assert option in result.output


class TestSearchSubcommandHappyPath:
    def test_emits_summary_json(self, obj: dict[str, SearchForStudiesUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["search", "--text", "q", "--source", "arxiv", "--source", "openalex"],
            obj=obj,
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["n_sources_ok"] == 2
        assert parsed["n_sources_errored"] == 0
        assert parsed["n_items_total"] == 3
        assert parsed["n_items_deduplicated"] == 2
        # per_source order matches command order.
        assert [s["source"] for s in parsed["per_source_status"]] == [
            "arxiv",
            "openalex",
        ]


class TestSearchSubcommandRequiredArguments:
    def test_text_is_required(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--source", "arxiv"])
        assert result.exit_code != 0
        assert "--text" in result.output

    def test_at_least_one_source_is_required(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--text", "q"])
        assert result.exit_code != 0
        assert "--source" in result.output


class TestSearchSubcommandResilience:
    def test_network_error_propagates_as_real_error(
        self, obj: dict[str, SearchForStudiesUseCase]
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["search", "--text", "q", "--source", "arxiv", "--source", "broken"],
            obj=obj,
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["n_sources_ok"] == 1
        assert parsed["n_sources_errored"] == 1
        per = {s["source"]: s for s in parsed["per_source_status"]}
        assert per["broken"]["method"] == "real_error"


class TestSearchSubcommandOutputFile:
    def test_writes_full_payload_to_output_path(
        self,
        obj: dict[str, SearchForStudiesUseCase],
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "results.json"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "search",
                "--text",
                "q",
                "--source",
                "arxiv",
                "--source",
                "openalex",
                "--output",
                str(out),
            ],
            obj=obj,
        )
        assert result.exit_code == 0
        assert out.exists()
        body = json.loads(out.read_text(encoding="utf-8"))
        assert "per_source" in body
        assert "deduplicated_items" in body
        # 2 unique titles after dedup.
        assert {i["title"] for i in body["deduplicated_items"]} == {
            "Paper A",
            "Paper B",
        }


class TestSearchSubcommandQueryTranslation:
    def test_year_window_and_languages_propagate(self) -> None:
        captured: list[SearchQuery] = []

        class _CapturingAdapter(AdapterPort):
            @property
            def source_id(self) -> str:
                return "capture"

            @property
            def source_tier(self) -> Tier:
                return Tier.TIER1

            def fetch(self, query: SearchQuery) -> SearchResult:
                captured.append(query)
                return SearchResult(
                    source="capture",
                    source_tier=Tier.TIER1,
                    method=Method.MOCK,
                    query=query,
                    items=(),
                )

        factory = _StubFactory({"capture": _CapturingAdapter()})
        use_case = SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "search",
                "--text",
                "q",
                "--source",
                "capture",
                "--year-start",
                "2020",
                "--year-end",
                "2024",
                "--language",
                "en",
                "--language",
                "pt",
            ],
            obj={"search_use_case": use_case},
        )
        assert result.exit_code == 0
        assert captured[0].text == "q"
        assert captured[0].year_start == 2020
        assert captured[0].year_end == 2024
        assert captured[0].languages == ("en", "pt")


class TestSearchCompositionRoot:
    def test_build_search_for_studies_use_case_returns_real_instance(self) -> None:
        use_case = build_search_for_studies_use_case()
        assert isinstance(use_case, SearchForStudiesUseCase)
