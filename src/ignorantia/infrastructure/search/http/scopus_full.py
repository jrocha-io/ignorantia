"""``ScopusFullAdapter`` — Scopus via Elsevier Search API.

Tier-2 paywall source. Migrated from v2 ``search_scopus_full.py``;
inherits the KEY → PROXY cascade from :class:`_PaywallAdapter`. Scopus
ships only KEY-mode access today; PROXY mode is intentionally
unsupported (the institutional proxy returns HTML that requires a
publisher-specific parser).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter

_FIELDS = (
    "dc:title,dc:creator,prism:publicationName,prism:coverDate,"
    "prism:doi,prism:issn,subtype,openaccess"
)


class ScopusFullAdapter(_PaywallAdapter):
    """Adapter for Scopus's ``api.elsevier.com/content/search/scopus``."""

    source_id = "scopus_full"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.elsevier.com/content/search/scopus"
    _PAGE_CAP: ClassVar[int] = 25  # Scopus caps a single response at 25 entries

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(url, headers={"X-ELS-APIKey": self._api_key or ""})
        entries = _parse_entries(body, self._max_results)
        return tuple(_normalise(e, self.source_tier) for e in entries)

    def _build_url(self, query: SearchQuery) -> str:
        scopus_query = query.text
        if query.year_start is not None and query.year_end is not None:
            scopus_query = (
                f"({query.text}) "
                f"AND PUBYEAR > {query.year_start - 1} "
                f"AND PUBYEAR < {query.year_end + 1}"
            )
        params: dict[str, str] = {
            "query": scopus_query,
            "count": str(min(self._max_results, self._PAGE_CAP)),
            "field": _FIELDS,
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_entries(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    block = payload.get("search-results")
    if not isinstance(block, dict):
        return []
    raw = block.get("entry") or []
    return [e for e in raw[:limit] if isinstance(e, dict)]


def _normalise(entry: dict[str, Any], tier: Tier) -> FetchedItem:
    creator = entry.get("dc:creator")
    authors = (str(creator),) if isinstance(creator, str) and creator else ()
    return FetchedItem(
        title=str(entry.get("dc:title") or ""),
        source_tier=tier,
        authors=authors,
        year=_year_from_iso(entry.get("prism:coverDate")),
        doi=_str_or_none(entry.get("prism:doi")),
        issn=_str_or_none(entry.get("prism:issn")),
        venue=_str_or_none(entry.get("prism:publicationName")),
        language="en",
        is_oa=_is_open_access(entry.get("openaccess")),
        publication_type=_str_or_none(entry.get("subtype")),
    )


def _year_from_iso(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _is_open_access(value: object) -> bool:
    return value in {"1", 1}


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
