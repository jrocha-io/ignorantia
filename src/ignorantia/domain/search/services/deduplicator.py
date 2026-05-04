"""``DeduplicatorService`` — collapses identical records across adapters.

A *domain service* (DDD): stateless, pure, and free of any I/O or
infrastructure dependency.

Deduplication policy:

* Same DOI (case-insensitive, whitespace-trimmed) → duplicate.
* Two records without a DOI but with the same normalised title → duplicate.
* DOI-bearing record arriving *after* a no-DOI record with the same title
  is also a duplicate (the no-DOI record was conservative; we trust it).
* Two records with **different** DOIs are *never* considered duplicates,
  even when titles match — different DOIs imply different registered
  objects (preprint vs. final version, e.g.).

First-seen order is preserved.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ignorantia.domain.search.entities import FetchedItem

_WHITESPACE = re.compile(r"\s+")


class DeduplicatorService:
    """Stateless, no-instance service exposing ``deduplicate`` only."""

    @staticmethod
    def deduplicate(items: Iterable[FetchedItem]) -> tuple[FetchedItem, ...]:
        """Return ``items`` with duplicates collapsed (first-seen wins)."""
        ledger = _Ledger()
        kept: list[FetchedItem] = []
        for item in items:
            if not ledger.is_duplicate(item):
                ledger.record(item)
                kept.append(item)
        return tuple(kept)


class _Ledger:
    """Internal book-keeping for the deduplicator."""

    def __init__(self) -> None:
        self._seen_dois: set[str] = set()
        self._titles_from_no_doi: set[str] = set()
        self._all_titles: set[str] = set()

    def is_duplicate(self, item: FetchedItem) -> bool:
        title = _title_key(item.title)
        if item.doi is None:
            return title in self._all_titles
        return _doi_key(item.doi) in self._seen_dois or title in self._titles_from_no_doi

    def record(self, item: FetchedItem) -> None:
        title = _title_key(item.title)
        self._all_titles.add(title)
        if item.doi is None:
            self._titles_from_no_doi.add(title)
        else:
            self._seen_dois.add(_doi_key(item.doi))


def _doi_key(value: str) -> str:
    return value.strip().lower()


def _title_key(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip().lower())
