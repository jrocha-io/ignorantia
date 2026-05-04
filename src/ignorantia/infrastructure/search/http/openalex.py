"""``OpenAlexAdapter`` — concrete :class:`AdapterPort` for OpenAlex.

OpenAlex is the open bibliographic database from OurResearch. It exposes
both metadata and (for OA records) full-text URLs. Tier classification
depends on the ``oa_only`` switch: when ``True`` the adapter restricts
results to open access (Tier 1); when ``False`` it returns Tier-2
metadata for any record.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class OpenAlexAdapter(AdapterPort):
    """Adapter for OpenAlex's ``/works`` endpoint."""

    source_id = "openalex"

    _API_URL: ClassVar[str] = "https://api.openalex.org/works"
    _MAX_PER_PAGE: ClassVar[int] = 200

    def __init__(
        self,
        http: HttpClient,
        *,
        max_results: int = 200,
        oa_only: bool = True,
        contact_email: str | None = None,
    ) -> None:
        """Wire the adapter, configure the OA filter and polite-pool email."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results
        self._oa_only = oa_only
        self._contact_email = contact_email

    @property
    def source_tier(self) -> Tier:
        """OA-only mode promotes the source to Tier 1."""
        return Tier.TIER1 if self._oa_only else Tier.TIER2

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from OpenAlex (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        raw_works = _parse_results(body, self._max_results)
        items = tuple(_normalise(raw, self.source_tier) for raw in raw_works)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        filters = [f"title_and_abstract.search:{query.text}"]
        if query.year_start is not None and query.year_end is not None:
            filters.append(f"publication_year:{query.year_start}-{query.year_end}")
        if self._oa_only:
            filters.append("is_oa:true")
        params: dict[str, str] = {
            "filter": ",".join(filters),
            "per-page": str(min(self._max_results, self._MAX_PER_PAGE)),
            "sort": "cited_by_count:desc",
        }
        if self._contact_email:
            params["mailto"] = self._contact_email
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_results(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("results") or []
    return [w for w in raw[:limit] if isinstance(w, dict)]


def _normalise(work: dict[str, Any], tier: Tier) -> FetchedItem:
    return FetchedItem(
        title=str(work.get("title") or work.get("display_name") or ""),
        source_tier=tier,
        authors=tuple(_authors(work)),
        year=_safe_int(work.get("publication_year")),
        doi=_doi(work.get("doi")),
        venue=_venue(work),
        language=str(work.get("language") or "en"),
        is_oa=bool(_open_access(work).get("is_oa", False)),
        url=_canonical_url(work),
        url_for_pdf=_pdf_url(work),
        abstract=_abstract(work.get("abstract_inverted_index"))[:500],
        publication_type=str(work.get("type") or "") or None,
    )


def _authors(work: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for ship in work.get("authorships") or []:
        if not isinstance(ship, dict):
            continue
        author = ship.get("author")
        if isinstance(author, dict) and author.get("display_name"):
            out.append(str(author["display_name"]))
    return out[:10]


def _doi(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    prefix = "https://doi.org/"
    return value[len(prefix) :] if value.startswith(prefix) else value


def _venue(work: dict[str, Any]) -> str | None:
    primary = work.get("primary_location")
    if isinstance(primary, dict):
        source = primary.get("source")
        if isinstance(source, dict) and source.get("display_name"):
            return str(source["display_name"])
    return None


def _open_access(work: dict[str, Any]) -> dict[str, Any]:
    oa = work.get("open_access")
    return oa if isinstance(oa, dict) else {}


def _canonical_url(work: dict[str, Any]) -> str | None:
    openalex_id = work.get("id")
    return str(openalex_id) if isinstance(openalex_id, str) else None


def _pdf_url(work: dict[str, Any]) -> str | None:
    for key in ("best_oa_location", "primary_location"):
        loc = work.get(key)
        if isinstance(loc, dict) and loc.get("pdf_url"):
            return str(loc["pdf_url"])
    return None


def _abstract(inverted_index: object) -> str:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for token, indices in inverted_index.items():
        if not isinstance(indices, list):
            continue
        for idx in indices:
            if isinstance(idx, int):
                positions.append((idx, str(token)))
    positions.sort()
    return " ".join(token for _, token in positions)


def _safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
