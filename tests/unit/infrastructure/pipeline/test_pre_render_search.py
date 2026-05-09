"""Unit tests for :func:`build_pre_render_search_step`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ignorantia.application.dtos import SearchForStudiesCommand
from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import StepStatus
from ignorantia.domain.search.entities import (
    FetchedItem,
    SearchQuery,
    SearchResult,
)
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.services.search_orchestrator import SearchOrchestrator
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.pipeline.pre_render_search import (
    build_pre_render_search_step,
)

# ----------------------------------------------------------------------
# Stubs (mirror the patterns in tests/unit/application/.../test_search_for_studies.py)
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
                    _item("Paper A", doi="10.1/a"),
                    _item("Paper B", doi="10.1/b"),
                ),
            ),
        }
    )
    return SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


class TestBuildPreRenderSearchStep:
    def test_step_metadata(self, use_case: SearchForStudiesUseCase, tmp_path: Path) -> None:
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="x", source_ids=("arxiv",))],
            output_dir=tmp_path,
        )
        assert step.name == "pre_render_search"
        assert "Phase 3" in step.label

    def test_empty_commands_rejected(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="at least one"):
            build_pre_render_search_step(use_case=use_case, commands=[], output_dir=tmp_path)


class TestStepExecution:
    def test_writes_searches_json(self, use_case: SearchForStudiesUseCase, tmp_path: Path) -> None:
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="q", source_ids=("arxiv",))],
            output_dir=tmp_path,
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        target = tmp_path / "searches.json"
        assert target.is_file()
        body = json.loads(target.read_text(encoding="utf-8"))
        assert "per_source" in body
        assert "deduplicated_items" in body

    def test_artifact_path_is_returned(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="q", source_ids=("arxiv",))],
            output_dir=tmp_path,
        )
        result = step.fn()
        assert result.artifact == str(tmp_path / "searches.json")

    def test_creates_output_dir_if_missing(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        nested = tmp_path / "nested" / "deeper"
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="q", source_ids=("arxiv",))],
            output_dir=nested,
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert (nested / "searches.json").is_file()

    def test_custom_filename(self, use_case: SearchForStudiesUseCase, tmp_path: Path) -> None:
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="q", source_ids=("arxiv",))],
            output_dir=tmp_path,
            filename="phase3-corpus.json",
        )
        result = step.fn()
        assert (tmp_path / "phase3-corpus.json").is_file()
        assert (tmp_path / "searches.json").exists() is False
        assert result.artifact == str(tmp_path / "phase3-corpus.json")


class TestMultipleCommands:
    def test_multiple_queries_merge_per_source(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[
                SearchForStudiesCommand(text="q1", source_ids=("arxiv",)),
                SearchForStudiesCommand(text="q2", source_ids=("openalex",)),
            ],
            output_dir=tmp_path,
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        body = json.loads((tmp_path / "searches.json").read_text(encoding="utf-8"))
        # Two queries → two SearchResult per_source entries (one per
        # query, one source each).
        assert len(body["per_source"]) == 2
        sources = {entry["source"] for entry in body["per_source"]}
        assert sources == {"arxiv", "openalex"}

    def test_cross_query_dedup_collapses_repeated_titles(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        # arxiv returns Paper A; openalex returns Paper A + Paper B.
        # Two queries that hit both sources produce 4 raw items (2+2)
        # → 2 unique titles after cross-query dedup.
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[
                SearchForStudiesCommand(text="q1", source_ids=("arxiv", "openalex")),
                SearchForStudiesCommand(text="q2", source_ids=("arxiv", "openalex")),
            ],
            output_dir=tmp_path,
        )
        result = step.fn()
        body = json.loads((tmp_path / "searches.json").read_text(encoding="utf-8"))
        titles = {item["title"] for item in body["deduplicated_items"]}
        assert titles == {"Paper A", "Paper B"}
        # Message reports cross-query dedup count.
        assert "after cross-query dedup" in result.message


class TestStepUnderExecutor:
    def test_executor_runs_step_and_returns_artifact(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="q", source_ids=("arxiv",))],
            output_dir=tmp_path,
        )
        clock_values = iter(["t1", "t2"])
        executor = PipelineExecutor(clock=lambda: next(clock_values))
        run = executor.run([step])
        assert run.is_successful is True
        assert run.n_ok == 1
        assert run.final_artifacts == (str(tmp_path / "searches.json"),)


class TestSchemaValidation:
    def test_output_validates_against_search_full_result_schema(
        self, use_case: SearchForStudiesUseCase, tmp_path: Path
    ) -> None:
        # JsonWriter validates before writing — so a successful step
        # implies the payload matched search_full_result.schema.json.
        # Confirm by re-validating the on-disk content explicitly.
        from ignorantia.interface.manifests import validate_manifest

        step = build_pre_render_search_step(
            use_case=use_case,
            commands=[SearchForStudiesCommand(text="q", source_ids=("arxiv",))],
            output_dir=tmp_path,
        )
        step.fn()
        body = json.loads((tmp_path / "searches.json").read_text(encoding="utf-8"))
        validate_manifest("search_full_result", body)  # raises on failure
