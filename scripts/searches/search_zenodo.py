#!/usr/bin/env python3
"""
search_zenodo.py — Adapter para Zenodo (CERN — repositório OA multi-disciplinar).

Zenodo é o repositório principal de open data + open access papers + open code
hospedado pelo CERN. ~3M de registros: artigos, datasets, software, working papers,
teses. Crítico para SLR de software engineering (recomendação JOSS) e para captura
de literatura cinza pós-2015.

API: https://developers.zenodo.org/#rest-api
Endpoint: GET https://zenodo.org/api/records
Sem chave para queries; chave necessária só para deposit.
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

API = "https://zenodo.org/api/records"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "zenodo", "source_tier": "tier1", "method": "ZENODO_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] ignorantia v2.10 reproducibility package",
                "authors": ["Mock Author"], "year": 2026,
                "doi": "10.5281/zenodo.MOCK001",
                "venue": "Zenodo",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://zenodo.org/records/MOCK001/files/manuscript.pdf",
                "resource_type": "publication-article",
                "license": "cc-by-4.0",
            },
            {
                "title": "[mock] Open data: digital literacy survey",
                "authors": ["Mock Researcher"], "year": 2025,
                "doi": "10.5281/zenodo.MOCK002",
                "venue": "Zenodo",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://zenodo.org/records/MOCK002/files/data.csv",
                "resource_type": "dataset",
                "license": "cc-0",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          resource_types: list[str] | None,
          throttle: float, timeout: float) -> dict:
    # Zenodo usa Elasticsearch query syntax
    q = query
    if year_start and year_end:
        q = f"({q}) AND publication_date:[{year_start}-01-01 TO {year_end}-12-31]"
    if resource_types:
        types_q = " OR ".join(f'resource_type.type:"{t}"' for t in resource_types)
        q = f"({q}) AND ({types_q})"
    params = {
        "q": q,
        "size": min(max_results, 100),
        "sort": "mostrecent",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in (data.get("hits") or {}).get("hits", [])[:max_results]:
            meta = item.get("metadata", {})
            authors_raw = meta.get("creators", []) or []
            authors = [a.get("name", "") for a in authors_raw if a.get("name")]
            year_pub = None
            pub_date = meta.get("publication_date") or ""
            if pub_date:
                try:
                    year_pub = int(pub_date[:4])
                except ValueError:
                    pass
            doi = meta.get("doi")
            files_url = None
            if item.get("links", {}).get("self_html"):
                files_url = item["links"]["self_html"]
            license_id = (meta.get("license") or {}).get("id")
            results.append({
                "title": meta.get("title"),
                "authors": authors,
                "year": year_pub,
                "doi": doi,
                "venue": "Zenodo",
                "language": (meta.get("language") or "en"),
                "is_oa": (meta.get("access_right") == "open"),
                "url_for_pdf": files_url,
                "resource_type": (meta.get("resource_type") or {}).get("type"),
                "license": license_id,
                "abstract": (meta.get("description") or "")[:500],
            })
        total = (data.get("hits") or {}).get("total", len(results))
        return {
            "source": "zenodo", "source_tier": "tier1", "method": "ZENODO_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": total,
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "zenodo", "source_tier": "tier1", "method": "ZENODO_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "zenodo", "source_tier": "tier1", "method": "ZENODO_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           resource_types: list[str] | None = None,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, resource_types,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Zenodo adapter (Tier 1; CERN OA repository).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--types", nargs="+", default=None,
                   help="Filtrar por tipo (publication, dataset, software, ...).")
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, resource_types=args.types)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[zenodo] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "zenodo")


if __name__ == "__main__":
    sys.exit(_cli())
