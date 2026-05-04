#!/usr/bin/env python3
"""
search_cochrane_central.py — Cochrane Central Register of Controlled Trials (CENTRAL).

CENTRAL é o subset acessível da Cochrane Library, contendo metadados de ensaios
controlados (RCTs + quasi-randomized trials) — ~2.6M registros derivados de PubMed,
Embase, e busca manual de mãos. **Citado pelo nome no PRISMA-2020 + Cochrane Handbook**
como base canônica obrigatória para SR de saúde com componente de intervenção.

Limitação importante: Cochrane Library **não tem API REST pública** para CENTRAL.
A busca pública é via interface web (https://www.cochranelibrary.com/search). Wiley
(que hospeda a Cochrane) oferece API apenas para clientes institucionais via Wiley
Online Library.

Esta v2.11.0 implementa estratégia best-effort:
1. Modo mock determinístico.
2. Modo real: usa o **endpoint de busca da Cochrane Library** (HTML público) e
   extrai trials. Como não é JSON estruturado, parser detalhado é parcial e marcado
   como TODO. CENTRAL trials acessíveis via PubMed (publication type "Randomized
   Controlled Trial") são cobertos via search_pubmed.py com filtro `--filter
   publication-type:RCT` recomendado em paralelo.

Recomendação operacional para SR estrita de saúde: combinar este adapter (modo
parcial) + search_pubmed.py com filtro `pt:Randomized Controlled Trial` para máxima
cobertura.
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

API = "https://www.cochranelibrary.com/search"

DEFAULT_THROTTLE = 1.5  # Cochrane é mais sensível a rate; throttle conservador
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "cochrane_central", "source_tier": "tier1",  # CENTRAL = OA metadados de RCTs
        "method": "COCHRANE_CENTRAL_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] RCT of digital literacy intervention in older adults",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.1002/central.CD000001",
                "central_id": "CN-00000001",
                "venue": "Cochrane Central Register of Controlled Trials",
                "study_type": "Randomized Controlled Trial",
                "language": "en",
                "is_oa": True,  # CENTRAL = registro de metadados OA
                "url": "https://www.cochranelibrary.com/central/doi/10.1002/central.CD000001/full",
            },
            {
                "title": "[mock] Effectiveness of mHealth literacy training: cluster RCT",
                "authors": ["Mock, C.", "Mock, D."], "year": 2024,
                "doi": "10.1002/central.CD000002",
                "central_id": "CN-00000002",
                "venue": "Cochrane Central Register of Controlled Trials",
                "study_type": "Randomized Controlled Trial",
                "language": "en",
                "is_oa": True,
                "url": "https://www.cochranelibrary.com/central/doi/10.1002/central.CD000002/full",
            },
        ],
        "note": "CENTRAL via mock determinístico. Modo real exige web parsing parcial.",
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # Cochrane Library web search retorna HTML. Construímos URL de busca pública;
    # parsing detalhado é TODO. Fallback honesto: declara cobertura via PubMed RCT.
    params = {
        "searchBy": "1",  # search all text
        "searchText": query,
        "selectedType": "trial",  # apenas CENTRAL (trials), não revisões
        "isPRISMA": "true",
    }
    if year_start and year_end:
        params["pubDateFrom"] = f"01/01/{year_start}"
        params["pubDateTo"] = f"31/12/{year_end}"
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {
            "source": "cochrane_central", "source_tier": "tier1",
            "method": "COCHRANE_CENTRAL_REAL_PARTIAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "url_consulted": url, "raw_size_bytes": len(raw),
            "results": [],
            "note": ("Cochrane CENTRAL não tem API REST pública; busca retornou HTML. "
                     "Parser detalhado é TODO. Recomendação operacional: combinar com "
                     "search_pubmed.py filtrado por publication_type=RCT — maior cobertura "
                     "e dados estruturados. CENTRAL é derivada de PubMed + Embase + handsearch."),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        return {"source": "cochrane_central", "source_tier": "tier1",
                "method": "COCHRANE_CENTRAL_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Cochrane CENTRAL adapter (Tier 1; PRISMA-canonical).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[cochrane_central] {n} resultados → {args.output}")
    if r.get("note"):
        print(f"  nota: {r['note'][:120]}")
    return cli_exit_with_error_message(r, "cochrane_central")


if __name__ == "__main__":
    sys.exit(_cli())
