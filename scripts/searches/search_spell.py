#!/usr/bin/env python3
"""
search_spell.py — Spell (Scientific Periodicals Electronic Library, FGV/SPELL).

Spell indexa ~80k artigos brasileiros em administração, contabilidade, turismo,
gestão pública. Foco em business research nacional. Sem API REST pública robusta;
busca via interface web HTML.

Para SR em business research brasileiro (notadamente programas Stricto Sensu em
Administração Qualis A1-A3), é referência cultural esperada.
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

API = "https://www.spell.org.br/documentos/buscaavancada/"

DEFAULT_THROTTLE = 1.5
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "spell", "source_tier": "tier1", "method": "SPELL_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {"title": "[mock] Transformação digital em pequenas empresas: revisão sistemática",
             "authors": ["Mock, A.", "Mock, B."], "year": 2023,
             "venue": "Revista de Administração Contemporânea (RAC)",
             "language": "pt", "country": "BR", "is_oa": True,
             "url_for_pdf": "https://www.spell.org.br/documentos/MOCK001.pdf",
             "spell_id": "SPELL-MOCK-001",
             "subject_area": "administração"},
            {"title": "[mock] Sustentabilidade e indicadores contábeis: meta-análise",
             "authors": ["Mock, C."], "year": 2024,
             "venue": "Revista Contabilidade & Finanças (USP)",
             "language": "pt", "country": "BR", "is_oa": True,
             "url_for_pdf": "https://www.spell.org.br/documentos/MOCK002.pdf",
             "spell_id": "SPELL-MOCK-002",
             "subject_area": "contabilidade"},
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {"q": query, "tipoBusca": "todos"}
    if year_start: params["anoInicial"] = year_start
    if year_end: params["anoFinal"] = year_end
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {"source": "spell", "source_tier": "tier1", "method": "SPELL_REAL_PARTIAL",
                "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
                "url_consulted": url, "raw_size_bytes": len(raw), "results": [],
                "note": "Spell retornou HTML; parser detalhado é TODO. Sem API REST oficial."}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "spell", "source_tier": "tier1", "method": "SPELL_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query, year_start=None, year_end=None, max_results=100, mock=False,
           throttle=DEFAULT_THROTTLE, timeout=DEFAULT_TIMEOUT):
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Spell adapter (Tier 1; business research BR).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[spell] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "spell")


if __name__ == "__main__":
    sys.exit(_cli())
