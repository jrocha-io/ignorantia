"""Audit domain services.

This module exposes :class:`ManifestService`, the v3 successor to
v2's ``manifest_helpers`` (Decisions 21 and 22). The service appends
new :class:`AuditEntry` instances to a
:class:`ReproducibilityManifest`, stamping each with a timestamp
from an injected clock callable.

Time injection (issue #13): the service constructor takes a
``clock`` callable returning the timestamp string. Tests pin a
frozen value, audit replay produces identical bytes, and production
wiring binds ``clock`` to ``lambda: datetime.now(UTC).isoformat()``
in ``infrastructure/`` — keeping :func:`datetime.now` out of the
domain.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ignorantia.domain.audit.entities import (
    AuditEntry,
    ReproducibilityManifest,
)


class ManifestService:
    """Append events to a :class:`ReproducibilityManifest`.

    The service is stateless beyond the injected clock; instances are
    cheap to construct. :meth:`record` returns a *new* manifest with
    the appended entry — the input manifest is unchanged, so callers
    can hold prior snapshots without copying defensively.
    """

    def __init__(self, *, clock: Callable[[], str]) -> None:
        """Wire the service to a deterministic clock (issue #13)."""
        self._clock = clock

    def record(
        self,
        manifest: ReproducibilityManifest,
        *,
        action: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> ReproducibilityManifest:
        """Return a new manifest with a fresh entry appended.

        The clock is called at record time, not at service
        construction — every call gets the current timestamp.
        """
        entry = AuditEntry(
            timestamp_iso8601=self._clock(),
            action=action,
            actor=actor,
            payload=dict(payload) if payload is not None else {},
        )
        return manifest.append(entry)
