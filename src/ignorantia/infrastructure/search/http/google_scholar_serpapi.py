"""``GoogleScholarSerpApiAdapter`` — Google Scholar via SerpAPI (Tier 2).

Google Scholar prohibits direct programmatic access in its ToS; the only
ToS-compliant programmatic path is through SerpAPI's commercial service,
which assumes the legal/operational responsibility of the underlying
scraping. SerpAPI requires a paid key (``SERPAPI_KEY``); without it the
adapter short-circuits to ``Method.REAL_ERROR`` rather than wasting an
unauthenticated call SerpAPI would reject.

Caveat for SLR rigor: Google Scholar does not expose structured DOIs, so
items returned here have ``doi=None``. Crossref / OpenAlex enrichment by
title is recommended downstream when DOIs are required.
"""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_ABSTRACT_CAP = 500


class GoogleScholarSerpApiAdapter(AdapterPort):
    """Adapter for Google Scholar via SerpAPI's REST endpoint."""

    source_id = "google_scholar_serpapi"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://serpapi.com/search"
    _PAGE_SIZE: ClassVar[int] = 10

    def __init__(
        self,
        http: HttpClient,
        *,
        api_key: str | None = None,
        max_results: int = 100,
    ) -> None:
        """Wire the adapter; ``api_key`` (SerpAPI) is required for any real fetch."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._api_key = api_key
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Paginate through SerpAPI's Google Scholar results."""
        if not self._api_key:
            return self._build_result(query, Method.REAL_ERROR, ())
        items: list[FetchedItem] = []
        start = 0
        while len(items) < self._max_results:
            body = self._http.get(
                self._build_url(query, start), headers={"Accept": "application/json"}
            )
            organic = _parse_organic(body)
            if not organic:
                break
            for raw in organic:
                if len(items) >= self._max_results:
                    break
                items.append(_normalise(raw, self.source_tier))
            if len(organic) < self._PAGE_SIZE:
                break
            start += self._PAGE_SIZE
        return self._build_result(query, Method.REAL, tuple(items))

    def _build_url(self, query: SearchQuery, start: int) -> str:
        params: list[tuple[str, str]] = [
            ("engine", "google_scholar"),
            ("q", query.text),
            ("api_key", self._api_key or ""),
            ("start", str(start)),
            ("num", str(self._PAGE_SIZE)),
        ]
        if query.year_start is not None:
            params.append(("as_ylo", str(query.year_start)))
        if query.year_end is not None:
            params.append(("as_yhi", str(query.year_end)))
        return f"{self._API_URL}?{urlencode(params)}"

    def _build_result(
        self,
        query: SearchQuery,
        method: Method,
        items: tuple[FetchedItem, ...],
    ) -> SearchResult:
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=method,
            query=query,
            items=items,
        )


def _parse_organic(body: bytes) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("organic_results") or []
    return [r for r in raw if isinstance(r, dict)]


def _normalise(item: dict[str, Any], tier: Tier) -> FetchedItem:
    pub_info = item.get("publication_info") or {}
    summary = pub_info.get("summary") if isinstance(pub_info, dict) else None
    pdf_url = _first_pdf(item.get("resources"))
    return FetchedItem(
        title=str(item.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(pub_info))[:10],
        year=_year_from_summary(summary),
        venue=_venue_from_summary(summary),
        language="en",
        is_oa=pdf_url is not None,
        url=_str_or_none(item.get("link")),
        url_for_pdf=pdf_url,
        abstract=str(item.get("snippet") or "")[:_ABSTRACT_CAP],
    )


def _authors(pub_info: object) -> list[str]:
    if not isinstance(pub_info, dict):
        return []
    raw = pub_info.get("authors") or []
    return [str(a["name"]) for a in raw if isinstance(a, dict) and a.get("name")]


def _year_from_summary(summary: object) -> int | None:
    if not isinstance(summary, str):
        return None
    match = _YEAR_RE.search(summary)
    return int(match.group(1)) if match else None


def _venue_from_summary(summary: object) -> str | None:
    # SerpAPI summaries are formatted as "<authors> - <venue>, <year>".
    if not isinstance(summary, str) or " - " not in summary:
        return None
    return summary.split(" - ", 1)[1].strip() or None


def _first_pdf(resources: object) -> str | None:
    if not isinstance(resources, list):
        return None
    for entry in resources:
        if isinstance(entry, dict) and entry.get("file_format") == "PDF":
            link = entry.get("link")
            if isinstance(link, str) and link:
                return link
    return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
