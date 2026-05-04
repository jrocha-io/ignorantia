#!/usr/bin/env python3
"""
search_redib.py — Red Iberoamericana de Innovación y Conocimiento Científico.

REDIB indexa ~2M registros LATAM com cobertura sobreposta com Redalyc + LA Referencia,
mas com curadoria distinta (foco em journals de impacto regional + indicadores
bibliométricos próprios). Útil para SR ibero-americanas que buscam complemento.

API: https://redib.org/Recursos/Apis (REST com chave gratuita).
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

API = "https://redib.org/api/v1"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "redib", "source_tier": "tier1", "method": "REDIB_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {"title": "[mock] Educación digital en América Latina: revisión",
             "authors": ["Mock, A."], "year": 2023,
             "doi": "10.0000/redib-mock-001",
             "venue": "Revista Iberoamericana de Educación",
             "language": "es", "country": "regional", "is_oa": True,
             "url_for_pdf": "https://redib.org/recurso/MOCK001",
             "redib_id": "REDIB-MOCK-001"},
            {"title": "[mock] Inclusão digital de idosos: estudo comparativo Brasil-México",
             "authors": ["Mock, B."], "year": 2024,
             "doi": "10.0000/redib-mock-002",
             "venue": "Revista Latinoamericana de Tecnologías Educativas",
             "language": "pt", "country": "BR", "is_oa": True,
             "url_for_pdf": "https://redib.org/recurso/MOCK002",
             "redib_id": "REDIB-MOCK-002"},
        ],
    }


def _real(query, year_start, year_end, max_results, api_key, throttle, timeout):
    if not api_key:
        return {"source": "redib", "source_tier": "tier1", "method": "REDIB_REAL_NO_KEY",
                "query": query, "results": [],
                "note": ("REDIB API requer chave gratuita (cadastro em https://redib.org/Recursos/Apis). "
                         "Defina REDIB_API_KEY ou passe --api-key. Cobertura sobreposta com "
                         "search_redalyc.py e search_la_referencia.py.")}
    params = {"q": query, "key": api_key, "format": "json", "limit": max_results}
    if year_start: params["yearFrom"] = year_start
    if year_end: params["yearTo"] = year_end
    url = f"{API}/search?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in (data.get("results") or [])[:max_results]:
            results.append({
                "title": item.get("title"),
                "authors": item.get("authors", []),
                "year": item.get("year"),
                "doi": item.get("doi"),
                "venue": item.get("journal_title"),
                "language": item.get("language", "es"),
                "country": item.get("country"),
                "is_oa": True,
                "url_for_pdf": item.get("url"),
                "redib_id": item.get("id"),
            })
        return {"source": "redib", "source_tier": "tier1", "method": "REDIB_REAL",
                "query": query, "total_results": data.get("total", len(results)),
                "results": results}
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "redib", "source_tier": "tier1", "method": "REDIB_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query, year_start=None, year_end=None, max_results=100, mock=False,
           api_key=None, throttle=DEFAULT_THROTTLE, timeout=DEFAULT_TIMEOUT):
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    api_key = api_key or os.environ.get("REDIB_API_KEY")
    return _real(query, year_start or 0, year_end or 0, max_results, api_key, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="REDIB adapter (Tier 1; ibero-americana).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--api-key", default=None)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, api_key=args.api_key)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[redib] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "redib")


if __name__ == "__main__":
    sys.exit(_cli())
