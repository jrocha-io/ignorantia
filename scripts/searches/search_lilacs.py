#!/usr/bin/env python3
"""
search_lilacs.py — Adapter para LILACS via portal BVS (BIREME/OPAS/OMS).

LILACS é a base de literatura científica em saúde da América Latina e Caribe,
mantida pela BIREME (Centro Latino-Americano e do Caribe de Informação em Ciências
da Saúde, OPAS/OMS). Cobre ~900k registros, forte em pesquisa clínica regional
subindexada em PubMed/Scopus.

Site: https://lilacs.bvsalud.org/
Portal BVS: https://pesquisa.bvsalud.org/portal/
Endpoint público: pesquisa por iAH (interface VHL).
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

API = "https://pesquisa.bvsalud.org/portal/"



def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "lilacs", "source_tier": "tier1", "method": "LILACS_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Saúde digital de idosos: revisão LILACS",
                "authors": ["Souza, M.", "Pereira, A."], "year": 2023,
                "doi": "10.0000/lilacs-mock-001",
                "venue": "Cadernos de Saúde Pública",
                "language": "pt", "country": "BR", "is_oa": True,
                "url": "https://pesquisa.bvsalud.org/portal/resource/lilacs-mock-001",
                "lilacs_id": "LILACS-MOCK-001",
            },
            {
                "title": "[mock] Alfabetización en salud digital en adultos mayores",
                "authors": ["González, R."], "year": 2024,
                "doi": "10.0000/lilacs-mock-002",
                "venue": "Revista Panamericana de Salud Pública",
                "language": "es", "country": "regional", "is_oa": True,
                "url": "https://pesquisa.bvsalud.org/portal/resource/lilacs-mock-002",
                "lilacs_id": "LILACS-MOCK-002",
            },
        ],
    }


def _parse_bvs_html(raw: bytes, year_start: int, year_end: int) -> list[dict]:
    """A9 (v2.20.0, auditoria #2): parser para HTML do BVS portal LILACS.

    Estratégia: extrair blocos `<div class="reference-row">` ou marcadores
    típicos do iAH. Quando o parsing detalhado não encontra estrutura
    reconhecível (HTML mudou), retorna lista vazia em vez de blob.
    """
    import re
    html = raw.decode("utf-8", errors="replace")

    # BVS iAH HTML tem padrão variável; tentamos extrair via regexes conservadoras
    # baseadas em microformatos `<span class="data-meta">` e títulos.
    items: list[dict] = []

    # Padrão 1: <div class="reference"> ... </div> (newer iAH)
    reference_blocks = re.findall(
        r'<(?:div|li)[^>]*class="[^"]*(?:reference|result-row)[^"]*"[^>]*>(.*?)</(?:div|li)>',
        html, re.DOTALL | re.IGNORECASE,
    )

    for block in reference_blocks[:200]:  # safety cap
        # Título via primeiro <a> ou <h*>
        title_m = re.search(
            r'<(?:a[^>]*|h\d[^>]*)>([^<]+)</(?:a|h\d)>', block, re.IGNORECASE,
        )
        title = title_m.group(1).strip() if title_m else ""
        if not title or len(title) < 5:
            continue

        # Year via primeiro grupo de 4 dígitos 19xx-20xx
        year_m = re.search(r'\b(19[5-9]\d|20[0-3]\d)\b', block)
        year = int(year_m.group(1)) if year_m else None

        # Authors via padrão "Autor1; Autor2" próximo ao topo do bloco
        authors_m = re.search(
            r'<span[^>]*(?:author|autor)[^>]*>([^<]+)</span>',
            block, re.IGNORECASE,
        )
        if authors_m:
            authors = [a.strip() for a in authors_m.group(1).split(";") if a.strip()]
        else:
            authors = []

        # URL via href no primeiro <a>
        url_m = re.search(r'href="([^"]+)"', block)
        url = url_m.group(1) if url_m else ""
        if url and not url.startswith("http"):
            url = "https://pesquisa.bvsalud.org" + url

        # Idioma: heurística baseada em texto português comum vs espanhol
        lang_m = re.search(r'\b(spa|por|eng)\b', block, re.IGNORECASE)
        lang_map = {"por": "pt", "spa": "es", "eng": "en"}
        language = lang_map.get((lang_m.group(1).lower() if lang_m else ""), "und")

        # Filtro temporal local
        if year_start and year_end and year is not None:
            if not (year_start <= year <= year_end):
                continue

        items.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": None,
            "language": language,
            "country": "regional",
            "is_oa": True,
            "url": url,
            "doi": None,
        })

    return items


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {
        "lang": "pt",
        "output": "site",
        "lilacs_filter_database": "LILACS",
        "q": query,
        "count": max_results,
    }
    if year_start and year_end:
        params["filter[year]"] = f"{year_start}-{year_end}"
    qs = urllib.parse.urlencode(params)
    url = f"{API}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # A9 (v2.20.0): parser HTML implementado com fallback honesto se não casar
        parsed_items = _parse_bvs_html(raw, year_start, year_end)
        return {
            "source": "lilacs", "source_tier": "tier1", "method": "LILACS_REAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "raw_size_bytes": len(raw), "url_consulted": url,
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
            "note": ("Parser HTML iAH/BVS via regex conservadora. "
                     "Estrutura HTML do portal pode mudar; em caso de zero "
                     "resultados reais, considere usar PubMed para descoberta "
                     "(Cochrane CENTRAL pattern)."),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "lilacs", "source_tier": "tier1", "method": "LILACS_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = 1.0, timeout: float = 30.0) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="LILACS/BVS search adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[lilacs] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "lilacs")


if __name__ == "__main__":
    sys.exit(_cli())
