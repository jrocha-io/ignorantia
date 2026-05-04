#!/usr/bin/env python3
"""
search_europepmc.py — Adapter para Europe PMC REST API.

Europe PMC é o mirror europeu do PubMed Central, mantido por European Bioinformatics
Institute. Cobertura semelhante (~9M full-text OA + ~40M registros de metadados)
mas com endpoints REST mais limpos que o E-utilities da NCBI.

API: https://europepmc.org/RestfulWebService
Endpoint: https://www.ebi.ac.uk/europepmc/webservices/rest/search

Sem rate limit declarado (uso responsável); sem chave de API.
"""
from __future__ import annotations

import argparse
import json
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

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "europepmc", "source_tier": "tier1", "method": "EUROPEPMC_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] eHealth literacy interventions: European cohort",
                "authors": ["Mock, D.", "Mock, E."], "year": 2023,
                "pmid": "30100001", "pmcid": "PMC0100001",
                "doi": "10.0000/europepmc-mock-001",
                "venue": "BMJ Open",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://europepmc.org/article/PMC0100001",
            },
            {
                "title": "[mock] Aging and digital health: scoping review",
                "authors": ["Mock, F."], "year": 2024,
                "pmid": "30100002",
                "doi": "10.0000/europepmc-mock-002",
                "venue": "Age and Ageing",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://europepmc.org/article/MED/30100002",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # Europe PMC usa sintaxe Lucene; PUB_YEAR field para filtro temporal
    q = query
    if year_start and year_end:
        q = f"({q}) AND PUB_YEAR:[{year_start} TO {year_end}]"
    params = {
        "query": q,
        "format": "json",
        "pageSize": min(max_results, 100),
        "resultType": "core",  # metadados + abstract
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in (data.get("resultList") or {}).get("result", [])[:max_results]:
            authors_raw = item.get("authorString", "")
            authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
            year_pub = None
            try:
                year_pub = int(item.get("pubYear", 0))
            except (ValueError, TypeError):
                pass
            pmcid = item.get("pmcid")
            pmid = item.get("pmid")
            url_pdf = None
            if pmcid:
                url_pdf = f"https://europepmc.org/article/PMC/{pmcid}"
            elif pmid:
                url_pdf = f"https://europepmc.org/article/MED/{pmid}"
            results.append({
                "title": item.get("title"),
                "authors": authors,
                "year": year_pub,
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": item.get("doi"),
                "venue": item.get("journalTitle"),
                "language": "en",
                "is_oa": (item.get("isOpenAccess", "N") == "Y"),
                "url_for_pdf": url_pdf,
                "abstract": item.get("abstractText", "")[:500],
            })
        return {
            "source": "europepmc", "source_tier": "tier1", "method": "EUROPEPMC_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": data.get("hitCount", len(results)),
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "europepmc", "source_tier": "tier1",
                "method": "EUROPEPMC_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "europepmc", "source_tier": "tier1", "method": "EUROPEPMC_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Europe PMC adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[europepmc] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "europepmc")


if __name__ == "__main__":
    sys.exit(_cli())
