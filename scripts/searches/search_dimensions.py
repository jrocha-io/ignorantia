#!/usr/bin/env python3
"""
search_dimensions.py — Dimensions Free Tier (Digital Science).

Dimensions é uma base bibliográfica abrangente da Digital Science (~140M publicações)
com indicadores únicos: FWCI (Field-Weighted Citation Impact), Altmetric Attention
Score, Relative Citation Ratio (RCR), funding info. Reviewers Q1 esperam ver indicadores
bibliométricos quando o paper discute "impacto" ou "trending".

API: Dimensions oferece **Free Tier** com queries limitadas (sem chave) + tier
acadêmico gratuito mediante cadastro institucional. Esta v2.11.0 implementa Free
Tier público.

Limitação: Free Tier limita ~1000 queries/mês por IP, não retorna full-text URLs
para itens não-OA, e tem rate de ~5 req/min. Adapter declara cobertura honesta.

Cobertura sobreposta com OpenAlex e Crossref. Diferencial: indicadores FWCI, Altmetrics,
e funding linkage.
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

API = "https://app.dimensions.ai/discover/publication"

DEFAULT_THROTTLE = 12.0  # ~5 req/min limite no Free Tier
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "dimensions", "source_tier": "tier2",
        "method": "DIMENSIONS_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Citation impact of digital health literacy research",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.0000/dimensions-mock-001",
                "venue": "Journal of Medical Internet Research",
                "language": "en",
                "is_oa": True,
                "url": "https://app.dimensions.ai/details/publication/pub.MOCK001",
                "fwci": 2.45,
                "altmetric_score": 28,
                "relative_citation_ratio": 1.78,
                "times_cited": 42,
                "funding": ["NIH (R01)", "NSF"],
            },
            {
                "title": "[mock] Bibliometric analysis of mHealth literature",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.0000/dimensions-mock-002",
                "venue": "Scientometrics",
                "language": "en",
                "is_oa": False,
                "url": "https://app.dimensions.ai/details/publication/pub.MOCK002",
                "fwci": 1.12,
                "altmetric_score": 5,
                "relative_citation_ratio": 0.92,
                "times_cited": 11,
                "funding": [],
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          api_key: str | None,
          throttle: float, timeout: float) -> dict:
    # Dimensions Free Tier: usa API DSL via app.dimensions.ai com autenticação opcional
    # via Authorization header. Sem chave, retorna apenas previewdata limitada.
    # Para queries reais, usuário precisa registro acadêmico em https://www.dimensions.ai/
    if not api_key:
        return {
            "source": "dimensions", "source_tier": "tier2",
            "method": "DIMENSIONS_REAL_NO_KEY",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "results": [],
            "note": ("Dimensions Free Tier requer chave de API (cadastro acadêmico "
                     "gratuito em https://www.dimensions.ai/). Defina DIMENSIONS_API_KEY "
                     "no ambiente ou passe --api-key. Sem chave, este adapter declara "
                     "cobertura indisponível em vez de buscar parcialmente. Cobertura "
                     "sobreposta com OpenAlex e Crossref está garantida por outros adapters."),
        }
    # Modo real com chave: DSL de Dimensions
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"JWT {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    dsl = (f'search publications for "{query}" '
           f'where year in [{year_start}:{year_end}] '
           f'return publications[basics+altmetric+citations] '
           f'limit {min(max_results, 100)}')
    if not (year_start and year_end):
        dsl = (f'search publications for "{query}" '
               f'return publications[basics+altmetric+citations] '
               f'limit {min(max_results, 100)}')
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(
            "https://app.dimensions.ai/api/dsl/v2",
            data=json.dumps({"query": dsl}).encode("utf-8"),
            headers=headers, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for pub in (data.get("publications") or [])[:max_results]:
            authors = [a.get("first_name", "") + " " + a.get("last_name", "")
                       for a in (pub.get("authors") or [])][:10]
            results.append({
                "title": pub.get("title"),
                "authors": [a.strip() for a in authors if a.strip()],
                "year": pub.get("year"),
                "doi": pub.get("doi"),
                "venue": (pub.get("journal") or {}).get("title"),
                "language": "en",
                "is_oa": (pub.get("open_access") in ("oa_all", "hybrid", "gold", "green")),
                "url": (f"https://app.dimensions.ai/details/publication/{pub.get('id')}"
                        if pub.get("id") else None),
                "fwci": pub.get("field_citation_ratio"),
                "altmetric_score": (pub.get("altmetric") or {}).get("score"),
                "relative_citation_ratio": pub.get("relative_citation_ratio"),
                "times_cited": pub.get("times_cited"),
            })
        return {
            "source": "dimensions", "source_tier": "tier2", "method": "DIMENSIONS_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": (data.get("_stats") or {}).get("total_count", len(results)),
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "dimensions", "source_tier": "tier2",
                "method": "DIMENSIONS_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "dimensions", "source_tier": "tier2", "method": "DIMENSIONS_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           api_key: str | None = None,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    api_key = api_key or os.environ.get("DIMENSIONS_API_KEY")
    return _real(query, year_start or 0, year_end or 0, max_results, api_key,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Dimensions adapter (Tier 2; bibliometrics).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--api-key", default=None,
                   help="Chave Dimensions; lê DIMENSIONS_API_KEY do ambiente.")
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, api_key=args.api_key)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[dimensions] {n} resultados → {args.output}")
    if r.get("note"):
        print(f"  nota: {r['note'][:140]}")
    return cli_exit_with_error_message(r, "dimensions")


if __name__ == "__main__":
    sys.exit(_cli())
