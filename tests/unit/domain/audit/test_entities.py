"""Unit tests for audit entities.

Two entities pinned by these tests:

* :class:`AuditEntry` — a single timestamped event in the audit log
  (timestamp, action, actor, payload). Immutable.
* :class:`ReproducibilityManifest` — an ordered collection of
  :class:`AuditEntry` instances forming the project's reproducibility
  log. Append returns a new manifest; the old one is unchanged.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ignorantia.domain.audit.entities import (
    AuditEntry,
    ReproducibilityManifest,
)

# ----------------------------------------------------------------------
# AuditEntry
# ----------------------------------------------------------------------


class TestAuditEntryConstruction:
    def test_minimum_fields(self) -> None:
        entry = AuditEntry(
            timestamp_iso8601="2026-05-07T12:00:00Z",
            action="search.run",
            actor="ignorantia-engine",
        )
        assert entry.timestamp_iso8601 == "2026-05-07T12:00:00Z"
        assert entry.action == "search.run"
        assert entry.actor == "ignorantia-engine"
        # Default payload is an empty mapping.
        assert entry.payload == {}

    def test_with_payload(self) -> None:
        entry = AuditEntry(
            timestamp_iso8601="2026-05-07T12:00:00Z",
            action="search.run",
            actor="ignorantia-engine",
            payload={"query_hash": "abc123", "n_results": 42},
        )
        assert entry.payload["query_hash"] == "abc123"
        assert entry.payload["n_results"] == 42


class TestAuditEntryInvariants:
    def test_timestamp_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="timestamp"):
            AuditEntry(timestamp_iso8601="", action="x", actor="x")

    def test_action_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="action"):
            AuditEntry(timestamp_iso8601="2026-05-07T12:00:00Z", action="", actor="x")

    def test_actor_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="actor"):
            AuditEntry(timestamp_iso8601="2026-05-07T12:00:00Z", action="x", actor="")


class TestAuditEntryImmutability:
    def test_is_frozen(self) -> None:
        entry = AuditEntry(timestamp_iso8601="2026-05-07T12:00:00Z", action="x", actor="x")
        with pytest.raises(FrozenInstanceError):
            entry.action = "y"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        assert AuditEntry.__slots__
        entry = AuditEntry(timestamp_iso8601="2026-05-07T12:00:00Z", action="x", actor="x")
        assert not hasattr(entry, "__dict__")

    def test_payload_is_a_separate_object_per_instance(self) -> None:
        a = AuditEntry(timestamp_iso8601="t", action="a", actor="x")
        b = AuditEntry(timestamp_iso8601="t", action="a", actor="x")
        # Default-factory mutables must not be shared.
        assert a.payload is not b.payload


# ----------------------------------------------------------------------
# ReproducibilityManifest
# ----------------------------------------------------------------------


def _entry(action: str = "x", actor: str = "ignorantia-engine") -> AuditEntry:
    return AuditEntry(
        timestamp_iso8601="2026-05-07T12:00:00Z",
        action=action,
        actor=actor,
    )


class TestReproducibilityManifestConstruction:
    def test_empty_construction(self) -> None:
        manifest = ReproducibilityManifest(entries=())
        assert manifest.entries == ()
        assert len(manifest) == 0

    def test_with_entries(self) -> None:
        e1 = _entry("search.run")
        e2 = _entry("phase4.consent")
        manifest = ReproducibilityManifest(entries=(e1, e2))
        assert len(manifest) == 2
        assert manifest.entries[0] is e1
        assert manifest.entries[1] is e2


class TestReproducibilityManifestAppend:
    def test_append_returns_new_manifest(self) -> None:
        original = ReproducibilityManifest(entries=())
        e = _entry("search.run")
        appended = original.append(e)
        assert appended is not original
        assert appended.entries == (e,)
        # original is unchanged
        assert original.entries == ()

    def test_append_preserves_order(self) -> None:
        e1 = _entry("a")
        e2 = _entry("b")
        e3 = _entry("c")
        manifest = ReproducibilityManifest(entries=()).append(e1).append(e2).append(e3)
        assert tuple(d.action for d in manifest.entries) == ("a", "b", "c")


class TestReproducibilityManifestQuery:
    def test_filter_by_action_returns_matching_entries(self) -> None:
        manifest = ReproducibilityManifest(
            entries=(
                _entry("search.run"),
                _entry("phase4.consent"),
                _entry("search.run"),
            )
        )
        runs = manifest.filter_by_action("search.run")
        assert len(runs) == 2
        assert all(e.action == "search.run" for e in runs)

    def test_filter_by_action_returns_empty_when_no_match(self) -> None:
        manifest = ReproducibilityManifest(entries=(_entry("a"),))
        assert manifest.filter_by_action("not-present") == ()

    def test_last_action_returns_most_recent_entry(self) -> None:
        e1 = _entry("search.run")
        e2 = _entry("search.run")
        manifest = ReproducibilityManifest(entries=(e1, e2))
        assert manifest.last_action("search.run") is e2

    def test_last_action_returns_none_when_no_match(self) -> None:
        manifest = ReproducibilityManifest(entries=(_entry("a"),))
        assert manifest.last_action("b") is None


class TestReproducibilityManifestImmutability:
    def test_is_frozen(self) -> None:
        manifest = ReproducibilityManifest(entries=())
        with pytest.raises(FrozenInstanceError):
            manifest.entries = ()  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        assert ReproducibilityManifest.__slots__
        manifest = ReproducibilityManifest(entries=())
        assert not hasattr(manifest, "__dict__")
