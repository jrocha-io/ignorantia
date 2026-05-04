"""Entities for the search bounded context.

Entities here are *immutable values* — they have no identity beyond their
fields, but they are richer than plain :mod:`dataclasses` fixtures because
they encode invariants (e.g. ``year_end >= year_start``).

The unification of :class:`FetchedItem` across all 62 adapters is item D4
of audit #5 (issue #15) and is realised in F3 (issue #4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ignorantia.domain.search.value_objects import Method, Tier


@dataclass(frozen=True, slots=True)
class FetchedItem:
    """A single bibliographic record returned by a search adapter.

    The schema mirrors the v2 ``_adapter_base.FetchedItem`` plus the
    parity fields added by audit #5 (D3) — ``language``, ``is_oa``,
    ``url``, ``venue`` — so legacy mock fixtures can be migrated without
    rewriting tests. Identifier fields stay as ``str`` here; canonical
    parsing into :class:`~ignorantia.domain.slr.value_objects.DOI` /
    :class:`~ignorantia.domain.slr.value_objects.ISSN` happens at the
    SLR ingestion boundary.

    Attributes:
        title: Mandatory record title as returned by the source.
        source_tier: Origin tier (canonical per audit #5 fix E1).
        authors: Author names in source order.
        year: Publication year, when known.
        doi: Digital Object Identifier in raw form.
        issn: ISSN in raw form.
        isbn: ISBN in raw form.
        venue: Journal or conference venue.
        language: ISO 639-1 code; defaults to ``"en"``.
        is_oa: Whether the record is openly accessible.
        url: Landing page URL.
        url_for_pdf: Direct PDF URL when available.
        abstract: Abstract text in plain (non-HTML) form.
        publication_type: Free-form type tag (article, preprint, ...).
    """

    title: str
    source_tier: Tier
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
class SearchQuery:
    """A query targeting one or more search adapters.

    Attributes:
        text: Free-text query string. Adapters translate it to their
            native query syntax.
        year_start: Inclusive lower bound on publication year.
        year_end: Inclusive upper bound on publication year.
        languages: ISO 639-1 codes the caller is willing to accept;
            empty tuple means any.
    """

    text: str
    year_start: int | None = None
    year_end: int | None = None
    languages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the temporal window when both bounds are provided."""
        if (
            self.year_start is not None
            and self.year_end is not None
            and self.year_end < self.year_start
        ):
            raise ValueError(
                f"year_end ({self.year_end}) must be >= year_start ({self.year_start})"
            )


@dataclass(frozen=True, slots=True)
class SearchResult:
    """The result of one adapter run for one :class:`SearchQuery`.

    ``items`` is typed as ``tuple`` so the result is fully immutable;
    callers passing a ``list`` will get a static type error under
    ``mypy --strict``.

    Attributes:
        source: Adapter identifier (e.g. ``"arxiv"``).
        source_tier: The adapter's tier classification.
        method: How this run was executed (mock vs real).
        query: The originating query.
        items: Records returned (post-filtering by the adapter).
        total_results: Total hits the adapter reports for the query;
            defaults to ``len(items)`` when not supplied.
    """

    source: str
    source_tier: Tier
    method: Method
    query: SearchQuery
    items: tuple[FetchedItem, ...] = field(default_factory=tuple)
    total_results: int | None = None

    def __post_init__(self) -> None:
        """Default ``total_results`` to ``len(items)`` when not supplied."""
        if self.total_results is None:
            object.__setattr__(self, "total_results", len(self.items))
