"""``SpringerFullAdapter`` — Springer Nature Meta API.

Tier-2 paywall (free key with registration). Uses the
``meta/v2/json`` endpoint with a query DSL that accepts
``onlinedatefrom``/``onlinedateto`` filters inline.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class SpringerFullAdapter(_PaywallAdapter):
    """Adapter for Springer Nature's ``api.springernature.com/meta/v2/json``."""

    source_id = "springer_full"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.springernature.com/meta/v2/json"
    _PAGE_CAP: ClassVar[int] = 100

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(url)
        records = _parse_records(body, self._max_results)
        return tuple(_normalise(r, self.source_tier) for r in records)

    def _build_url(self, query: SearchQuery) -> str:
        q_text = query.text
        if query.year_start is not None and query.year_end is not None:
            q_text = (
                f"{query.text} "
                f"onlinedatefrom:{query.year_start:04d}-01-01 "
                f"onlinedateto:{query.year_end:04d}-12-31"
            )
        params: dict[str, str] = {
            "q": q_text,
            "p": str(min(self._max_results, self._PAGE_CAP)),
            "api_key": self._api_key or "",
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_records(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("records") or []
    return [r for r in raw[:limit] if isinstance(r, dict)]


def _normalise(record: dict[str, Any], tier: Tier) -> FetchedItem:
    landing, pdf = _urls(record)
    return FetchedItem(
        title=str(record.get("title") or ""),
        source_tier=tier,
        authors=tuple(_creators(record))[:10],
        year=_year_from_iso(record.get("publicationDate")),
        doi=_str_or_none(record.get("doi")),
        issn=_str_or_none(record.get("issn")) or _str_or_none(record.get("eIssn")),
        isbn=_str_or_none(record.get("isbn")),
        venue=_str_or_none(record.get("publicationName")),
        language=str(record.get("language") or "en"),
        is_oa=record.get("openaccess") in {"true", True},
        url=landing,
        url_for_pdf=pdf,
    )


def _creators(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for c in record.get("creators") or []:
        if isinstance(c, dict) and c.get("creator"):
            out.append(str(c["creator"]))
    return out


def _urls(record: dict[str, Any]) -> tuple[str | None, str | None]:
    landing: str | None = None
    pdf: str | None = None
    for entry in record.get("url") or []:
        if not isinstance(entry, dict):
            continue
        value = entry.get("value")
        if not isinstance(value, str) or not value:
            continue
        if entry.get("format") == "pdf":
            pdf = value
        elif landing is None:
            landing = value
    return landing, pdf


def _year_from_iso(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
