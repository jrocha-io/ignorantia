"""``BioRxivAdapter`` / ``MedRxivAdapter`` — bioRxiv and medRxiv preprint servers.

Both servers share the same ``api.biorxiv.org`` endpoint and only differ
in the ``server`` path segment, so :class:`MedRxivAdapter` is a thin
subclass that overrides one constant.

API peculiarity: there is no full-text search endpoint. Instead the API
returns *all* preprints in a date window, paginated via a cursor; the
adapter filters locally by matching the query against the title or
abstract. This is acceptable for systematic literature reviews because
the date window is naturally narrow (the SLR temporal scope).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any, ClassVar

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class BioRxivAdapter(AdapterPort):
    """Adapter for bioRxiv via ``api.biorxiv.org/details/biorxiv/...``."""

    source_id = "biorxiv"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://api.biorxiv.org/details"
    _SERVER: ClassVar[str] = "biorxiv"
    _DEFAULT_FROM: ClassVar[str] = "2020-01-01"

    def __init__(
        self,
        http: HttpClient,
        *,
        max_pages: int = 5,
        max_results: int = 200,
    ) -> None:
        """Wire the adapter and configure pagination."""
        if max_pages <= 0:
            raise ValueError("max_pages must be > 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_pages = max_pages
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Page through the date window and filter locally by query text."""
        from_date, to_date = self._date_window(query)
        needle = query.text.lower()
        kept: list[FetchedItem] = []
        cursor = 0
        for _ in range(self._max_pages):
            url = f"{self._API_URL}/{self._SERVER}/{from_date}/{to_date}/{cursor}"
            body = self._http.get(url)
            collection = _parse_collection(body)
            if not collection:
                break
            for item in collection:
                if len(kept) >= self._max_results:
                    break
                if _matches(item, needle):
                    kept.append(_normalise(item, self._SERVER, self.source_tier))
            if len(kept) >= self._max_results:
                break
            cursor += len(collection)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(kept),
        )

    def _date_window(self, query: SearchQuery) -> tuple[str, str]:
        today = date.today().isoformat()
        from_date = f"{query.year_start:04d}-01-01" if query.year_start else self._DEFAULT_FROM
        to_date = f"{query.year_end:04d}-12-31" if query.year_end else today
        if to_date > today:
            to_date = today
        return from_date, to_date


class MedRxivAdapter(BioRxivAdapter):
    """Adapter for medRxiv (same API as bioRxiv with a different path segment)."""

    source_id = "medrxiv"
    _SERVER = "medrxiv"


def _parse_collection(body: bytes) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("collection") or []
    return [item for item in raw if isinstance(item, dict)]


def _matches(item: dict[str, Any], needle: str) -> bool:
    title = str(item.get("title") or "").lower()
    abstract = str(item.get("abstract") or "").lower()
    return needle in title or needle in abstract


def _normalise(item: dict[str, Any], server: str, tier: Tier) -> FetchedItem:
    doi = item.get("doi") or None
    return FetchedItem(
        title=str(item.get("title") or ""),
        source_tier=tier,
        authors=tuple(_split_authors(item.get("authors"))),
        year=_year_from_date(item.get("date")),
        doi=str(doi) if doi else None,
        venue=server,
        language="en",
        is_oa=True,
        url=f"https://www.{server}.org/content/{doi}v1" if doi else None,
        url_for_pdf=f"https://www.{server}.org/content/{doi}v1.full.pdf" if doi else None,
        abstract=str(item.get("abstract") or "")[:500],
        publication_type="preprint",
    )


def _split_authors(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    return [chunk.strip() for chunk in value.split(";") if chunk.strip()]


def _year_from_date(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
