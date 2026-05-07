"""Unit tests for the application DTOs.

DTOs are intentionally simple — frozen, slotted, shape-only — so the
contract pinned here is correspondingly small: required fields are
present, identity strings are non-empty, instances are immutable.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ignorantia.application.dtos import (
    ReferenceInputDto,
    RenderManuscriptCommand,
    RenderManuscriptResult,
    RunAuditCommand,
    RunAuditResult,
    SectionInputDto,
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
