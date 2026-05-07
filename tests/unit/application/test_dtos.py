"""Unit tests for the application DTOs.

DTOs are intentionally simple — frozen, slotted, shape-only — so the
contract pinned here is correspondingly small: required fields are
present, identity strings are non-empty, instances are immutable.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ignorantia.application.dtos import (
    FetchedItemDto,
    FinalizePipelineCommand,
    FinalizePipelineResult,
    ReferenceInputDto,
    RenderManuscriptCommand,
    RenderManuscriptResult,
    RunAuditCommand,
    RunAuditResult,
    SearchForStudiesCommand,
    SearchForStudiesResult,
    SearchSourceResultDto,
    SectionInputDto,
    StepResultDto,
)


class TestRunAuditCommand:
    def test_minimum_construction(self) -> None:
        cmd = RunAuditCommand(action="search.run", actor="cli")
        assert cmd.action == "search.run"
        assert cmd.actor == "cli"
        # Default payload is an empty mapping.
        assert cmd.payload == {}

    def test_with_payload(self) -> None:
        cmd = RunAuditCommand(
            action="search.run",
            actor="cli",
            payload={"n_results": 42},
        )
        assert cmd.payload["n_results"] == 42

    def test_action_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="action"):
            RunAuditCommand(action="", actor="cli")

    def test_actor_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="actor"):
            RunAuditCommand(action="x", actor="")

    def test_is_frozen(self) -> None:
        cmd = RunAuditCommand(action="x", actor="y")
        with pytest.raises(FrozenInstanceError):
            cmd.action = "z"  # type: ignore[misc]

    def test_payload_is_separate_object_per_instance(self) -> None:
        a = RunAuditCommand(action="x", actor="y")
        b = RunAuditCommand(action="x", actor="y")
        assert a.payload is not b.payload


class TestRunAuditResult:
    def test_construction(self) -> None:
        r = RunAuditResult(
            timestamp_iso8601="2026-05-07T12:00:00Z",
            action="search.run",
            manifest_size=1,
        )
        assert r.timestamp_iso8601 == "2026-05-07T12:00:00Z"
        assert r.action == "search.run"
        assert r.manifest_size == 1

    def test_is_frozen(self) -> None:
        r = RunAuditResult(timestamp_iso8601="t", action="a", manifest_size=0)
        with pytest.raises(FrozenInstanceError):
            r.action = "b"  # type: ignore[misc]


class TestStepResultDto:
    def test_minimum_construction(self) -> None:
        d = StepResultDto(name="render_html", status="ok")
        assert d.name == "render_html"
        assert d.status == "ok"
        assert d.message == ""
        assert d.artifact is None

    def test_with_message_and_artifact(self) -> None:
        d = StepResultDto(
            name="render_html",
            status="ok",
            message="Rendered 12 sections",
            artifact="output/manuscript.html",
        )
        assert d.message.startswith("Rendered")
        assert d.artifact == "output/manuscript.html"

    def test_is_frozen(self) -> None:
        d = StepResultDto(name="x", status="ok")
        with pytest.raises(FrozenInstanceError):
            d.name = "y"  # type: ignore[misc]


class TestFinalizePipelineCommand:
    def test_construction(self) -> None:
        cmd = FinalizePipelineCommand(actor="cli")
        assert cmd.actor == "cli"

    def test_actor_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="actor"):
            FinalizePipelineCommand(actor="")

    def test_is_frozen(self) -> None:
        cmd = FinalizePipelineCommand(actor="cli")
        with pytest.raises(FrozenInstanceError):
            cmd.actor = "engine"  # type: ignore[misc]


class TestFinalizePipelineResult:
    def test_construction(self) -> None:
        r = FinalizePipelineResult(
            started_at_iso8601="2026-05-07T12:00:00Z",
            finished_at_iso8601="2026-05-07T12:00:05Z",
            steps=(StepResultDto(name="a", status="ok"),),
            n_ok=1,
            n_skipped=0,
            n_errors=0,
            final_artifacts=(),
            is_successful=True,
        )
        assert r.is_successful is True
        assert r.n_ok == 1
        assert r.steps[0].name == "a"

    def test_is_frozen(self) -> None:
        r = FinalizePipelineResult(
            started_at_iso8601="t",
            finished_at_iso8601="t",
            steps=(),
            n_ok=0,
            n_skipped=0,
            n_errors=0,
            final_artifacts=(),
            is_successful=True,
        )
        with pytest.raises(FrozenInstanceError):
            r.n_ok = 1  # type: ignore[misc]


class TestSectionInputDto:
    def test_construction(self) -> None:
        s = SectionInputDto(id="intro", title="Introduction", body_md="x")
        assert s.id == "intro"
        assert s.title == "Introduction"
        assert s.body_md == "x"

    def test_is_frozen(self) -> None:
        s = SectionInputDto(id="x", title="X", body_md="x")
        with pytest.raises(FrozenInstanceError):
            s.id = "y"  # type: ignore[misc]


class TestReferenceInputDto:
    def test_minimum_construction(self) -> None:
        r = ReferenceInputDto(type="article", title="A", authors=("Silva, J.",))
        assert r.type == "article"
        assert r.year is None
        assert r.language == "en"

    def test_full_construction(self) -> None:
        r = ReferenceInputDto(
            type="article",
            title="A",
            authors=("Silva, J.",),
            year=2024,
            venue="Journal",
            volume="10",
            doi="10.1234/x",
        )
        assert r.year == 2024
        assert r.venue == "Journal"


class TestRenderManuscriptCommand:
    def test_minimum_construction(self) -> None:
        cmd = RenderManuscriptCommand(title="My SLR")
        assert cmd.title == "My SLR"
        assert cmd.abstract == ""
        assert cmd.language == "en"
        assert cmd.keywords == ()
        assert cmd.sections == ()
        assert cmd.references == ()

    def test_with_sections_and_references(self) -> None:
        cmd = RenderManuscriptCommand(
            title="My SLR",
            abstract="Short abstract.",
            sections=(SectionInputDto(id="i", title="I", body_md="b"),),
            references=(ReferenceInputDto(type="article", title="A", authors=("X",)),),
        )
        assert len(cmd.sections) == 1
        assert len(cmd.references) == 1

    def test_title_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="title"):
            RenderManuscriptCommand(title="")

    def test_is_frozen(self) -> None:
        cmd = RenderManuscriptCommand(title="x")
        with pytest.raises(FrozenInstanceError):
            cmd.title = "y"  # type: ignore[misc]


class TestRenderManuscriptResult:
    def test_construction(self) -> None:
        r = RenderManuscriptResult(
            output_format="html",
            artifact_bytes=b"<html></html>",
            byte_size=13,
        )
        assert r.output_format == "html"
        assert r.byte_size == 13

    def test_is_frozen(self) -> None:
        r = RenderManuscriptResult(output_format="html", artifact_bytes=b"", byte_size=0)
        with pytest.raises(FrozenInstanceError):
            r.byte_size = 1  # type: ignore[misc]


class TestFetchedItemDto:
    def test_minimum_construction(self) -> None:
        item = FetchedItemDto(title="A paper", source_tier="tier1")
        assert item.title == "A paper"
        assert item.source_tier == "tier1"
        assert item.authors == ()
        assert item.year is None
        assert item.is_oa is False
        assert item.language == "en"

    def test_full_construction(self) -> None:
        item = FetchedItemDto(
            title="A paper",
            source_tier="tier1",
            authors=("Silva, J.",),
            year=2024,
            doi="10.1234/x",
            venue="Journal",
            is_oa=True,
            url="https://example.org/paper",
        )
        assert item.year == 2024
        assert item.is_oa is True

    def test_is_frozen(self) -> None:
        item = FetchedItemDto(title="A", source_tier="tier1")
        with pytest.raises(FrozenInstanceError):
            item.title = "B"  # type: ignore[misc]


class TestSearchSourceResultDto:
    def test_construction(self) -> None:
        dto = SearchSourceResultDto(
            source="arxiv",
            source_tier="tier1",
            method="real",
            items=(FetchedItemDto(title="A", source_tier="tier1"),),
            total_results=1,
        )
        assert dto.source == "arxiv"
        assert dto.method == "real"
        assert dto.total_results == 1


class TestSearchForStudiesCommand:
    def test_minimum_construction(self) -> None:
        cmd = SearchForStudiesCommand(text="quantum computing", source_ids=("arxiv",))
        assert cmd.text == "quantum computing"
        assert cmd.source_ids == ("arxiv",)
        assert cmd.year_start is None
        assert cmd.year_end is None
        assert cmd.languages == ()

    def test_with_year_window_and_languages(self) -> None:
        cmd = SearchForStudiesCommand(
            text="x",
            source_ids=("arxiv", "openalex"),
            year_start=2020,
            year_end=2025,
            languages=("en", "pt"),
        )
        assert cmd.year_start == 2020
        assert cmd.year_end == 2025
        assert cmd.languages == ("en", "pt")

    def test_text_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="text"):
            SearchForStudiesCommand(text="", source_ids=("arxiv",))

    def test_source_ids_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="source_ids"):
            SearchForStudiesCommand(text="q", source_ids=())

    def test_is_frozen(self) -> None:
        cmd = SearchForStudiesCommand(text="x", source_ids=("y",))
        with pytest.raises(FrozenInstanceError):
            cmd.text = "z"  # type: ignore[misc]


class TestSearchForStudiesResult:
    def test_construction(self) -> None:
        r = SearchForStudiesResult(
            per_source=(),
            deduplicated_items=(),
            n_sources_ok=0,
            n_sources_errored=0,
            n_items_total=0,
            n_items_deduplicated=0,
        )
        assert r.per_source == ()
        assert r.deduplicated_items == ()

    def test_is_frozen(self) -> None:
        r = SearchForStudiesResult(
            per_source=(),
            deduplicated_items=(),
            n_sources_ok=0,
            n_sources_errored=0,
            n_items_total=0,
            n_items_deduplicated=0,
        )
        with pytest.raises(FrozenInstanceError):
            r.n_sources_ok = 1  # type: ignore[misc]
