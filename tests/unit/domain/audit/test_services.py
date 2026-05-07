"""Unit tests for :class:`ManifestService`.

The service records new :class:`AuditEntry` instances on a
:class:`ReproducibilityManifest`, stamping them with a timestamp from
an injected clock callable (issue #13: datetime.now() injection for
reproducibility).
"""

from __future__ import annotations

import pytest

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


class TestManifestServiceRecord:
    def test_record_returns_new_manifest_with_appended_entry(
        self, service: ManifestService
    ) -> None:
        original = ReproducibilityManifest(entries=())
        updated = service.record(
            original,
            action="search.run",
            actor="ignorantia-engine",
        )
        assert updated is not original
        assert len(updated) == 1
        assert original.entries == ()  # original unchanged

    def test_appended_entry_carries_clock_timestamp(self) -> None:
        service = ManifestService(clock=_frozen_clock("2030-12-25T00:00:00Z"))
        manifest = service.record(
            ReproducibilityManifest(entries=()),
            action="x",
            actor="x",
        )
        assert manifest.entries[0].timestamp_iso8601 == "2030-12-25T00:00:00Z"

    def test_appended_entry_carries_action_and_actor(self, service: ManifestService) -> None:
        manifest = service.record(
            ReproducibilityManifest(entries=()),
            action="search.run",
            actor="ignorantia-engine",
        )
        assert manifest.entries[0].action == "search.run"
        assert manifest.entries[0].actor == "ignorantia-engine"

    def test_record_with_payload_passes_through(self, service: ManifestService) -> None:
        manifest = service.record(
            ReproducibilityManifest(entries=()),
            action="search.run",
            actor="ignorantia-engine",
            payload={"query_hash": "abc123", "n_results": 42},
        )
        assert manifest.entries[0].payload == {
            "query_hash": "abc123",
            "n_results": 42,
        }

    def test_record_without_payload_uses_empty_dict(self, service: ManifestService) -> None:
        manifest = service.record(
            ReproducibilityManifest(entries=()),
            action="x",
            actor="x",
        )
        assert manifest.entries[0].payload == {}

    def test_record_appends_to_existing_history(self, service: ManifestService) -> None:
        existing = ReproducibilityManifest(
            entries=(
                AuditEntry(
                    timestamp_iso8601="2026-05-01T00:00:00Z",
                    action="bootstrap",
                    actor="setup",
                ),
            )
        )
        updated = service.record(existing, action="search.run", actor="engine")
        assert len(updated) == 2
        assert updated.entries[0].action == "bootstrap"
        assert updated.entries[1].action == "search.run"


class TestManifestServiceClockIsolation:
    def test_clock_is_called_at_record_time_not_at_construction(self) -> None:
        # Each call uses the *current* clock return value — the
        # service must not cache the timestamp at construction.
        timestamps = iter(["2026-01-01T00:00:00Z", "2026-02-02T00:00:00Z", "2026-03-03T00:00:00Z"])

        def _clock() -> str:
            return next(timestamps)

        service = ManifestService(clock=_clock)
        manifest = ReproducibilityManifest(entries=())
        manifest = service.record(manifest, action="a", actor="x")
        manifest = service.record(manifest, action="b", actor="x")
        manifest = service.record(manifest, action="c", actor="x")

        assert manifest.entries[0].timestamp_iso8601 == "2026-01-01T00:00:00Z"
        assert manifest.entries[1].timestamp_iso8601 == "2026-02-02T00:00:00Z"
        assert manifest.entries[2].timestamp_iso8601 == "2026-03-03T00:00:00Z"
