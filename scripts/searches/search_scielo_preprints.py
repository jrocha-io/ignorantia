#!/usr/bin/env python3
"""
search_scielo_preprints.py — SciELO Preprints (medRxiv lusófono).

SciELO Preprints lançado em 2020, ~6k preprints multidisciplinares com forte presença
em saúde, educação, biomedicina LATAM. Diferente do `search_scielo` (que cobre journals
com peer review consolidado), este adapter cobre preprints submetidos para revisão
ou em fase de revisão.

Site: https://preprints.scielo.org/
API: OAI-PMH em https://preprints.scielo.org/index.php/scielo/oai
Sem chave; rate limit responsável.
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

API_BASE = "https://preprints.scielo.org"
API_SEARCH = "https://preprints.scielo.org/index.php/scielo/search/search"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "scielo_preprints", "source_tier": "tier1",
        "method": "SCIELO_PREPRINTS_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Letramento digital de idosos: revisão sistemática (preprint)",
                "authors": ["Mock, A.", "Mock, B."], "year": 2024,
                "doi": "10.1590/SciELOPreprints.MOCK001",
                "venue": "SciELO Preprints",
                "language": "pt", "is_oa": True,
                "url_for_pdf": "https://preprints.scielo.org/index.php/scielo/preprint/view/MOCK001",
                "preprint_status": "posted",
                "subject_area": "saúde",
            },
            {
                "title": "[mock] mHealth interventions in Brazilian elderly populations",
                "authors": ["Mock, C."], "year": 2025,
                "doi": "10.1590/SciELOPreprints.MOCK002",
                "venue": "SciELO Preprints",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://preprints.scielo.org/index.php/scielo/preprint/view/MOCK002",
                "preprint_status": "under_review",
                "subject_area": "saúde",
            },
        ],
    }


def _parse_scielo_preprints_html(raw: bytes, year_start: int, year_end: int) -> list[dict]:
    """C3 (v2.22.0, auditoria #4): parser HTML para SciELO Preprints (OJS-based).

    OJS tipicamente retorna `<div class="obj_article_summary">` com título em
    `<h3 class="title">`, autores em `<div class="meta">`, ano em `<div class="published">`.
    Estratégia conservadora via regex; fallback honesto.
    """
    import re
    html = raw.decode("utf-8", errors="replace")

    items: list[dict] = []

    # OJS pattern v3+. Tolera aninhamento de divs internos.
    # Regex: bloco começa com class obj_article_summary; vai até </article>, </li>,
    # ou </div> que NÃO seja imediatamente seguida de outro </div> ou conteúdo
    # de tag aninhada — usamos lookahead para fim de bloco mais tolerante.
    blocks = re.findall(
        r'<(?:div|article|li)[^>]*class="[^"]*(?:obj_article_summary|article-summary|search-result-item)[^"]*"[^>]*>(.*?)(?=<(?:div|article|li)[^>]*class="[^"]*(?:obj_article_summary|article-summary|search-result-item)|</body>)',
        html, re.DOTALL | re.IGNORECASE,
    )
    # Fallback: se lookahead não funciona (ex: 1 só item), pegar até </body>
    if not blocks:
        blocks = re.findall(
            r'<(?:div|article|li)[^>]*class="[^"]*(?:obj_article_summary|article-summary|search-result-item)[^"]*"[^>]*>(.*?)</body>',
            html, re.DOTALL | re.IGNORECASE,
        )

    for block in blocks[:200]:
        title_m = re.search(
            r'<(?:h\d|a)[^>]*class="[^"]*(?:title|article-title)[^"]*"[^>]*>(?:[^<]*<a[^>]*>)?([^<]+)</',
            block, re.IGNORECASE,
        ) or re.search(r'<(?:h\d|a)[^>]*>([^<]+)</(?:h\d|a)>', block, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else ""
        if not title or len(title) < 5:
            continue

        url_m = re.search(r'href="([^"]+)"', block)
        url = url_m.group(1) if url_m else ""
        if url and not url.startswith("http"):
            url = "https://preprints.scielo.org" + url

        authors_m = re.search(
            r'<(?:div|span)[^>]*(?:authors|meta)[^>]*>([^<]+)</(?:div|span)>',
            block, re.IGNORECASE,
        )
        authors = []
        if authors_m:
            authors = [a.strip() for a in re.split(r'[,;]', authors_m.group(1)) if a.strip()]

        year_m = re.search(r'\b(19[5-9]\d|20[0-3]\d)\b', block)
        year = int(year_m.group(1)) if year_m else None

        if year_start and year_end and year:
            if not (year_start <= year <= year_end):
                continue

        # SciELO Preprints é predominantemente português + espanhol
        is_es = any(token in block.lower() for token in ['español', 'espanol', 'es-es'])
        language = "es" if is_es else "pt"

        items.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "SciELO Preprints",
            "language": language,
            "country": "BR" if language == "pt" else "regional",
            "url": url,
            "doi": None,  # OJS HTML público raramente expõe DOI estruturado
            "is_oa": True,  # SciELO Preprints é OA por design
            "publication_type": "preprint",
        })

    return items


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # SciELO Preprints usa OJS (Open Journal Systems); busca via interface web pública.
    # Endpoint estruturado retorna HTML; OAI-PMH alternativo retorna XML estruturado.
    params = {
        "query": query,
    }
    if year_start:
        params["dateFromYear"] = year_start
    if year_end:
        params["dateToYear"] = year_end
    url = f"{API_SEARCH}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json,text/html"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # C3 (v2.22.0): parser OJS implementado
        parsed_items = _parse_scielo_preprints_html(raw, year_start, year_end)
        return {
            "source": "scielo_preprints", "source_tier": "tier1",
            "method": "SCIELO_PREPRINTS_REAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "year_range": [year_start, year_end],
            "url_consulted": url, "raw_size_bytes": len(raw),
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
            "note": ("Parser OJS HTML implementado em v2.22.0. Para harvest "
                     "programático estruturado, OAI-PMH disponível em "
                     "https://preprints.scielo.org/index.php/scielo/oai. "
                     "Cobertura parcial via search_scielo (preprints às vezes "
                     "indexados na busca SciELO regular)."),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        return {"source": "scielo_preprints", "source_tier": "tier1",
                "method": "SCIELO_PREPRINTS_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="SciELO Preprints adapter (Tier 1; LATAM).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[scielo_preprints] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "scielo_preprints")


if __name__ == "__main__":
    sys.exit(_cli())
