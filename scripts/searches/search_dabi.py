#!/usr/bin/env python3
"""
search_dabi.py — DABI / Norwegian National Library / Tidsskrift OA.

Para SR de educação nórdica (Suécia, Noruega, Dinamarca, Finlândia, Islândia),
a literatura científica está parcialmente coberta por bases internacionais (ERIC,
Scopus) mas significativa parte está em revistas em línguas nórdicas indexadas
em portais nacionais.

DABI (Dansk Bibliografisk) e Tidsskrift OA (Noruega) cobrem nichos. Este adapter
implementa stub honesto — para SR de educação nórdica seria necessário trabalho
adicional. Modo mock funciona; modo real declara cobertura limitada.

Cobertura sobreposta com search_doaj e search_openalex, mas adapter dedicado
documenta busca específica para revisão Q1 internacional.
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

API = "https://tidsskrift.dk/index/search/search"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query, year_start, year_end):
    return {
        "source": "dabi", "source_tier": "tier1", "method": "DABI_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {"title": "[mock] Digital læring blandt ældre i Danmark",
             "authors": ["Mock, A."], "year": 2023,
             "venue": "Dansk Pædagogisk Tidsskrift",
             "language": "da", "country": "DK", "is_oa": True,
             "url_for_pdf": "https://tidsskrift.dk/MOCK001",
             "dabi_id": "DABI-MOCK-001"},
            {"title": "[mock] Norsk pedagogikk og digitale verktøy",
             "authors": ["Mock, B."], "year": 2024,
             "venue": "Norsk Pedagogisk Tidsskrift",
             "language": "no", "country": "NO", "is_oa": True,
             "url_for_pdf": "https://tidsskrift.dk/MOCK002",
             "dabi_id": "DABI-MOCK-002"},
        ],
    }


def _real(query, year_start, year_end, max_results, throttle, timeout):
    params = {"query": query}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {"source": "dabi", "source_tier": "tier1", "method": "DABI_REAL_PARTIAL",
                "query": query, "url_consulted": url, "raw_size_bytes": len(raw),
                "results": [],
                "note": ("Tidsskrift.dk retornou HTML OJS; parser detalhado é TODO. "
                         "Cobertura sobreposta com search_doaj.py para journals OA nórdicos. "
                         "Para SR de educação nórdica, considerar adapter dedicado por país.")}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "dabi", "source_tier": "tier1", "method": "DABI_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query, year_start=None, year_end=None, max_results=100, mock=False,
           throttle=DEFAULT_THROTTLE, timeout=DEFAULT_TIMEOUT):
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="DABI / Tidsskrift adapter (Tier 1; nórdica).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[dabi] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "dabi")


if __name__ == "__main__":
    sys.exit(_cli())
