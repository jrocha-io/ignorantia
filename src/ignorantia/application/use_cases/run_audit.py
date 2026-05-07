"""``RunAuditUseCase`` — record an event in the reproducibility manifest.

Wraps :class:`ManifestService` (F5b) behind the F6 use-case pattern: the
use case takes a :class:`RunAuditCommand` DTO from the interface layer,
delegates to the domain service, and returns a :class:`RunAuditResult`
DTO so the interface layer never touches a domain entity directly.

The use case holds the *current* :class:`ReproducibilityManifest` in an
attribute so successive calls accumulate entries within a process run.
Persistence is the interface layer's responsibility — this use case
does not load or save the manifest, matching the architecture plan's
"application orchestrates, infrastructure persists" split.
"""

from __future__ import annotations

from ignorantia.application.dtos import RunAuditCommand, RunAuditResult
from ignorantia.domain.audit.entities import ReproducibilityManifest
from ignorantia.domain.audit.services import ManifestService


class RunAuditUseCase:
    """Append one audit entry per :meth:`execute` call."""

    def __init__(
        self,
        *,
        service: ManifestService,
        manifest: ReproducibilityManifest | None = None,
    ) -> None:
        """Wire the use case to a service and an initial manifest.

        Args:
            service: The :class:`ManifestService` (DIP — the use case
                depends on the abstraction; production wiring binds
                it to a service constructed with a real clock).
            manifest: Optional starting manifest. Defaults to an empty
                manifest, so a freshly constructed use case is usable
                without an explicit bootstrap step.
        """
        self._service = service
        self._manifest = manifest or ReproducibilityManifest(entries=())

    @property
    def manifest(self) -> ReproducibilityManifest:
        """The current manifest after the most recent :meth:`execute`."""
        return self._manifest

    def execute(self, command: RunAuditCommand) -> RunAuditResult:
        """Record one entry and return a :class:`RunAuditResult` DTO."""
        self._manifest = self._service.record(
            self._manifest,
            action=command.action,
            actor=command.actor,
            payload=command.payload,
        )
        last = self._manifest.entries[-1]
        return RunAuditResult(
            timestamp_iso8601=last.timestamp_iso8601,
            action=last.action,
            manifest_size=len(self._manifest),
        )
