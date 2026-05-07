"""Entities for the audit bounded context.

Two aggregates anchor the audit domain:

* :class:`AuditEntry` — a single timestamped event in the project's
  reproducibility log. Carries the timestamp, the action identifier
  (e.g. ``"search.run"``, ``"phase4.consent"``), the actor that
  produced it, and an optional free-form payload mapping.
* :class:`ReproducibilityManifest` — an ordered, immutable
  collection of :class:`AuditEntry` instances. Append returns a
  *new* manifest; the original is unchanged so the audit history
  forms a persistent sequence rather than mutable state hidden
  behind a method call.

These replace the dict + YAML helpers in
``scripts/manifest_helpers.py`` (Decisions 21 and 22). The v3 form
is structurally enforced — empty actions / actors / timestamps are
rejected at construction time, so audit replay never trips on
malformed entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """A single event recorded in the reproducibility manifest.

    Attributes:
        timestamp_iso8601: When the event happened
            (``YYYY-MM-DDTHH:MM:SSZ``).
        action: Stable action identifier; dotted names recommended
            (``"search.run"``, ``"phase4.consent"``,
            ``"compliance.evaluate"``).
        actor: Who recorded the entry. Production wiring uses
            ``"ignorantia-engine"``; CI / human runs override.
        payload: Free-form key/value details about the event. Empty
            by default. Renamed from v2's flat-dict approach so
            payload is a *child* mapping, not the entry itself.
    """

    timestamp_iso8601: str
    action: str
    actor: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject empty identifiers — they break audit replay lookups."""
        if not self.timestamp_iso8601:
            raise ValueError("AuditEntry.timestamp_iso8601 must be a non-empty string")
        if not self.action:
            raise ValueError("AuditEntry.action must be a non-empty string")
        if not self.actor:
            raise ValueError("AuditEntry.actor must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ReproducibilityManifest:
    """Ordered, immutable collection of audit entries.

    The manifest is the project's persistent reproducibility log.
    Mutation methods return a *new* manifest with the change applied
    rather than mutating in place — the design keeps audit history
    as a persistent data structure so callers can always reference
    a stable, immutable snapshot.
    """

    entries: tuple[AuditEntry, ...]

    def __len__(self) -> int:
        """Number of entries in the manifest."""
        return len(self.entries)

    def append(self, entry: AuditEntry) -> ReproducibilityManifest:
        """Return a new manifest with ``entry`` appended."""
        return ReproducibilityManifest(entries=(*self.entries, entry))

    def filter_by_action(self, action: str) -> tuple[AuditEntry, ...]:
        """Return every entry whose ``action`` equals ``action``."""
        return tuple(e for e in self.entries if e.action == action)

    def last_action(self, action: str) -> AuditEntry | None:
        """Return the most recent entry with the given action, or ``None``."""
        for entry in reversed(self.entries):
            if entry.action == action:
                return entry
        return None
