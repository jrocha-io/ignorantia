#!/usr/bin/env python3
"""
search_scioteca.py — Adapter para Scioteca (CAF — Banco de Desarrollo de América Latina).

Scioteca é o repositório institucional de conhecimento do CAF (Corporación Andina de
Fomento), agregando estudos econômicos, sociais e de desenvolvimento sobre a América
Latina. Conteúdo OA, frequentemente cinza (gray literature) — relatórios técnicos,
working papers, livros institucionais.

Site: https://scioteca.caf.com/
Endpoint público: HTML search; OAI-PMH disponível.

Crítico para revisões em economia do desenvolvimento, políticas públicas e
infraestrutura latino-americana — fontes que journals tradicionais não indexam.
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

API_SEARCH = "https://scioteca.caf.com/discover"



def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "scioteca", "source_tier": "tier1", "method": "SCIOTECA_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Brecha digital y desarrollo en América Latina: informe regional",
                "authors": ["CAF — Banco de Desarrollo de América Latina"], "year": 2023,
                "type": "technical_report",
                "venue": "CAF — Estudios sobre Economía Digital",
                "country": "regional", "language": "es", "is_oa": True,
                "url": "https://scioteca.caf.com/handle/123456789/mock-001",
                "license": "cc-by-nc-sa",
            },
            {
                "title": "[mock] Inclusão digital de adultos: estudo de caso multi-país",
                "authors": ["CAF Working Paper Series"], "year": 2024,
                "type": "working_paper",
                "venue": "CAF — Working Paper",
                "country": "regional", "language": "pt", "is_oa": True,
                "url": "https://scioteca.caf.com/handle/123456789/mock-002",
                "license": "cc-by-nc-sa",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {"query": query, "rpp": max_results}
    qs = urllib.parse.urlencode(params)
    url = f"{API_SEARCH}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {
            "source": "scioteca", "source_tier": "tier1", "method": "SCIOTECA_REAL_PARTIAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "raw_size_bytes": len(raw), "url_consulted": url, "results": [],
            "note": "Real fetch retornou HTML; parser detalhado é TODO.",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "scioteca", "source_tier": "tier1", "method": "SCIOTECA_REAL_ERROR",
                "error": str(exc), "query": query}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = 1.0, timeout: float = 30.0) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Scioteca (CAF) search adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[scioteca] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "scioteca")


if __name__ == "__main__":
    sys.exit(_cli())
