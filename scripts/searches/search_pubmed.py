#!/usr/bin/env python3
"""
search_pubmed.py — Adapter para PubMed completo via NCBI E-utilities.

PubMed indexa ~36M registros biomédicos (MEDLINE + PubMed Central + outros), incluindo
a maior parte de literatura clínica peer-reviewed. Diferente do PMC (apenas full-text OA),
PubMed traz metadados de tudo, incluindo abstract na maioria dos casos.

PRISMA-2020 item 6 cita PubMed como base canônica para SR de saúde. Reviewers Q1
assumem PubMed buscado por default — consultar só PMC sinaliza desconhecimento metodológico.

API: NCBI E-utilities (mesma do PMC, com db=pubmed em vez de db=pmc).
Política NCBI: rate limit 3 req/s sem chave; 10 req/s com chave (gratuita).
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

DEFAULT_THROTTLE = 0.4
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "pubmed", "source_tier": "tier2",  # PubMed = metadados livres; full-text via PMC
        "method": "PUBMED_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Digital health literacy: systematic review",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "pmid": "30200001",
                "pmcid": "PMC0200001",
                "doi": "10.0000/pubmed-mock-001",
                "venue": "JMIR Public Health and Surveillance",
                "language": "en",
                "is_oa": True,
                "url": "https://pubmed.ncbi.nlm.nih.gov/30200001/",
                "publication_type": "Review",
                "mesh_terms": ["Health Literacy", "Aged", "Internet"],
            },
            {
                "title": "[mock] Older adults and mHealth: meta-analysis",
                "authors": ["Mock, C."], "year": 2024,
                "pmid": "30200002",
                "doi": "10.0000/pubmed-mock-002",
                "venue": "Patient Education and Counseling",
                "language": "en",
                "is_oa": False,
                "url": "https://pubmed.ncbi.nlm.nih.gov/30200002/",
                "publication_type": "Meta-Analysis",
                "mesh_terms": ["Aged", "Mobile Applications"],
            },
        ],
    }


def _esearch(query: str, year_start: int, year_end: int, retmax: int,
             api_key: str | None, contact_email: str | None,
             throttle: float, timeout: float) -> tuple[list[str], str | None]:
    term = query
    if year_start and year_end:
        term = f"({term}) AND ({year_start}:{year_end}[pdat])"
    params = {"db": "pubmed", "term": term, "retmax": retmax, "retmode": "json"}
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


def _esummary(pmids: list[str], api_key: str | None, contact_email: str | None,
              throttle: float, timeout: float) -> tuple[dict, str | None]:
    if not pmids:
        return {}, None
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
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
    pmids, err = _esearch(query, year_start, year_end, max_results,
                           api_key, contact_email, throttle, timeout)
    if err:
        return {"source": "pubmed", "source_tier": "tier2",
                "method": "PUBMED_REAL_ERROR", "error": err, "query": query, "results": []}
    summary, err2 = _esummary(pmids[:max_results], api_key, contact_email, throttle, timeout)
    if err2:
        return {"source": "pubmed", "source_tier": "tier2",
                "method": "PUBMED_REAL_PARTIAL", "error": err2,
                "query": query, "pmids": pmids, "results": []}
    results = []
    for pmid in pmids[:max_results]:
        item = summary.get(pmid) or {}
        if not item:
            continue
        authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
        doi = next((i["value"] for i in item.get("articleids", [])
                    if i.get("idtype") == "doi"), None)
        pmcid = next((i["value"] for i in item.get("articleids", [])
                      if i.get("idtype") == "pmc"), None)
        pubdate = item.get("pubdate", "")
        year_pub = None
        if pubdate:
            try:
                year_pub = int(pubdate.split()[0])
            except (ValueError, IndexError):
                pass
        pub_types = item.get("pubtype", [])
        if isinstance(pub_types, list) and pub_types:
            publication_type = pub_types[0]
        else:
            publication_type = pub_types or None
        results.append({
            "title": item.get("title"),
            "authors": authors,
            "year": year_pub,
            "pmid": pmid,
            "pmcid": pmcid,
            "doi": doi,
            "venue": item.get("fulljournalname") or item.get("source"),
            "language": (item.get("lang", ["en"]) or ["en"])[0]
                        if isinstance(item.get("lang"), list) else "en",
            "is_oa": bool(pmcid),  # PMC ID indica full-text OA disponível
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "publication_type": publication_type,
        })
    return {
        "source": "pubmed", "source_tier": "tier2", "method": "PUBMED_REAL",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": len(pmids),
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
    p = argparse.ArgumentParser(description="PubMed adapter (Tier 2; NCBI E-utilities).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--api-key", default=None)
    p.add_argument("--contact-email", default=None)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, api_key=args.api_key, contact_email=args.contact_email)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[pubmed] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "pubmed")


if __name__ == "__main__":
    sys.exit(_cli())
