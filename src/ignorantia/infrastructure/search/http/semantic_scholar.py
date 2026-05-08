"""``SemanticScholarAdapter`` — concrete :class:`AdapterPort` for Semantic Scholar.

Semantic Scholar exposes a free Graph API. With an API key the rate
limit increases substantially; without one the adapter still works but
slower. Migrated from v2 ``search_semantic_scholar.py``.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient

_FIELDS = (
    "paperId,title,abstract,year,venue,authors,externalIds,"
    "openAccessPdf,citationCount,publicationTypes,fieldsOfStudy"
)


class SemanticScholarAdapter(AdapterPort):
    """Adapter for the Semantic Scholar Graph API ``/paper/search``."""

    source_id = "semantic_scholar"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(
        self,
        http: HttpClient,
        *,
        max_per_page: int = 100,
        max_results: int = 500,
        api_key: str | None = None,
    ) -> None:
        """Wire the adapter and configure pagination + optional API key."""
        if max_per_page <= 0:
            raise ValueError("max_per_page must be > 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_per_page = max_per_page
        self._max_results = max_results
        self._api_key = api_key

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from S2 paginating until empty or capped."""
        items: list[FetchedItem] = []
        offset = 0
        while offset < self._max_results:
            url = self._build_url(query, offset)
            body = self._http.get(url, headers=self._headers())
            page = _parse_page(body)
            if not page:
                break
            for raw in page:
                if len(items) >= self._max_results:
                    break
                items.append(_normalise(raw))
            if len(items) >= self._max_results:
                break
            if len(page) < self._max_per_page:
                break
            offset += self._max_per_page
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(items),
        )

    def _build_url(self, query: SearchQuery, offset: int) -> str:
        params: dict[str, str] = {
            "query": query.text,
            "fields": _FIELDS,
            "offset": str(offset),
            "limit": str(self._max_per_page),
        }
        if query.year_start is not None and query.year_end is not None:
            params["year"] = f"{query.year_start}-{query.year_end}"
        return f"{self._API_URL}?{urlencode(params)}"

    def _headers(self) -> dict[str, str] | None:
        return {"x-api-key": self._api_key} if self._api_key else None


def _parse_page(body: bytes) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    return [p for p in (payload.get("data") or []) if isinstance(p, dict)]


def _normalise(paper: dict[str, Any]) -> FetchedItem:
    pdf = _pdf_url(paper)
    return FetchedItem(
        title=str(paper.get("title") or ""),
        source_tier=Tier.TIER2,
        authors=tuple(_authors(paper)),
        year=_safe_int(paper.get("year")),
        doi=_doi(paper.get("externalIds")),
        venue=str(paper.get("venue") or "") or None,
        language="en",
        is_oa=bool(pdf),
        url=_canonical_url(paper, pdf),
        url_for_pdf=pdf,
        abstract=str(paper.get("abstract") or ""),
        publication_type=_first_publication_type(paper),
    )


def _authors(paper: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for a in paper.get("authors") or []:
        if isinstance(a, dict) and a.get("name"):
            out.append(str(a["name"]))
    return out


def _doi(external_ids: object) -> str | None:
    if not isinstance(external_ids, dict):
        return None
    doi = external_ids.get("DOI")
    return str(doi) if isinstance(doi, str) and doi else None


def _pdf_url(paper: dict[str, Any]) -> str | None:
    pdf = paper.get("openAccessPdf")
    if isinstance(pdf, dict) and pdf.get("url"):
        return str(pdf["url"])
    return None


def _canonical_url(paper: dict[str, Any], pdf: str | None) -> str | None:
    if pdf:
        return pdf
    paper_id = paper.get("paperId")
    if isinstance(paper_id, str) and paper_id:
        return f"https://www.semanticscholar.org/paper/{paper_id}"
    return None


def _first_publication_type(paper: dict[str, Any]) -> str | None:
    types = paper.get("publicationTypes")
    if isinstance(types, list) and types and isinstance(types[0], str):
        return types[0]
    return None


def _safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
