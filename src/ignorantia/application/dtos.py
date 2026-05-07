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
