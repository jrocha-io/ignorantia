"""``CoreAdapter`` — CORE.ac.uk OA aggregator (Open University UK).

Tier-0 source. CORE indexes ~280M Open Access works from institutional
repositories and journals worldwide — the largest OA aggregator,
complementary to Unpaywall and OA.Works. Search is via POST to
``api.core.ac.uk/v3/search/works`` with a JSON body. The API key is
optional (rate limit 10 req/min unauthenticated, 50 req/min with key).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class CoreAdapter(AdapterPort):
    """Adapter for CORE's ``api.core.ac.uk/v3/search/works`` endpoint."""

    source_id = "core"
    source_tier = Tier.TIER0

    _API_URL: ClassVar[str] = "https://api.core.ac.uk/v3/search/works"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(
        self,
        http: HttpClient,
        *,
        api_key: str | None = None,
        max_results: int = 100,
    ) -> None:
        """Wire the adapter; ``api_key`` raises the rate limit if provided."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._api_key = api_key
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """POST a search and return the parsed result."""
        body = self._http.post(
            self._API_URL,
            data=self._build_body(query),
            headers=self._build_headers(),
        )
        items = tuple(
            _normalise(it, self.source_tier) for it in _parse_results(body, self._max_results)
        )
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_body(self, query: SearchQuery) -> bytes:
        q = query.text
        if query.year_start is not None and query.year_end is not None:
            q = (
                f"({query.text}) AND yearPublished>={query.year_start} "
                f"AND yearPublished<={query.year_end}"
            )
        payload = {
            "q": q,
            "limit": min(self._max_results, self._PAGE_CAP),
            "scroll": False,
        }
        return json.dumps(payload).encode("utf-8")

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers


def _parse_results(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("results") or []
    return [r for r in raw[:limit] if isinstance(r, dict)]


def _normalise(item: dict[str, Any], tier: Tier) -> FetchedItem:
    providers = item.get("dataProviders") or []
    repository = None
    if providers and isinstance(providers[0], dict):
        repository = _str_or_none(providers[0].get("name"))
    venue = _str_or_none(item.get("publisher")) or repository
    return FetchedItem(
        title=str(item.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(item))[:10],
        year=_safe_int(item.get("yearPublished")),
        doi=_str_or_none(item.get("doi")),
        venue=venue,
        language="en",
        is_oa=True,
        url_for_pdf=_str_or_none(item.get("downloadUrl")),
        publication_type="journal-article",
    )


def _authors(item: dict[str, Any]) -> list[str]:
    raw = item.get("authors") or []
    out: list[str] = []
    for a in raw:
        if isinstance(a, dict) and a.get("name"):
            out.append(str(a["name"]))
    return out


def _safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
