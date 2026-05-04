#!/usr/bin/env python3
"""
search_jstor_oa.py — JSTOR Open Content (subset OA gratuito).

JSTOR é a base canônica de humanidades e ciências sociais. ~10M de artigos no total;
desses, **JSTOR Open Content** disponibiliza ~9k livros + ~12 journals + Early Journal
Content (artigos pré-1924) gratuitamente.

Para humanidades e ciências sociais, citar JSTOR é **expectativa cultural** dos
reviewers. O subset OA cobre 5-10% do total; full JSTOR continua paywall.

API: JSTOR Labs Open Access API + Constellate (data mining text). Sem chave para
o subset OA básico.
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

API = "https://labs.jstor.org/api/v1/search"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "jstor_oa", "source_tier": "tier1", "method": "JSTOR_OA_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Aging societies and digital transformation: a sociological essay",
                "authors": ["Mock, A."], "year": 2022,
                "doi": "10.0000/jstor-mock-001",
                "jstor_id": "i12345678",
                "venue": "American Sociological Review",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://www.jstor.org/stable/MOCK001",
                "resource_type": "journal-article",
                "subjects": ["Sociology", "Aging"],
                "is_early_journal_content": False,
            },
            {
                "title": "[mock] Letramento na era digital",
                "authors": ["Mock, B."], "year": 2023,
                "doi": "10.0000/jstor-mock-002",
                "jstor_id": "j87654321",
                "venue": "JSTOR OA Books (Routledge)",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://www.jstor.org/stable/MOCK002",
                "resource_type": "book",
                "subjects": ["Education", "Information Society"],
                "is_early_journal_content": False,
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # JSTOR Labs Open Access endpoint público (best-effort)
    params = {
        "query": query,
        "filter": "open_access",
        "limit": min(max_results, 100),
    }
    if year_start and year_end:
        params["year_from"] = year_start
        params["year_to"] = year_end
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # JSTOR Labs API tem endpoint variável — best-effort parsing
        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("results") or data.get("hits") or []
            results = []
            for item in items[:max_results]:
                results.append({
                    "title": item.get("title"),
                    "authors": item.get("authors") or item.get("creators") or [],
                    "year": item.get("year"),
                    "doi": item.get("doi"),
                    "jstor_id": item.get("id") or item.get("jstor_id"),
                    "venue": item.get("source") or item.get("publication"),
                    "language": item.get("language", "en"),
                    "is_oa": True,
                    "url_for_pdf": item.get("url"),
                    "resource_type": item.get("type", "journal-article"),
                })
            return {
                "source": "jstor_oa", "source_tier": "tier1", "method": "JSTOR_OA_REAL",
                "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
                "total_results": len(results),
                "results": results,
            }
        except (json.JSONDecodeError, AttributeError):
            return {
                "source": "jstor_oa", "source_tier": "tier1",
                "method": "JSTOR_OA_REAL_PARTIAL",
                "query": query, "raw_size_bytes": len(raw), "results": [],
                "note": ("JSTOR Labs API retornou formato não-JSON; parser detalhado é TODO. "
                         "Cobertura OA via Constellate (https://constellate.org) é alternativa "
                         "para data mining. Para uso programático robusto, recomenda-se "
                         "JSTOR Data for Research (acesso institucional)."),
            }
    except urllib.error.HTTPError as exc:
        return {"source": "jstor_oa", "source_tier": "tier1", "method": "JSTOR_OA_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"source": "jstor_oa", "source_tier": "tier1", "method": "JSTOR_OA_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="JSTOR Open Content adapter (Tier 1; humanities/social).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[jstor_oa] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "jstor_oa")


if __name__ == "__main__":
    sys.exit(_cli())
