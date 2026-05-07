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
    RunAuditCommand,
    RunAuditResult,
    SearchForStudiesCommand,
    SearchForStudiesResult,
    SearchSourceResultDto,
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
