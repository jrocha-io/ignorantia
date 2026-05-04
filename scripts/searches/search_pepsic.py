#!/usr/bin/env python3
"""
search_pepsic.py — Periódicos Eletrônicos em Psicologia (BVS-Psi).

PePSIC é o portal de revistas científicas em psicologia da BVS-Psi (Conselho Federal
de Psicologia + BIREME/OPAS). Cobertura: ~120 revistas brasileiras + ibero-americanas
em psicologia. Para SR de psicologia em PT-BR, é canônico — banca de mestrado/
doutorado em psicologia espera ver.

Site: https://www.pepsic.bvsalud.org/
Endpoint: similar ao LILACS/BVS via portal iAH (Acesso Hierárquico).

Cobertura sobreposta com LILACS (que retorna registros de PePSIC), mas adapter
dedicado torna a declaração explícita ao reviewer/banca.
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

API = "https://pesquisa.bvsalud.org/portal/"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "pepsic", "source_tier": "tier1",
        "method": "PEPSIC_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Psicologia do envelhecimento e tecnologias digitais",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.0000/pepsic-mock-001",
                "venue": "Estudos de Psicologia (Natal)",
                "language": "pt", "country": "BR", "is_oa": True,
                "url_for_pdf": "https://pepsic.bvsalud.org/scielo.php?script=sci_arttext&pid=MOCK001",
                "pepsic_id": "PEPSIC-MOCK-001",
                "subject_area": "psicologia",
            },
            {
                "title": "[mock] Letramento digital e cognição em idosos: revisão integrativa",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.0000/pepsic-mock-002",
                "venue": "Psicologia: Reflexão e Crítica",
                "language": "pt", "country": "BR", "is_oa": True,
                "url_for_pdf": "https://pepsic.bvsalud.org/scielo.php?script=sci_arttext&pid=MOCK002",
                "pepsic_id": "PEPSIC-MOCK-002",
                "subject_area": "psicologia",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # PePSIC compartilha portal iAH com LILACS; filtro por base de dados
    params = {
        "lang": "pt",
        "output": "site",
        "lilacs_filter_database": "INDEXPSI",  # BVS index para psicologia
        "q": query,
        "count": max_results,
    }
    if year_start and year_end:
        params["filter[year]"] = f"{year_start}-{year_end}"
    qs = urllib.parse.urlencode(params)
    url = f"{API}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # C3 (v2.22.0): reusa parser do LILACS (mesma estrutura BVS).
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from search_lilacs import _parse_bvs_html
            parsed_items = _parse_bvs_html(raw, year_start, year_end)
            # Normalizar source no item (LILACS parser não preenche)
            for item in parsed_items:
                item["source_indexer"] = "PePSIC"
                item["country"] = "BR"  # PePSIC é predominantemente brasileiro
                item["subject_area"] = "psicologia"
        except ImportError:
            parsed_items = []
        return {
            "source": "pepsic", "source_tier": "tier1", "method": "PEPSIC_REAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "year_range": [year_start, year_end],
            "raw_size_bytes": len(raw), "url_consulted": url,
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
            "note": ("Parser BVS iAH reusado de search_lilacs._parse_bvs_html. "
                     "PePSIC tem cobertura sobreposta com LILACS via portal BVS regional; "
                     "deduplicação por título+autor recomendada downstream."),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "pepsic", "source_tier": "tier1", "method": "PEPSIC_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="PePSIC adapter (Tier 1; psicologia BR/LATAM).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[pepsic] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "pepsic")


if __name__ == "__main__":
    sys.exit(_cli())
