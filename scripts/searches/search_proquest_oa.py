#!/usr/bin/env python3
"""
search_proquest_oa.py — ProQuest Open Access subset.

ProQuest é uma das maiores agregadoras de teses, dissertações e periódicos —
amplamente usada por bibliotecas universitárias. Full ProQuest é fully paywall.

ProQuest oferece **PQDT Open** (Open Access subset de teses/dissertações) e
**ProQuest Open Access ETDs** com subset de teses OA. Esta v2.11.0 implementa
busca pública limitada ao subset OA via interface PQDT.

Site OA: https://pqdtopen.proquest.com/

Limitação: ProQuest não tem API REST pública para o subset OA. Adapter faz best-effort
HTTP GET; parser detalhado é TODO. Para SR estrita com cobertura ProQuest completa,
banca brasileira frequentemente exige acesso institucional via Periódicos CAPES
(declarado em priority_0_routing).
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

API = "https://pqdtopen.proquest.com/search.html"

DEFAULT_THROTTLE = 1.5
DEFAULT_TIMEOUT = 30.0


def _mock(query, year_start, year_end):
    return {
        "source": "proquest_oa", "source_tier": "tier1", "method": "PROQUEST_OA_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {"title": "[mock] Digital literacy interventions in elderly: dissertation",
             "authors": ["Mock, A."], "year": 2023,
             "venue": "PQDT Open",
             "language": "en", "is_oa": True,
             "url_for_pdf": "https://pqdtopen.proquest.com/MOCK001",
             "pqdt_id": "PQDT-MOCK-001",
             "thesis_type": "dissertation_doctorate",
             "institution": "[mock] University"},
            {"title": "[mock] mHealth literacy framework: master's thesis",
             "authors": ["Mock, B."], "year": 2024,
             "venue": "PQDT Open",
             "language": "en", "is_oa": True,
             "url_for_pdf": "https://pqdtopen.proquest.com/MOCK002",
             "pqdt_id": "PQDT-MOCK-002",
             "thesis_type": "thesis_master",
             "institution": "[mock] State University"},
        ],
    }


def _real(query, year_start, year_end, max_results, throttle, timeout):
    params = {"q": query}
    if year_start and year_end:
        params["date"] = f"{year_start}-{year_end}"
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {"source": "proquest_oa", "source_tier": "tier1",
                "method": "PROQUEST_OA_REAL_PARTIAL",
                "query": query, "url_consulted": url, "raw_size_bytes": len(raw),
                "results": [],
                "note": ("ProQuest PQDT Open retornou HTML; parser detalhado é TODO. "
                         "Para cobertura ProQuest completa, banca BR pode cobrar acesso "
                         "via Periódicos CAPES (declarado em priority_0_routing).")}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "proquest_oa", "source_tier": "tier1",
                "method": "PROQUEST_OA_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query, year_start=None, year_end=None, max_results=100, mock=False,
           throttle=DEFAULT_THROTTLE, timeout=DEFAULT_TIMEOUT):
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="ProQuest OA adapter (Tier 1; teses/dissertações).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[proquest_oa] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "proquest_oa")


if __name__ == "__main__":
    sys.exit(_cli())
