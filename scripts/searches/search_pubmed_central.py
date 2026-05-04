#!/usr/bin/env python3
"""
search_pubmed_central.py — Adapter para PubMed Central via NCBI E-utilities.

PubMed Central (PMC) é o repositório OA full-text de literatura biomédica do NIH.
~9M artigos full-text OA; complementa MEDLINE/PubMed (que é só metadados).

API: NCBI E-utilities (esearch + esummary + efetch).
Endpoint: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/

Política NCBI: rate limit 3 req/s sem chave; 10 req/s com chave (gratuita).
A chave vai em --api-key ou env var NCBI_API_KEY. Email de contato em --contact-email
ou IGNORANTIA_CONTACT_EMAIL (recomendado pela NCBI).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _adapter_base import cli_exit_with_error_message
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

DEFAULT_THROTTLE = 0.4  # 3 req/s sem chave; throttle conservador
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "pubmed_central", "source_tier": "tier1", "method": "PMC_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Digital health literacy in older adults: systematic review",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "pmcid": "PMC0000001", "pmid": "30000001",
                "doi": "10.0000/pmc-mock-001",
                "venue": "BMC Geriatrics",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC0000001/pdf/",
                "license": "cc-by",
            },
            {
                "title": "[mock] Mobile health interventions for elderly: meta-analysis",
                "authors": ["Mock, C."], "year": 2024,
                "pmcid": "PMC0000002", "pmid": "30000002",
                "doi": "10.0000/pmc-mock-002",
                "venue": "JMIR mHealth and uHealth",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC0000002/pdf/",
                "license": "cc-by-nc",
            },
        ],
    }


def _esearch(query: str, year_start: int, year_end: int, retmax: int,
             api_key: str | None, contact_email: str | None,
             throttle: float, timeout: float) -> tuple[list[str], str | None]:
    """Faz esearch para PMC e retorna lista de PMC IDs."""
    term = query
    if year_start and year_end:
        term = f"({term}) AND ({year_start}:{year_end}[pdat])"
    params = {
        "db": "pmc", "term": term, "retmax": retmax, "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key
    if contact_email:
        params["email"] = contact_email
        params["tool"] = "ignorantia-skill"
    url = f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        idlist = (data.get("esearchresult") or {}).get("idlist", []) or []
        return idlist, None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return [], f"esearch error: {exc}"


def _esummary(pmcids: list[str], api_key: str | None, contact_email: str | None,
              throttle: float, timeout: float) -> tuple[dict, str | None]:
    """Recupera metadados resumidos via esummary."""
    if not pmcids:
        return {}, None
    params = {
        "db": "pmc", "id": ",".join(pmcids), "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key
    if contact_email:
        params["email"] = contact_email
        params["tool"] = "ignorantia-skill"
    url = f"{EUTILS}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("result", {}) or {}, None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {}, f"esummary error: {exc}"


def _real(query: str, year_start: int, year_end: int, max_results: int,
          api_key: str | None, contact_email: str | None,
          throttle: float, timeout: float) -> dict:
    pmcids, err = _esearch(query, year_start, year_end, max_results,
                            api_key, contact_email, throttle, timeout)
    if err:
        return {"source": "pubmed_central", "source_tier": "tier1",
                "method": "PMC_REAL_ERROR", "error": err, "query": query, "results": []}
    summary, err2 = _esummary(pmcids[:max_results], api_key, contact_email, throttle, timeout)
    if err2:
        return {"source": "pubmed_central", "source_tier": "tier1",
                "method": "PMC_REAL_PARTIAL", "error": err2,
                "query": query, "pmcids": pmcids, "results": []}
    results = []
    for pmcid in pmcids[:max_results]:
        item = summary.get(pmcid) or {}
        if not item:
            continue
        # NCBI esummary retorna author como lista de dicts {"name": "..."}
        authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
        # DOI vem em articleids (lista de {"idtype": ..., "value": ...})
        doi = next((i["value"] for i in item.get("articleids", [])
                    if i.get("idtype") == "doi"), None)
        pmid = next((i["value"] for i in item.get("articleids", [])
                     if i.get("idtype") == "pmid"), None)
        # Year de pubdate (formato "2023 Jun 15")
        pubdate = item.get("pubdate", "")
        year_pub = None
        if pubdate:
            try:
                year_pub = int(pubdate.split()[0])
            except (ValueError, IndexError):
                pass
        results.append({
            "title": item.get("title"),
            "authors": authors,
            "year": year_pub,
            "pmcid": f"PMC{pmcid}" if not pmcid.startswith("PMC") else pmcid,
            "pmid": pmid,
            "doi": doi,
            "venue": item.get("fulljournalname") or item.get("source"),
            "language": "en",  # PMC indexa quase exclusivamente inglês
            "is_oa": True,
            "url_for_pdf": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf/",
        })
    return {
        "source": "pubmed_central", "source_tier": "tier1", "method": "PMC_REAL",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": len(pmcids),
        "results": results,
    }


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           api_key: str | None = None, contact_email: str | None = None,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    api_key = api_key or os.environ.get("NCBI_API_KEY")
    contact_email = contact_email or os.environ.get("IGNORANTIA_CONTACT_EMAIL")
    return _real(query, year_start or 0, year_end or 0, max_results,
                 api_key, contact_email, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="PubMed Central adapter (Tier 1, NCBI E-utilities).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--api-key", default=None,
                   help="NCBI API key; lê NCBI_API_KEY do ambiente se não passada.")
    p.add_argument("--contact-email", default=None)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, api_key=args.api_key, contact_email=args.contact_email)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[pmc] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "pubmed_central")


if __name__ == "__main__":
    sys.exit(_cli())
