"""``DimensionsAdapter`` — Dimensions DSL via Digital Science.

Tier-2 paywall. Dimensions Free Tier is gated behind a JWT key
obtained via free academic registration at
``https://www.dimensions.ai``. The adapter POSTs a DSL query to
``app.dimensions.ai/api/dsl/v2`` with ``Authorization: JWT <key>``.
Without a key, the cascade falls through to ``Method.REAL_ERROR``.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class DimensionsAdapter(_PaywallAdapter):
    """Adapter for Dimensions' DSL POST endpoint."""

    source_id = "dimensions"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://app.dimensions.ai/api/dsl/v2"
    _PAGE_CAP: ClassVar[int] = 100

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        body = self._http.post(
            self._API_URL,
            data=self._build_body(query),
            headers={
                "Authorization": f"JWT {self._api_key or ''}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        return tuple(
            _normalise(p, self.source_tier) for p in _parse_publications(body, self._max_results)
        )

    def _build_body(self, query: SearchQuery) -> bytes:
        limit = min(self._max_results, self._PAGE_CAP)
        if query.year_start is not None and query.year_end is not None:
            dsl = (
                f'search publications for "{query.text}" '
                f"where year in [{query.year_start}:{query.year_end}] "
                f"return publications[basics+altmetric+citations] "
                f"limit {limit}"
            )
        else:
            dsl = (
                f'search publications for "{query.text}" '
                f"return publications[basics+altmetric+citations] "
                f"limit {limit}"
            )
        return json.dumps({"query": dsl}).encode("utf-8")


def _parse_publications(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("publications") or []
    return [p for p in raw[:limit] if isinstance(p, dict)]


def _normalise(pub: dict[str, Any], tier: Tier) -> FetchedItem:
    journal = pub.get("journal")
    venue = None
    if isinstance(journal, dict):
        venue = _str_or_none(journal.get("title"))
    pub_id = _str_or_none(pub.get("id"))
    return FetchedItem(
        title=str(pub.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(pub))[:10],
        year=_safe_int(pub.get("year")),
        doi=_str_or_none(pub.get("doi")),
        venue=venue,
        language="en",
        is_oa=False,
        url=f"https://app.dimensions.ai/details/publication/{pub_id}" if pub_id else None,
        publication_type="journal-article",
    )


def _authors(pub: dict[str, Any]) -> list[str]:
    raw = pub.get("authors") or []
    out: list[str] = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        first = str(a.get("first_name") or "").strip()
        last = str(a.get("last_name") or "").strip()
        full = f"{first} {last}".strip()
        if full:
            out.append(full)
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
