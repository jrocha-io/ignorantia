"""``PubMedAdapter`` — NCBI PubMed via the E-utilities API.

Two-call protocol shared with PubMed Central (PMC) and any other NCBI
E-utilities endpoint:

1. ``esearch.fcgi`` → list of record IDs matching the query
2. ``esummary.fcgi`` → metadata for those IDs

An optional ``api_key`` raises the rate limit; ``contact_email`` enrols
the client into the polite pool.

PubMed Central reuses everything except ``_DB``, the canonical URL
shape, and the ``is_oa`` rule. Subclass and override those three hooks
— see :class:`~ignorantia.infrastructure.search.http.pubmed_central.PubMedCentralAdapter`.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class PubMedAdapter(AdapterPort):
    """Adapter for PubMed via NCBI's E-utilities."""

    source_id = "pubmed"
    source_tier = Tier.TIER2

    _EUTILS: ClassVar[str] = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    _DB: ClassVar[str] = "pubmed"

    def __init__(
        self,
        http: HttpClient,
        *,
        max_results: int = 200,
        api_key: str | None = None,
        contact_email: str | None = None,
    ) -> None:
        """Wire the adapter and configure auth + polite-pool email."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results
        self._api_key = api_key
        self._contact_email = contact_email

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Run esearch then (when there are hits) esummary."""
        ids = self._esearch(query)
        if not ids:
            return self._empty_result(query)
        records = self._esummary(ids)
        items = tuple(self._normalise_record(records[rid], rid) for rid in ids if rid in records)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _empty_result(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
        )

    def _esearch(self, query: SearchQuery) -> list[str]:
        term = query.text
        if query.year_start is not None and query.year_end is not None:
            term = f"({term}) AND ({query.year_start}:{query.year_end}[pdat])"
        params = self._common_params({"term": term, "retmax": str(self._max_results)})
        url = f"{self._EUTILS}/esearch.fcgi?{urlencode(params)}"
        body = self._http.get(url)
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
        result = payload.get("esearchresult")
        if not isinstance(result, dict):
            return []
        idlist = result.get("idlist") or []
        return [rid for rid in idlist if isinstance(rid, str)][: self._max_results]

    def _esummary(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        params = self._common_params({"id": ",".join(ids)})
        url = f"{self._EUTILS}/esummary.fcgi?{urlencode(params)}"
        body = self._http.get(url)
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
        result = payload.get("result")
        if not isinstance(result, dict):
            return {}
        return {rid: rec for rid, rec in result.items() if isinstance(rec, dict)}

    def _common_params(self, extra: dict[str, str]) -> dict[str, str]:
        params: dict[str, str] = {"db": self._DB, "retmode": "json"}
        if self._api_key:
            params["api_key"] = self._api_key
        if self._contact_email:
            params["email"] = self._contact_email
            params["tool"] = "ignorantia-skill"
        params.update(extra)
        return params

    def _normalise_record(self, record: dict[str, Any], record_id: str) -> FetchedItem:
        """Map an E-utilities ``esummary`` record to a :class:`FetchedItem`.

        Subclasses customise via :meth:`_canonical_url`,
        :meth:`_pdf_url_from_record`, and :meth:`_record_is_oa`.
        """
        article_ids = record.get("articleids") or []
        doi = _id_value(article_ids, "doi")
        pmcid = _id_value(article_ids, "pmc")
        return FetchedItem(
            title=str(record.get("title") or ""),
            source_tier=self.source_tier,
            authors=tuple(_authors(record)),
            year=_year_from_pubdate(record.get("pubdate")),
            doi=doi,
            venue=str(record.get("fulljournalname") or record.get("source") or "") or None,
            language=_language(record),
            is_oa=self._record_is_oa(record, pmcid),
            url=self._canonical_url(record_id),
            url_for_pdf=self._pdf_url_from_record(pmcid),
            publication_type=_first_pub_type(record),
        )

    def _canonical_url(self, record_id: str) -> str | None:
        return f"https://pubmed.ncbi.nlm.nih.gov/{record_id}/"

    def _pdf_url_from_record(self, pmcid: str | None) -> str | None:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else None

    def _record_is_oa(self, record: dict[str, Any], pmcid: str | None) -> bool:
        del record
        return bool(pmcid)


def _authors(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for a in record.get("authors") or []:
        if isinstance(a, dict) and a.get("name"):
            out.append(str(a["name"]))
    return out


def _id_value(article_ids: list[Any], idtype: str) -> str | None:
    for entry in article_ids:
        if isinstance(entry, dict) and entry.get("idtype") == idtype and entry.get("value"):
            return str(entry["value"])
    return None


def _year_from_pubdate(value: object) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    head = value.split()[0] if value.split() else ""
    return int(head) if head.isdigit() else None


def _language(record: dict[str, Any]) -> str:
    lang = record.get("lang")
    if isinstance(lang, list) and lang:
        return str(lang[0])
    if isinstance(lang, str) and lang:
        return lang
    return "en"


def _first_pub_type(record: dict[str, Any]) -> str | None:
    pub = record.get("pubtype")
    if isinstance(pub, list) and pub and isinstance(pub[0], str):
        return pub[0]
    if isinstance(pub, str) and pub:
        return pub
    return None
