#!/usr/bin/env python3
"""
search_bdtd.py — Adapter para BDTD (Biblioteca Digital Brasileira de Teses e Dissertações).

BDTD é mantida pelo IBICT/MCTI e agrega ~750k teses e dissertações de instituições
brasileiras. Coverage: 100% de programas de pós-graduação federais e a maioria dos
estaduais e privados acreditados.

Site: https://bdtd.ibict.br/vufind/
Endpoint OAI-PMH: https://bdtd.ibict.br/vufind/OAI/Server

Crítico para captura de pesquisa de pós-graduação brasileira (frequentemente fonte
primária para extensões e revisões posteriores em journals).
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

API_SEARCH = "https://bdtd.ibict.br/vufind/Search/Results"
API_OAI = "https://bdtd.ibict.br/vufind/OAI/Server"



def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "bdtd", "source_tier": "tier1", "method": "BDTD_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Letramento digital de idosos em comunidades populares: estudo de caso",
                "authors": ["Pereira, A. C."], "year": 2023,
                "type": "doctoral_thesis",
                "venue": "Programa de Pós-Graduação em Educação, USP",
                "country": "BR", "language": "pt", "is_oa": True,
                "url": "https://bdtd.ibict.br/vufind/Record/USP_mock-001",
                "advisor": "Mock, M. M.",
            },
            {
                "title": "[mock] Acesso a tecnologias digitais entre adultos 60+: dissertação",
                "authors": ["Souza, M. R."], "year": 2022,
                "type": "masters_dissertation",
                "venue": "Programa de Pós-Graduação em Informática Educativa, UFMG",
                "country": "BR", "language": "pt", "is_oa": True,
                "url": "https://bdtd.ibict.br/vufind/Record/UFMG_mock-002",
                "advisor": "Mock, J. A.",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {"lookfor": query, "type": "AllFields", "limit": max_results, "view": "rss"}
    if year_start and year_end:
        params["filter[]"] = f"publishDate:[{year_start} TO {year_end}]"
    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{API_SEARCH}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {
            "source": "bdtd", "source_tier": "tier1", "method": "BDTD_REAL_PARTIAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "raw_size_bytes": len(raw), "url_consulted": url, "results": [],
            "note": "Real fetch retornou RSS XML; parser detalhado é TODO. OAI-PMH é alternativa robusta.",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "bdtd", "source_tier": "tier1", "method": "BDTD_REAL_ERROR",
                "error": str(exc), "query": query}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = 1.0, timeout: float = 30.0) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="BDTD search adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[bdtd] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "bdtd")


if __name__ == "__main__":
    sys.exit(_cli())
