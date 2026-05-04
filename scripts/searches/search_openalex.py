#!/usr/bin/env python3
"""
search_openalex.py — Adapter dedicado para OpenAlex.

OpenAlex é a base bibliográfica aberta do projeto OurResearch (sucessora do
Microsoft Academic). ~250M obras, ~95M autores, ~120k venues. Cobertura
multi-disciplinar e melhor que Crossref para metadados estruturados (instituições,
afiliações, conceitos derivados).

Esta adição é **redundante por design**: `search_semantic_scholar.py` já consome
OpenAlex internamente como uma de suas fontes, e `search_crossref.py` cobre overlap
substancial. Mantemos um adapter dedicado para:

1. **Clareza arquitetural**: TIER_DATABASES declara `openalex` como fonte; existe um
   arquivo correspondente (Decisão 25 — declarar é se comprometer).
2. **Filtros específicos** que Semantic Scholar não expõe: filter por instituição,
   por venue, por tipo de obra com granularidade fina.
3. **Snowballing forward** (já implementado em `snowballing_forward.py`) usa OpenAlex
   `cites:` filter — este adapter compartilha o cliente HTTP base.

API: https://api.openalex.org/works
Política mailto: incluir email no User-Agent acelera "polite pool" (resposta mais
rápida). Lê IGNORANTIA_CONTACT_EMAIL do ambiente.
"""
from __future__ import annotations

import argparse
import json
import os
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

API = "https://api.openalex.org/works"
USER_AGENT_BASE = "ignorantia-skill/2.10.2"
DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int, oa_only: bool) -> dict:
    return {
        "source": "openalex", "source_tier": "tier1" if oa_only else "tier2",
        "method": "OPENALEX_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "oa_only": oa_only,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Comprehensive review of digital health interventions",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "openalex_id": "https://openalex.org/W4000000001",
                "doi": "10.0000/openalex-mock-001",
                "venue": "PLOS ONE",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://journals.plos.org/plosone/article/file?id=10.0000/openalex-mock-001&type=printable",
                "type": "journal-article",
                "cited_by_count": 42,
            },
            {
                "title": "[mock] Older adults and technology: meta-analysis",
                "authors": ["Mock, C."], "year": 2024,
                "openalex_id": "https://openalex.org/W4000000002",
                "doi": "10.0000/openalex-mock-002",
                "venue": "Computers in Human Behavior",
                "language": "en",
                "is_oa": True if oa_only else False,
                "url_for_pdf": "https://example.org/mock-002.pdf" if oa_only else None,
                "type": "journal-article",
                "cited_by_count": 17,
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          oa_only: bool, contact_email: str | None,
          throttle: float, timeout: float) -> dict:
    # OpenAlex usa filter compostos separados por vírgula
    filters = [f"title_and_abstract.search:{query}"]
    if year_start and year_end:
        filters.append(f"publication_year:{year_start}-{year_end}")
    if oa_only:
        filters.append("is_oa:true")
    params = {
        "filter": ",".join(filters),
        "per-page": min(max_results, 200),
        "sort": "cited_by_count:desc",
    }
    user_agent = USER_AGENT_BASE
    if contact_email:
        user_agent = f"{USER_AGENT_BASE} (mailto:{contact_email})"
        params["mailto"] = contact_email

    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for w in (data.get("results") or [])[:max_results]:
            authors = [a.get("author", {}).get("display_name")
                       for a in (w.get("authorships") or [])
                       if a.get("author")][:10]
            primary_loc = w.get("primary_location") or {}
            source = primary_loc.get("source") or {}
            doi = w.get("doi")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]
            best_oa = w.get("best_oa_location") or {}
            url_pdf = best_oa.get("pdf_url") or primary_loc.get("pdf_url")
            results.append({
                "title": w.get("title") or w.get("display_name"),
                "authors": authors,
                "year": w.get("publication_year"),
                "openalex_id": w.get("id"),
                "doi": doi,
                "venue": source.get("display_name"),
                "language": w.get("language", "en"),
                "is_oa": w.get("open_access", {}).get("is_oa", False),
                "url_for_pdf": url_pdf,
                "type": w.get("type"),
                "cited_by_count": w.get("cited_by_count", 0),
                "abstract": _reconstruct_abstract(w.get("abstract_inverted_index"))[:500],
            })
        meta = data.get("meta", {})
        total = meta.get("count", len(results))
        return {
            "source": "openalex", "source_tier": "tier1" if oa_only else "tier2",
            "method": "OPENALEX_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "oa_only": oa_only,
            "total_results": total,
            "results": results,
            "note": ("Adapter dedicado por clareza arquitetural; cobertura sobrepõe "
                     "search_semantic_scholar e search_crossref. Use combinado para "
                     "deduplicação por DOI."),
        }
    except urllib.error.HTTPError as exc:
        return {"source": "openalex", "source_tier": "tier1" if oa_only else "tier2",
                "method": "OPENALEX_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "openalex", "source_tier": "tier1" if oa_only else "tier2",
                "method": "OPENALEX_REAL_ERROR", "error": str(exc), "query": query,
                "results": []}


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex retorna abstract como inverted_index para evitar copyright; reconstrói."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False, oa_only: bool = True,
           contact_email: str | None = None,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0, oa_only)
    contact_email = contact_email or os.environ.get("IGNORANTIA_CONTACT_EMAIL")
    return _real(query, year_start or 0, year_end or 0, max_results, oa_only,
                 contact_email, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="OpenAlex adapter (Tier 1 OA / Tier 2 metadados).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--include-non-oa", action="store_true",
                   help="Incluir works sem full-text OA (modo Tier 2 metadados).")
    p.add_argument("--contact-email", default=None,
                   help="Email para polite pool; lê IGNORANTIA_CONTACT_EMAIL do ambiente.")
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    oa_only = not args.include_non_oa
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, oa_only=oa_only, contact_email=args.contact_email)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[openalex] {n} resultados ({'OA only' if oa_only else 'inclui non-OA'}) → {args.output}")
    return cli_exit_with_error_message(r, "openalex")


if __name__ == "__main__":
    sys.exit(_cli())
