"""Unit tests for :class:`RunAuditUseCase`.

The use case is exercised against a real :class:`ManifestService`
wired with a frozen clock — domain services are deterministic and
fast, so there is no benefit to mocking them; the real assembly is
what we actually want to pin. Where the use case carries its *own*
state (the running manifest), tests assert it accumulates correctly
across calls.
"""

from __future__ import annotations

import pytest

from ignorantia.application.dtos import RunAuditCommand, RunAuditResult
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.domain.audit.entities import (
    AuditEntry,
    ReproducibilityManifest,
)
from ignorantia.domain.audit.services import ManifestService


def _frozen_clock(value: str = "2026-05-07T12:00:00Z"):
    def _clock() -> str:
        return value

    return _clock


@pytest.fixture
def service() -> ManifestService:
    return ManifestService(clock=_frozen_clock())


@pytest.fixture
def use_case(service: ManifestService) -> RunAuditUseCase:
    return RunAuditUseCase(service=service)


class TestRunAuditUseCaseExecute:
    def test_execute_returns_run_audit_result(self, use_case: RunAuditUseCase) -> None:
        result = use_case.execute(RunAuditCommand(action="x", actor="cli"))
        assert isinstance(result, RunAuditResult)

    def test_result_carries_clock_timestamp(self, use_case: RunAuditUseCase) -> None:
        result = use_case.execute(RunAuditCommand(action="x", actor="cli"))
        assert result.timestamp_iso8601 == "2026-05-07T12:00:00Z"

    def test_result_echoes_action(self, use_case: RunAuditUseCase) -> None:
        result = use_case.execute(RunAuditCommand(action="search.run", actor="cli"))
        assert result.action == "search.run"

    def test_result_reports_manifest_size_after_append(self, use_case: RunAuditUseCase) -> None:
        first = use_case.execute(RunAuditCommand(action="a", actor="cli"))
        second = use_case.execute(RunAuditCommand(action="b", actor="cli"))
        assert first.manifest_size == 1
        assert second.manifest_size == 2


class TestRunAuditUseCaseManifestState:
    def test_default_initial_manifest_is_empty(self, use_case: RunAuditUseCase) -> None:
        assert len(use_case.manifest) == 0

    def test_initial_manifest_can_be_seeded(self, service: ManifestService) -> None:
        seeded = ReproducibilityManifest(
            entries=(
                AuditEntry(
                    timestamp_iso8601="2026-05-01T00:00:00Z",
                    action="bootstrap",
                    actor="setup",
                ),
            )
        )
        use_case = RunAuditUseCase(service=service, manifest=seeded)
        assert len(use_case.manifest) == 1
        assert use_case.manifest.entries[0].action == "bootstrap"

    def test_manifest_accumulates_across_calls(self, use_case: RunAuditUseCase) -> None:
        use_case.execute(RunAuditCommand(action="a", actor="cli"))
        use_case.execute(RunAuditCommand(action="b", actor="cli"))
        use_case.execute(RunAuditCommand(action="c", actor="cli"))
        assert tuple(e.action for e in use_case.manifest.entries) == ("a", "b", "c")

    def test_payload_propagates_through_to_entry(self, use_case: RunAuditUseCase) -> None:
        use_case.execute(
            RunAuditCommand(
                action="search.run",
                actor="cli",
                payload={"query_hash": "abc123", "n_results": 7},
            )
        )
        last = use_case.manifest.entries[-1]
        assert last.payload == {"query_hash": "abc123", "n_results": 7}


class TestRunAuditUseCaseDoesNotLeakDomain:
    def test_execute_returns_dto_not_audit_entry(self, use_case: RunAuditUseCase) -> None:
        # Per V3_ARCHITECTURE_PLAN.md: no domain leak to interface
        # layer. AuditEntry stays inside the use case.
        result = use_case.execute(RunAuditCommand(action="x", actor="cli"))
        assert not isinstance(result, AuditEntry)
        assert isinstance(result, RunAuditResult)
