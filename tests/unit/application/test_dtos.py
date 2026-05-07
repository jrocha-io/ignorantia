"""Unit tests for the application DTOs.

DTOs are intentionally simple — frozen, slotted, shape-only — so the
contract pinned here is correspondingly small: required fields are
present, identity strings are non-empty, instances are immutable.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ignorantia.application.dtos import (
    FinalizePipelineCommand,
    FinalizePipelineResult,
    RunAuditCommand,
    RunAuditResult,
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
