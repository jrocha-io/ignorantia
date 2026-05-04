#!/usr/bin/env python3
"""
search_eric.py — Adapter para ERIC (Education Resources Information Center).

ERIC é o repositório do U.S. Department of Education. Indexa ~1.9M registros
em educação e ciências sociais correlatas. Subset OA tem full-text PDF gratuito;
restante tem só metadados+abstract (mas isso é Tier 2, não outro adapter).

API: https://api.ies.ed.gov/eric/
Endpoint: GET /?search=...&format=json&fields=...&rows=...&start=...

Este adapter consolida os dois listings antigos do TIER_DATABASES — `eric_oa`
(Tier 1) e `eric_full` (Tier 2). A flag `--oa-only` filtra subset OA.
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

API = "https://api.ies.ed.gov/eric/"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int, oa_only: bool) -> dict:
    return {
        "source": "eric", "source_tier": "tier1" if oa_only else "tier2",
        "method": "ERIC_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "oa_only": oa_only,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Digital literacy curricula for older learners",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "eric_id": "EJ1234567",
                "venue": "Adult Education Quarterly",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://files.eric.ed.gov/fulltext/EJ1234567.pdf",
                "publication_type": "Journal Articles",
            },
            {
                "title": "[mock] Adult education and technology adoption",
                "authors": ["Mock, C."], "year": 2024,
                "eric_id": "EJ1234568",
                "venue": "Journal of Adult Learning",
                "language": "en",
                "is_oa": False if not oa_only else True,
                "url_for_pdf": None if not oa_only else "https://files.eric.ed.gov/fulltext/EJ1234568.pdf",
                "publication_type": "Journal Articles",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          oa_only: bool, throttle: float, timeout: float) -> dict:
    # ERIC sintaxe: search=text + AND publicationdateyear:[YYYY TO YYYY]
    search_q = query
    if year_start and year_end:
        search_q += f' AND publicationdateyear:["{year_start}" TO "{year_end}"]'
    if oa_only:
        search_q += " AND peerreviewed:T AND publicationtype:\"Journal Articles\""
    params = {
        "search": search_q,
        "format": "json",
        "rows": min(max_results, 200),
        "start": 0,
        "fields": ("title,author,publicationdateyear,publicationtype,description,"
                   "source,peerreviewed,id,url,issn,e_yearadded"),
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        docs = (data.get("response") or {}).get("docs", []) or []
        results = []
        for d in docs[:max_results]:
            authors = d.get("author") or []
            if isinstance(authors, str):
                authors = [authors]
            year_pub = None
            try:
                year_pub = int(d.get("publicationdateyear", 0))
            except (ValueError, TypeError):
                pass
            eric_id = d.get("id", "")
            url_pdf = None
            if eric_id:
                # Heurística: ERIC oferece PDF para registros com prefixo EJ ou ED
                # quando peerreviewed=T e arquivo está hospedado.
                # URL canônica é files.eric.ed.gov/fulltext/{ID}.pdf
                url_pdf = f"https://files.eric.ed.gov/fulltext/{eric_id}.pdf"
            results.append({
                "title": d.get("title"),
                "authors": authors,
                "year": year_pub,
                "eric_id": eric_id,
                "venue": (d.get("source") or [None])[0]
                         if isinstance(d.get("source"), list) else d.get("source"),
                "language": "en",
                "is_oa": d.get("peerreviewed") == "T",
                "url_for_pdf": url_pdf,
                "publication_type": (d.get("publicationtype") or [None])[0]
                                    if isinstance(d.get("publicationtype"), list)
                                    else d.get("publicationtype"),
                "abstract": (d.get("description") or "")[:500],
            })
        total = (data.get("response") or {}).get("numFound", len(results))
        return {
            "source": "eric", "source_tier": "tier1" if oa_only else "tier2",
            "method": "ERIC_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "oa_only": oa_only,
            "total_results": total,
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "eric", "source_tier": "tier1" if oa_only else "tier2",
                "method": "ERIC_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "eric", "source_tier": "tier1" if oa_only else "tier2",
                "method": "ERIC_REAL_ERROR", "error": str(exc), "query": query,
                "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False, oa_only: bool = True,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0, oa_only)
    return _real(query, year_start or 0, year_end or 0, max_results, oa_only,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="ERIC adapter (Tier 1 OA / Tier 2 metadados).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--include-non-oa", action="store_true",
                   help="Incluir registros sem full-text OA (modo Tier 2).")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    oa_only = not args.include_non_oa
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, oa_only=oa_only)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[eric] {n} resultados ({'OA only' if oa_only else 'incluindo non-OA'}) → {args.output}")
    return cli_exit_with_error_message(r, "eric")


if __name__ == "__main__":
    sys.exit(_cli())
