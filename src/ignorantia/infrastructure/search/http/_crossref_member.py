"""Shared base for paywall adapters that discover DOIs via Crossref.

Several publishers (Sage, ACM, Wiley TDM, ...) expose no public search
API of their own. Crossref, however, indexes their entire catalogue and
filters cleanly by ``member:<numeric-id>``. The pattern is identical
across publishers — only the member ID and ``source_id`` change — so
the parsing and URL building live here once.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter

_API_URL = "https://api.crossref.org/works"


class _CrossrefMemberAdapter(_PaywallAdapter):
    """Paywall adapter that uses Crossref's ``filter=member:N`` for discovery.

    Subclasses must declare:

    * :attr:`source_id` (e.g. ``"sage_full"``)
    * :attr:`source_tier` (typically :class:`Tier.TIER2`)
    * :attr:`_MEMBER_ID` — the numeric Crossref member identifier as a
      string (e.g. ``"179"`` for Sage, ``"320"`` for ACM).

    The base implements :meth:`_key_search`. The KEY here is the user's
    Crossref polite-pool email (recommended but not strictly required —
    we accept any non-empty ``api_key`` as the "credential" so the
    cascade still gates network calls behind explicit credentials).
    """

    _MEMBER_ID: ClassVar[str]

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(url)
        records = _parse_records(body, self._max_results)
        return tuple(_normalise(r, self.source_tier) for r in records)

    def _build_url(self, query: SearchQuery) -> str:
        filters = [f"member:{self._MEMBER_ID}"]
        if query.year_start is not None and query.year_end is not None:
            filters.append(f"from-pub-date:{query.year_start:04d}-01-01")
            filters.append(f"until-pub-date:{query.year_end:04d}-12-31")
        params: dict[str, str] = {
            "query": query.text,
            "filter": ",".join(filters),
            "rows": str(min(self._max_results, 100)),
        }
        return f"{_API_URL}?{urlencode(params)}"


def _parse_records(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    block = payload.get("message")
    if not isinstance(block, dict):
        return []
    raw = block.get("items") or []
    return [r for r in raw[:limit] if isinstance(r, dict)]


def _normalise(record: dict[str, Any], tier: Tier) -> FetchedItem:
    return FetchedItem(
        title=_first(record.get("title")),
        source_tier=tier,
        authors=tuple(_authors(record))[:10],
        year=_year(record),
        doi=_str_or_none(record.get("DOI")),
        issn=_first_or_none(record.get("ISSN")),
        venue=_first_or_none(record.get("container-title")),
        language=str(record.get("language") or "en"),
        is_oa=False,
        url=_str_or_none(record.get("URL")),
        publication_type=_str_or_none(record.get("type")),
    )


def _authors(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for author in record.get("author") or []:
        if not isinstance(author, dict):
            continue
        family = str(author.get("family") or "")
        given = str(author.get("given") or "")
        if family and given:
            out.append(f"{family}, {given}")
        elif family:
            out.append(family)
        elif given:
            out.append(given)
    return out


def _year(record: dict[str, Any]) -> int | None:
    issued = record.get("issued")
    if not isinstance(issued, dict):
        return None
    parts = issued.get("date-parts")
    if not isinstance(parts, list) or not parts:
        return None
    first = parts[0]
    if not isinstance(first, list) or not first:
        return None
    head = first[0]
    return int(head) if isinstance(head, int) else None


def _first(value: object) -> str:
    if isinstance(value, list) and value:
        head = value[0]
        return str(head) if head else ""
    if isinstance(value, str):
        return value
    return ""


def _first_or_none(value: object) -> str | None:
    out = _first(value)
    return out or None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
