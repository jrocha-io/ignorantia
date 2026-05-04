#!/usr/bin/env python3
"""
search_clacso.py — Adapter para o repositório CLACSO.

CLACSO (Conselho Latino-Americano de Ciências Sociais) mantém repositório OA
com livros, capítulos, artigos e working papers em ciências sociais, humanidades
e estudos críticos da América Latina e Caribe.

Site: https://biblioteca-repositorio.clacso.edu.ar/
Endpoint OAI-PMH: https://biblioteca-repositorio.clacso.edu.ar/oai/request

Cobertura: ~150k itens; forte em livros e capítulos (subindexados em Scopus/WoS).
Crítico para revisões em ciências sociais e estudos críticos latino-americanos.
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

API = "https://biblioteca-repositorio.clacso.edu.ar/oai/request"
SEARCH_PAGE = "https://biblioteca-repositorio.clacso.edu.ar/search"



def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "clacso", "source_tier": "tier1", "method": "CLACSO_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Tecnologías y exclusión digital en América Latina",
                "authors": ["Martínez, C."], "year": 2022,
                "type": "book_chapter",
                "venue": "Tensiones digitales en la región (CLACSO)",
                "country": "AR", "language": "es", "is_oa": True,
                "url": "https://biblioteca-repositorio.clacso.edu.ar/handle/CLACSO/mock-001",
                "license": "cc-by-nc-sa",
            },
            {
                "title": "[mock] Letramento crítico digital: perspectivas decoloniais",
                "authors": ["Souza, P.", "Lima, V."], "year": 2024,
                "type": "working_paper",
                "venue": "CLACSO Working Papers Series",
                "country": "BR", "language": "pt", "is_oa": True,
                "url": "https://biblioteca-repositorio.clacso.edu.ar/handle/CLACSO/mock-002",
                "license": "cc-by-nc-sa",
            },
        ],
    }


def _parse_clacso_html(raw: bytes, year_start: int, year_end: int) -> list[dict]:
    """C3 (v2.22.0, auditoria #4): parser HTML para CLACSO (DSpace-based).

    DSpace tipicamente retorna `<div class="artifact-description">` com
    `<a class="artifact-title">` e `<div class="artifact-info">`.
    Estratégia conservadora via regex; fallback honesto se HTML não bate.
    """
    import re
    html = raw.decode("utf-8", errors="replace")

    items: list[dict] = []

    # DSpace artifact pattern (common across Manakin/JSPUI themes).
    # Regex flexível: aceita single </div> de fechamento.
    artifact_blocks = re.findall(
        r'<div[^>]*class="[^"]*artifact-description[^"]*"[^>]*>(.*?)(?:</div>\s*</div>|</div>)',
        html, re.DOTALL | re.IGNORECASE,
    )

    # Fallback: handle blocks
    if not artifact_blocks:
        artifact_blocks = re.findall(
            r'<(?:div|li)[^>]*class="[^"]*(?:result-row|item|search-result)[^"]*"[^>]*>(.*?)</(?:div|li)>',
            html, re.DOTALL | re.IGNORECASE,
        )

    for block in artifact_blocks[:200]:
        # Title via primeiro <a> com class artifact-title ou primeiro link forte
        title_m = re.search(
            r'<a[^>]*class="[^"]*artifact-title[^"]*"[^>]*>([^<]+)</a>',
            block, re.IGNORECASE,
        ) or re.search(r'<(?:a|h\d)[^>]*>([^<]+)</(?:a|h\d)>', block, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else ""
        if not title or len(title) < 5:
            continue

        # URL — handle DSpace é /handle/CLACSO/NNNN
        url_m = re.search(r'href="(/handle/[^"]+|https?://[^"]+/handle/[^"]+)"', block)
        url = url_m.group(1) if url_m else ""
        if url and not url.startswith("http"):
            url = "https://biblioteca-repositorio.clacso.edu.ar" + url

        # Authors via "publisher" ou "author" patterns
        authors_m = re.search(
            r'<span[^>]*(?:author|publisher)[^>]*>([^<]+)</span>',
            block, re.IGNORECASE,
        )
        authors = []
        if authors_m:
            authors = [a.strip() for a in authors_m.group(1).split(";") if a.strip()]

        # Year via 4-dígitos
        year_m = re.search(r'\b(19[5-9]\d|20[0-3]\d)\b', block)
        year = int(year_m.group(1)) if year_m else None

        if year_start and year_end and year:
            if not (year_start <= year <= year_end):
                continue

        # Idioma: heurística (CLACSO é predominantemente espanhol/português)
        lang_m = re.search(r'\b(spa|por|eng|fra)\b', block, re.IGNORECASE)
        lang_map = {"spa": "es", "por": "pt", "eng": "en", "fra": "fr"}
        language = lang_map.get((lang_m.group(1).lower() if lang_m else ""), "es")

        items.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "CLACSO Repository",
            "language": language,
            "country": "regional",  # CLACSO agrega América Latina
            "url": url,
            "doi": None,
            "is_oa": True,  # CLACSO é OA
            "license": "cc-by-nc-sa",  # padrão CLACSO
        })

    return items


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {"query": query, "rpp": max_results}
    qs = urllib.parse.urlencode(params)
    url = f"{SEARCH_PAGE}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # C3 (v2.22.0): parser HTML implementado com fallback honesto
        parsed_items = _parse_clacso_html(raw, year_start, year_end)
        return {
            "source": "clacso", "source_tier": "tier1", "method": "CLACSO_REAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "year_range": [year_start, year_end],
            "raw_size_bytes": len(raw), "url_consulted": url,
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
            "note": ("Parser DSpace via regex conservadora. CLACSO é "
                     "DSpace-based; HTML pode mudar. OAI-PMH alternativo: "
                     "https://biblioteca-repositorio.clacso.edu.ar/oai/request"),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "clacso", "source_tier": "tier1", "method": "CLACSO_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = 1.0, timeout: float = 30.0) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="CLACSO search adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[clacso] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "clacso")


if __name__ == "__main__":
    sys.exit(_cli())
