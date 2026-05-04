"""``WosFullAdapter`` — Web of Science Starter API (Clarivate).

Tier-2 paywall. Uses the WoS Starter API (limited free tier, ~10k
requests/month) with ``X-ApiKey`` header and ``TS=(...)`` topic-search
syntax. Pagination via ``page`` parameter; this adapter performs a
single request because the Starter API caps results at 50/req anyway.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class WosFullAdapter(_PaywallAdapter):
    """Adapter for Web of Science's ``api.clarivate.com/apis/wos-starter/v1``."""

    source_id = "wos_full"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.clarivate.com/apis/wos-starter/v1/documents"
    _PAGE_CAP: ClassVar[int] = 50

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(url, headers={"X-ApiKey": self._api_key or ""})
        hits = _parse_hits(body, self._max_results)
        return tuple(_normalise(h, self.source_tier) for h in hits)

    def _build_url(self, query: SearchQuery) -> str:
        wos_query = f"TS=({query.text})"
        if query.year_start is not None and query.year_end is not None:
            wos_query += f" AND PY={query.year_start}-{query.year_end}"
        params: dict[str, str] = {
            "db": "WOS",
            "q": wos_query,
            "limit": str(min(self._max_results, self._PAGE_CAP)),
            "page": "1",
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_hits(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("hits") or []
    return [h for h in raw[:limit] if isinstance(h, dict)]


def _normalise(hit: dict[str, Any], tier: Tier) -> FetchedItem:
    uid = _str_or_none(hit.get("uid"))
    return FetchedItem(
        title=_title(hit),
        source_tier=tier,
        authors=tuple(_authors(hit))[:10],
        year=_safe_int(_source(hit).get("publishYear")),
        doi=_identifier(hit, "doi"),
        issn=_identifier(hit, "issn"),
        venue=_str_or_none(_source(hit).get("sourceTitle")),
        language="en",
        is_oa=False,
        url=f"https://www.webofscience.com/wos/woscc/full-record/{uid}" if uid else None,
        publication_type=_first_doc_type(hit),
    )


def _title(hit: dict[str, Any]) -> str:
    title = hit.get("title")
    if isinstance(title, dict):
        return str(title.get("value") or "")
    if isinstance(title, str):
        return title
    return ""


def _authors(hit: dict[str, Any]) -> list[str]:
    names = hit.get("names")
    if not isinstance(names, dict):
        return []
    raw = names.get("authors") or []
    out: list[str] = []
    for a in raw:
        if isinstance(a, dict) and a.get("displayName"):
            out.append(str(a["displayName"]))
    return out


def _source(hit: dict[str, Any]) -> dict[str, Any]:
    src = hit.get("source")
    return src if isinstance(src, dict) else {}


def _identifier(hit: dict[str, Any], identifier_type: str) -> str | None:
    for entry in hit.get("identifiers") or []:
        if isinstance(entry, dict) and entry.get("type") == identifier_type and entry.get("value"):
            return str(entry["value"])
    return None


def _first_doc_type(hit: dict[str, Any]) -> str | None:
    types = hit.get("documentTypes")
    if isinstance(types, list) and types and isinstance(types[0], str):
        return types[0]
    if isinstance(types, str) and types:
        return types
    return None


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
