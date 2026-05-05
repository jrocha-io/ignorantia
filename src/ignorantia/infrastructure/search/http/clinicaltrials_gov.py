"""``ClinicalTrialsGovAdapter`` — NIH ClinicalTrials.gov v2 API.

Tier-1 source. PRISMA-2020 item 6 cites trial-registry searching as
mandatory for SRs of interventions, both to surface ongoing studies
and to detect publication bias (registered but unpublished trials).
The adapter uses the public v2 REST API (no key required) and yields
``trial-registration`` records keyed by NCT ID.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class ClinicalTrialsGovAdapter(AdapterPort):
    """Adapter for ClinicalTrials.gov ``api/v2/studies`` endpoint."""

    source_id = "clinicaltrials_gov"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://clinicaltrials.gov/api/v2/studies"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from CT.gov (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        studies = _parse_studies(body, self._max_results)
        items = tuple(_normalise(s, self.source_tier) for s in studies)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        params: dict[str, str] = {
            "query.term": query.text,
            "pageSize": str(min(self._max_results, self._PAGE_CAP)),
            "format": "json",
        }
        if query.year_start is not None and query.year_end is not None:
            params["filter.advanced"] = (
                f"AREA[StartDate]RANGE[{query.year_start:04d}-01-01,{query.year_end:04d}-12-31]"
            )
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_studies(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("studies") or []
    return [s for s in raw[:limit] if isinstance(s, dict)]


def _normalise(study: dict[str, Any], tier: Tier) -> FetchedItem:
    protocol = study.get("protocolSection")
    proto: dict[str, Any] = protocol if isinstance(protocol, dict) else {}
    ident = _section(proto, "identificationModule")
    status = _section(proto, "statusModule")
    nct_id = _str_or_none(ident.get("nctId"))
    return FetchedItem(
        title=str(ident.get("briefTitle") or ""),
        source_tier=tier,
        year=_year_from_iso(_section(status, "startDateStruct").get("date")),
        venue="ClinicalTrials.gov",
        language="en",
        is_oa=True,
        url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None,
        publication_type="trial-registration",
    )


def _section(parent: dict[str, Any], name: str) -> dict[str, Any]:
    block = parent.get(name)
    return block if isinstance(block, dict) else {}


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
