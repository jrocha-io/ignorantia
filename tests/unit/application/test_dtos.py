"""Unit tests for the application DTOs.

DTOs are intentionally simple — frozen, slotted, shape-only — so the
contract pinned here is correspondingly small: required fields are
present, identity strings are non-empty, instances are immutable.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ignorantia.application.dtos import RunAuditCommand, RunAuditResult


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
