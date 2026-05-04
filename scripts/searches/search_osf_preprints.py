#!/usr/bin/env python3
"""
search_osf_preprints.py — Adapter para OSF Preprints (Center for Open Science).

OSF Preprints é a meta-plataforma do Center for Open Science que indexa preprints
de múltiplos servidores temáticos: edArxiv (educação), PsyArXiv (psicologia),
SocArXiv (ciências sociais), engrXiv (engenharia), AfricArXiv, Arabixiv, etc.

API: https://api.osf.io/v2/preprints/
Sem chave; rate limit responsável (recomendado throttle 1s).
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

API = "https://api.osf.io/v2/preprints/"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(provider: str | None, query: str, year_start: int, year_end: int) -> dict:
    src_label = f"osf_preprints/{provider}" if provider else "osf_preprints"
    return {
        "source": src_label, "source_tier": "tier1", "method": "OSF_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "provider_filter": provider,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Open preprint on digital education",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.31219/osf.io/mock-001",
                "venue": (provider or "osf").upper() + " preprint",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://osf.io/preprints/mock-001/download",
                "preprint_provider": provider or "osf",
            },
            {
                "title": "[mock] Adult learning research preprint",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.31219/osf.io/mock-002",
                "venue": (provider or "osf").upper() + " preprint",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://osf.io/preprints/mock-002/download",
                "preprint_provider": provider or "osf",
            },
        ],
    }


def _real(provider: str | None, query: str, year_start: int, year_end: int,
          max_results: int, throttle: float, timeout: float) -> dict:
    # OSF JSON:API filtros — texto via filter[q]; provider via filter[provider]
    filters = [f"filter[q]={urllib.parse.quote(query)}"]
    if provider:
        filters.append(f"filter[provider]={urllib.parse.quote(provider)}")
    if year_start:
        filters.append(f"filter[date_published][gte]={year_start}-01-01")
    if year_end:
        filters.append(f"filter[date_published][lte]={year_end}-12-31")
    page_size = min(max_results, 100)
    qs = "&".join(filters) + f"&page[size]={page_size}"
    url = f"{API}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in (data.get("data") or [])[:max_results]:
            attr = item.get("attributes", {})
            rels = item.get("relationships", {})
            # Autores não vêm inline; só count + URL para fetch (segunda chamada).
            # Por economia: extrair nomes de "creator" se disponível, senão lista vazia.
            year_pub = None
            date_pub = attr.get("date_published") or ""
            if date_pub:
                try:
                    year_pub = int(date_pub[:4])
                except ValueError:
                    pass
            doi = attr.get("doi")
            results.append({
                "title": attr.get("title"),
                "authors": [],  # exigiria 2ª chamada por item; deixado para futuro
                "year": year_pub,
                "doi": doi,
                "venue": ((rels.get("provider") or {}).get("data") or {}).get("id", "osf"),
                "language": "en",
                "is_oa": True,
                "url_for_pdf": item.get("links", {}).get("download"),
                "preprint_provider": ((rels.get("provider") or {}).get("data") or {}).get("id"),
                "abstract": (attr.get("description") or "")[:500],
                "tags": attr.get("tags", []),
            })
        total = (data.get("links") or {}).get("meta", {}).get("total", len(results))
        return {
            "source": "osf_preprints" + (f"/{provider}" if provider else ""),
            "source_tier": "tier1", "method": "OSF_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "provider_filter": provider,
            "total_results": total,
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "osf_preprints", "source_tier": "tier1",
                "method": "OSF_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "osf_preprints", "source_tier": "tier1",
                "method": "OSF_REAL_ERROR", "error": str(exc), "query": query,
                "results": []}


def search(query: str, provider: str | None = None,
           year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(provider, query, year_start or 0, year_end or 0)
    return _real(provider, query, year_start or 0, year_end or 0, max_results,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="OSF Preprints adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--provider", default=None,
                   help="Provider filter (ex.: edarxiv, psyarxiv, socarxiv, engrxiv).")
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.provider, args.year_start, args.year_end,
               args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[osf_preprints{'/' + args.provider if args.provider else ''}] "
          f"{n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "osf_preprints")


if __name__ == "__main__":
    sys.exit(_cli())
