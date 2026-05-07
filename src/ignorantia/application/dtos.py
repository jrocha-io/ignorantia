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
class FetchedItemDto:
    """Flat shape of one bibliographic record returned by a search adapter.

    Mirrors :class:`FetchedItem` from ``domain.search`` but with
    ``source_tier`` flattened to its wire string. CLI and HTTP layers
    consume this without importing domain types.
    """

    title: str
    source_tier: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None
    venue: str | None = None
    language: str = "en"
    is_oa: bool = False
    url: str | None = None
    url_for_pdf: str | None = None
    abstract: str = ""
    publication_type: str | None = None


@dataclass(frozen=True, slots=True)
class SearchSourceResultDto:
    """Per-source outcome of one adapter run.

    Attributes:
        source: Adapter identifier (e.g. ``"arxiv"``).
        source_tier: Wire string of the adapter's tier.
        method: Wire string of the execution method
            (e.g. ``"real"``, ``"real_error"``, ``"mock"``).
        items: The records the adapter returned, in source order.
        total_results: Total hits the adapter reports for the query
            (may be larger than ``len(items)`` when paginated).
    """

    source: str
    source_tier: str
    method: str
    items: tuple[FetchedItemDto, ...]
    total_results: int


@dataclass(frozen=True, slots=True)
class SearchForStudiesCommand:
    """Input DTO for :class:`SearchForStudiesUseCase`.

    Attributes:
        text: Free-text query string. Adapters translate it to their
            native query syntax.
        source_ids: Tuple of adapter identifiers to query
            (e.g. ``("arxiv", "openalex", "crossref")``).
        year_start: Inclusive lower bound on publication year.
        year_end: Inclusive upper bound on publication year.
        languages: ISO 639-1 codes the caller will accept. Empty
            tuple means any language.
    """

    text: str
    source_ids: tuple[str, ...]
    year_start: int | None = None
    year_end: int | None = None
    languages: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Empty queries / source lists make the request meaningless."""
        if not self.text:
            raise ValueError("SearchForStudiesCommand.text must be a non-empty string")
        if not self.source_ids:
            raise ValueError(
                "SearchForStudiesCommand.source_ids must contain at least one adapter id"
            )


@dataclass(frozen=True, slots=True)
class SearchForStudiesResult:
    """Output DTO for :class:`SearchForStudiesUseCase`.

    Attributes:
        per_source: Per-adapter results keyed by source id, in the
            order the command requested.
        deduplicated_items: Records across all sources with duplicates
            collapsed by the domain :class:`DeduplicatorService`.
        n_sources_ok: Adapter runs that produced ``Method.REAL`` /
            ``Method.MOCK`` (anything other than ``REAL_ERROR``).
        n_sources_errored: Adapter runs that captured a network
            failure as ``Method.REAL_ERROR``.
        n_items_total: Total items across all sources, *before*
            deduplication.
        n_items_deduplicated: ``len(deduplicated_items)``.
    """

    per_source: tuple[SearchSourceResultDto, ...]
    deduplicated_items: tuple[FetchedItemDto, ...]
    n_sources_ok: int
    n_sources_errored: int
    n_items_total: int
    n_items_deduplicated: int
