"""Data Transfer Objects between layers.

This module hosts the typed DTOs that flow across the application
boundary. Per ``V3_ARCHITECTURE_PLAN.md`` the rule is *no domain leak
to CLI* — interfaces (CLI, HTTP, etc.) only ever see DTOs from this
module, never raw domain entities or value objects.

DTOs are frozen dataclasses with ``slots=True`` (search-context
convention). They are intentionally simple shape-only carriers — no
business logic, no validation beyond "non-empty identity field".
That belongs in the domain.
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


@dataclass(frozen=True, slots=True)
class StepResultDto:
    """DTO for one step's outcome inside a :class:`FinalizePipelineResult`.

    Mirrors :class:`StepResult` from the pipeline domain, with
    ``status`` flattened to a string so interface-layer JSON
    serialisation is transparent.
    """

    name: str
    status: str
    message: str = ""
    artifact: str | None = None


@dataclass(frozen=True, slots=True)
class FinalizePipelineCommand:
    """Input DTO for :class:`FinalizePipelineUseCase`.

    The actual pipeline step registry is injected at use-case
    construction (DIP), so the command only conveys *runtime* hints
    callers want to surface in the manifest / summary. Today that's
    just the ``actor`` field — flags such as ``--skip-pdf`` will be
    added here when CLI wiring needs them.
    """

    actor: str

    def __post_init__(self) -> None:
        """Empty actor breaks audit replay; reject early."""
        if not self.actor:
            raise ValueError("FinalizePipelineCommand.actor must be a non-empty string")


@dataclass(frozen=True, slots=True)
class FinalizePipelineResult:
    """Output DTO for :class:`FinalizePipelineUseCase`.

    Attributes:
        started_at_iso8601: When the pipeline began.
        finished_at_iso8601: When the pipeline finished.
        steps: Per-step outcomes in execution order.
        n_ok: Steps that completed successfully.
        n_skipped: Steps that were deliberately skipped.
        n_errors: Steps that errored.
        final_artifacts: Paths of artefacts produced by ``OK`` steps,
            in execution order. Skipped / errored steps' artefacts
            are excluded — they may be partial or absent on disk.
        is_successful: ``True`` when no step errored.
    """

    started_at_iso8601: str
    finished_at_iso8601: str
    steps: tuple[StepResultDto, ...]
    n_ok: int
    n_skipped: int
    n_errors: int
    final_artifacts: tuple[str, ...]
    is_successful: bool


@dataclass(frozen=True, slots=True)
class SectionInputDto:
    """One body section in a :class:`RenderManuscriptCommand`."""

    id: str
    title: str
    body_md: str


@dataclass(frozen=True, slots=True)
class ReferenceInputDto:
    """One reference entry in a :class:`RenderManuscriptCommand`.

    The shape mirrors :class:`Reference` from ``domain.render``, with
    the same field names. The DTO exists so the interface layer can
    build references without importing domain types — translation to
    the domain happens inside the use case.
    """

    type: str
    title: str
    authors: tuple[str, ...]
    year: int | None = None
    venue: str = ""
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    accessed: str | None = None
    location: str | None = None
    publisher: str | None = None
    chapter_title: str | None = None
    book_editors: tuple[str, ...] | None = None
    program: str | None = None
    institution: str | None = None
    language: str = "en"


@dataclass(frozen=True, slots=True)
class RenderManuscriptCommand:
    """Input DTO for :class:`RenderManuscriptUseCase`.

    The shape is intentionally flat — interface code (CLI, HTTP)
    constructs this from raw inputs without ever touching a domain
    entity. The use case translates it to a :class:`ManuscriptDoc`
    via the F4j Builder.
    """

    title: str
    abstract: str = ""
    language: str = "en"
    keywords: tuple[str, ...] = field(default_factory=tuple)
    sections: tuple[SectionInputDto, ...] = field(default_factory=tuple)
    references: tuple[ReferenceInputDto, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Manuscripts without titles are not renderable; reject early."""
        if not self.title:
            raise ValueError("RenderManuscriptCommand.title must be a non-empty string")


@dataclass(frozen=True, slots=True)
class RenderManuscriptResult:
    """Output DTO for :class:`RenderManuscriptUseCase`.

    Attributes:
        output_format: Wire string for the format produced
            (``"html"``, ``"docx"``, ``"latex"``). Mirrors
            :class:`OutputFormat.value`.
        artifact_bytes: The rendered artefact as raw bytes. The
            interface layer is responsible for persisting / streaming.
        byte_size: ``len(artifact_bytes)``. Echoed for convenience —
            saves callers the size lookup when logging progress.
    """

    output_format: str
    artifact_bytes: bytes
    byte_size: int
