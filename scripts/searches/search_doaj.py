#!/usr/bin/env python3
"""
search_doaj.py — Adapter para DOAJ (Directory of Open Access Journals).

DOAJ indexa ~20k revistas peer-reviewed Open Access em todas as áreas e idiomas.
Curado por critérios de qualidade editorial; obrigatório como Tier 1 multi-área.

API pública: https://doaj.org/api/v3/docs
Endpoint usado: GET https://doaj.org/api/search/articles/{query}
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

API = "https://doaj.org/api/search/articles"



def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "doaj", "source_tier": "tier1", "method": "DOAJ_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Open access publishing in digital literacy research",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.0000/doaj-mock-001",
                "venue": "Journal of Open Educational Research",
                "language": "en", "is_oa": True,
                "url": "https://doaj.org/article/mock-001",
                "license": "cc-by",
            },
            {
                "title": "[mock] Letramento digital: revisão sistemática em acesso aberto",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.0000/doaj-mock-002",
                "venue": "Revista Brasileira de Tecnologias na Educação",
                "language": "pt", "is_oa": True,
                "url": "https://doaj.org/article/mock-002",
                "license": "cc-by-nc",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # DOAJ usa Lucene-style queries; year filtering via bibjson.year
    q_parts = [query]
    if year_start and year_end:
        q_parts.append(f"bibjson.year:[{year_start} TO {year_end}]")
    q = " AND ".join(f"({p})" for p in q_parts)
    url = f"{API}/{urllib.parse.quote(q)}?pageSize={min(max_results, 100)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in data.get("results", [])[:max_results]:
            bj = item.get("bibjson", {})
            authors = [a.get("name") for a in (bj.get("author") or []) if a.get("name")]
            doi = next((i.get("id") for i in (bj.get("identifier") or [])
                        if i.get("type") == "doi"), None)
            url_a = next((l.get("url") for l in (bj.get("link") or [])
                          if l.get("type") == "fulltext"), None)
            results.append({
                "title": bj.get("title"),
                "authors": authors,
                "year": bj.get("year"),
                "doi": doi,
                "venue": (bj.get("journal") or {}).get("title"),
                "language": (bj.get("journal") or {}).get("language", [None])[0]
                            if isinstance((bj.get("journal") or {}).get("language"), list)
                            else (bj.get("journal") or {}).get("language"),
                "is_oa": True,
                "url": url_a,
                "license": ((bj.get("journal") or {}).get("license") or [{}])[0].get("type")
                           if (bj.get("journal") or {}).get("license") else None,
            })
        return {
            "source": "doaj", "source_tier": "tier1", "method": "DOAJ_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": data.get("total", len(results)),
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "doaj", "source_tier": "tier1", "method": "DOAJ_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query,
                "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "doaj", "source_tier": "tier1", "method": "DOAJ_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = 1.0, timeout: float = 30.0) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="DOAJ search adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[doaj] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "doaj")


if __name__ == "__main__":
    sys.exit(_cli())
