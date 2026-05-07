"""Data Transfer Objects between layers.

This module hosts the typed DTOs that flow across the application
boundary. Per ``V3_ARCHITECTURE_PLAN.md`` the rule is *no domain leak
to CLI* — interfaces (CLI, HTTP, etc.) only ever see DTOs from this
module, never raw domain entities or value objects.

DTOs are frozen dataclasses with ``slots=True`` (search-context
convention). They are intentionally simple shape-only carriers — no
business logic, no validation beyond "non-empty identity field".
That belongs in the domain.

This first slice (F6a) introduces the audit DTOs only; subsequent F6
PRs (RenderManuscript, FinalizePipeline, SearchForStudies) will append
their own ``Command`` / ``Result`` pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RunAuditCommand:
    """Input DTO for :class:`RunAuditUseCase`.

    Attributes:
        action: Stable action identifier
            (e.g. ``"search.run"``, ``"compliance.evaluate"``).
        actor: Who is recording the entry. CLI wiring sets this to
            ``"cli"``; engine code uses ``"ignorantia-engine"``.
        payload: Free-form details about the event.
    """

    action: str
    actor: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Empty action / actor break audit replay; reject early."""
        if not self.action:
            raise ValueError("RunAuditCommand.action must be a non-empty string")
        if not self.actor:
            raise ValueError("RunAuditCommand.actor must be a non-empty string")


@dataclass(frozen=True, slots=True)
class RunAuditResult:
    """Output DTO for :class:`RunAuditUseCase`.

    Attributes:
        timestamp_iso8601: When the entry was recorded.
        action: The action recorded (echoed from the command for
            convenience — saves callers a lookup).
        manifest_size: Number of entries in the manifest *after* the
            new entry was appended. Useful for progress logging.
    """

    timestamp_iso8601: str
    action: str
    manifest_size: int
