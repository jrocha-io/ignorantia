#!/usr/bin/env python3
"""
search_core.py — Adapter para CORE API (Open University UK).

CORE agrega ~280M de artigos OA de repositórios institucionais e revistas em todo
o mundo. É a maior fonte agregadora de full-text OA legítimo, complementar ao
Unpaywall e Open Access Button.

API: https://api.core.ac.uk/v3/
Documentação: https://core.ac.uk/services/api
Autenticação: API key gratuita (rate limit 10 req/min sem key, 50 req/min com key);
key obtida em https://core.ac.uk/services/api#registering

POLÍTICA da v2.9.0 (Decisão 24): CORE entra como Tier 0 secundário, junto com
Unpaywall + OAB. A chave de API é opcional (modo unauthenticated funciona com rate
mais baixo); quando disponível, lê de --core-api-key ou IGNORANTIA_CORE_API_KEY.
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

API_BASE = "https://api.core.ac.uk/v3"

DEFAULT_THROTTLE = 1.5  # rate limit conservador sem key
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "core", "source_tier": "tier0", "method": "CORE_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Digital literacy in older adults: a meta-analytic review",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.0000/core-mock-001",
                "venue": "International Journal of Educational Research",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://core.ac.uk/download/pdf/mock-001.pdf",
                "repository": "Open Repository (mock)",
            },
            {
                "title": "[mock] Adult digital education: cross-cultural perspectives",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.0000/core-mock-002",
                "venue": "Computers & Education",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://core.ac.uk/download/pdf/mock-002.pdf",
                "repository": "Institutional Repository (mock)",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          api_key: str | None, throttle: float, timeout: float) -> dict:
    """Consulta a CORE Search API v3 (POST /search/works)."""
    body = {
        "q": query,
        "limit": min(max_results, 100),
        "scroll": False,
    }
    if year_start and year_end:
        body["q"] = f"({query}) AND yearPublished>={year_start} AND yearPublished<={year_end}"
    url = f"{API_BASE}/search/works"
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title"),
                "authors": [a.get("name") for a in (item.get("authors") or []) if a.get("name")],
                "year": item.get("yearPublished"),
                "doi": item.get("doi"),
                "venue": (item.get("publisher") or
                          (item.get("journals") or [{}])[0].get("title") if item.get("journals") else None),
                "language": (item.get("language") or {}).get("code") if isinstance(item.get("language"), dict) else None,
                "is_oa": True,  # CORE só indexa OA
                "url_for_pdf": item.get("downloadUrl"),
                "repository": (item.get("dataProviders") or [{}])[0].get("name") if item.get("dataProviders") else None,
            })
        return {
            "source": "core", "source_tier": "tier0", "method": "CORE_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": data.get("totalHits", len(results)),
            "results": results,
            "authenticated": bool(api_key),
        }
    except urllib.error.HTTPError as exc:
        return {"source": "core", "source_tier": "tier0", "method": "CORE_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "core", "source_tier": "tier0", "method": "CORE_REAL_ERROR",
                "error": str(exc), "query": query}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           api_key: str | None = None,
           throttle: float = DEFAULT_THROTTLE,
           timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    api_key = api_key or os.environ.get("IGNORANTIA_CORE_API_KEY")
    return _real(query, year_start or 0, year_end or 0, max_results, api_key, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="CORE search adapter (Tier 0 — Open University UK).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--core-api-key", default=None,
                   help="Chave da API CORE; lê IGNORANTIA_CORE_API_KEY se não passada.")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, api_key=args.core_api_key)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[core] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "core")


if __name__ == "__main__":
    sys.exit(_cli())
