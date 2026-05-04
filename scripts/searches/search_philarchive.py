#!/usr/bin/env python3
"""
search_philarchive.py — PhilArchive (PhilPapers, filosofia OA).

PhilArchive é o repositório principal de filosofia OA, parte do PhilPapers (Centre
for Digital Philosophy, Western University). Para SR de filosofia/ética, é canônico.

API: https://philpapers.org/api.html (JSON via parâmetro export=json).
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

API = "https://philpapers.org/s/all"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "philarchive", "source_tier": "tier1", "method": "PHILARCHIVE_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {"title": "[mock] Ética e tecnologia: revisão analítica",
             "authors": ["Mock, A."], "year": 2023,
             "doi": "10.0000/philarchive-mock-001",
             "venue": "Mind",
             "language": "en", "is_oa": True,
             "url_for_pdf": "https://philarchive.org/archive/MOCK001",
             "phil_category": "Ethics"},
            {"title": "[mock] Phenomenology of digital experience",
             "authors": ["Mock, B."], "year": 2024,
             "doi": "10.0000/philarchive-mock-002",
             "venue": "Synthese",
             "language": "en", "is_oa": True,
             "url_for_pdf": "https://philarchive.org/archive/MOCK002",
             "phil_category": "Phenomenology"},
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {"q": query, "export": "json", "limit": min(max_results, 100)}
    if year_start: params["start_year"] = year_start
    if year_end: params["end_year"] = year_end
    url = f"{API}?{urllib.parse.urlencode(params)}"
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
                "authors": item.get("authors") or [],
                "year": item.get("year"),
                "doi": item.get("doi"),
                "venue": item.get("publication") or item.get("source"),
                "language": item.get("language", "en"),
                "is_oa": bool(item.get("archive_url")),
                "url_for_pdf": item.get("archive_url"),
                "phil_category": item.get("category"),
            })
        return {"source": "philarchive", "source_tier": "tier1", "method": "PHILARCHIVE_REAL",
                "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
                "total_results": data.get("total", len(results)), "results": results}
    except urllib.error.HTTPError as exc:
        return {"source": "philarchive", "source_tier": "tier1",
                "method": "PHILARCHIVE_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "philarchive", "source_tier": "tier1",
                "method": "PHILARCHIVE_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query, year_start=None, year_end=None, max_results=100, mock=False,
           throttle=DEFAULT_THROTTLE, timeout=DEFAULT_TIMEOUT):
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="PhilArchive adapter (Tier 1; filosofia OA).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[philarchive] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "philarchive")


if __name__ == "__main__":
    sys.exit(_cli())
