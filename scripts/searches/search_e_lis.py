#!/usr/bin/env python3
"""
search_e_lis.py — E-LIS (E-prints in Library and Information Science).

E-LIS é o repositório OA internacional de biblioteconomia e ciência da informação,
~25k registros. Sem ser de uso massivo, é referência canônica para SR em LIS/CI.

Site: http://eprints.rclis.org/
API: OAI-PMH em http://eprints.rclis.org/cgi/oai2
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

API = "http://eprints.rclis.org/cgi/search/archive/simple"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query, year_start, year_end):
    return {
        "source": "e_lis", "source_tier": "tier1", "method": "E_LIS_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {"title": "[mock] Library services for digital literacy in older adults",
             "authors": ["Mock, A."], "year": 2023,
             "venue": "E-LIS preprint",
             "language": "en", "is_oa": True,
             "url_for_pdf": "http://eprints.rclis.org/MOCK001/",
             "e_lis_id": "ELIS-MOCK-001",
             "subject_area": "library_information_science"},
            {"title": "[mock] Information literacy frameworks: a synthesis",
             "authors": ["Mock, B."], "year": 2024,
             "venue": "E-LIS preprint",
             "language": "en", "is_oa": True,
             "url_for_pdf": "http://eprints.rclis.org/MOCK002/",
             "e_lis_id": "ELIS-MOCK-002",
             "subject_area": "library_information_science"},
        ],
    }


def _real(query, year_start, year_end, max_results, throttle, timeout):
    params = {"q": query, "_action_search": "Search"}
    if year_start: params["date"] = f"{year_start}-{year_end or year_start}"
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {"source": "e_lis", "source_tier": "tier1", "method": "E_LIS_REAL_PARTIAL",
                "query": query, "url_consulted": url, "raw_size_bytes": len(raw),
                "results": [],
                "note": "E-LIS retornou HTML EPrints; parser detalhado é TODO. OAI-PMH alternativo."}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "e_lis", "source_tier": "tier1", "method": "E_LIS_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query, year_start=None, year_end=None, max_results=100, mock=False,
           throttle=DEFAULT_THROTTLE, timeout=DEFAULT_TIMEOUT):
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="E-LIS adapter (Tier 1; biblioteconomia/CI).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[e_lis] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "e_lis")


if __name__ == "__main__":
    sys.exit(_cli())
