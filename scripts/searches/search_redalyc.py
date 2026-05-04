#!/usr/bin/env python3
"""
search_redalyc.py — Adapter para Redalyc (Red de Revistas Científicas de América Latina).

Redalyc indexa ~1.300 revistas OA da América Latina, Caribe, Espanha e Portugal
em ciências sociais, humanidades e ciências da saúde. Mantida pela UAEM (México).

Site: https://www.redalyc.org/
Endpoint público: https://www.redalyc.org/sistema/ws/buscar.php (GET)

Cobertura: forte em ciências sociais ibero-americanas; complementa SciELO em
áreas onde SciELO tem menos densidade (sociologia, antropologia, educação ibero).
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

API = "https://www.redalyc.org/sistema/ws/buscar.php"



def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "redalyc", "source_tier": "tier1", "method": "REDALYC_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Educación y tecnologías digitales: una revisión latinoamericana",
                "authors": ["Hernández, M.", "Castro, L."], "year": 2022,
                "doi": "10.0000/redalyc-mock-001",
                "venue": "Revista Latinoamericana de Estudios Educativos",
                "country": "MX", "language": "es", "is_oa": True,
                "url": "https://www.redalyc.org/articulo.oa?id=mock-001",
                "license": "cc-by-nc",
            },
            {
                "title": "[mock] Letramento digital no contexto ibero-americano",
                "authors": ["Almeida, R."], "year": 2023,
                "doi": "10.0000/redalyc-mock-002",
                "venue": "Educação & Sociedade",
                "country": "BR", "language": "pt", "is_oa": True,
                "url": "https://www.redalyc.org/articulo.oa?id=mock-002",
                "license": "cc-by-nc",
            },
        ],
    }


def _parse_redalyc_response(raw: bytes, year_start: int, year_end: int) -> list[dict]:
    """B7 (v2.21.0, auditoria #3): parser para resposta do endpoint Redalyc.

    Estratégia conservadora: tenta JSON primeiro (alguns endpoints retornam JSON);
    se falhar, tenta extração via regex de HTML estruturado. Quando ambos falham,
    retorna lista vazia honestamente em vez de blob.

    Schema normalizado: title, authors, year, venue, language, country, url,
    doi, is_oa, abstract_excerpt.
    """
    import re

    items: list[dict] = []

    # Tentativa 1: JSON
    try:
        data = json.loads(raw.decode("utf-8"))
        # Estrutura típica: {"results": [...]} ou {"data": [...]} ou lista direta
        records = data if isinstance(data, list) else \
                  data.get("results") or data.get("data") or data.get("articles") or []
        for rec in records[:200]:
            if not isinstance(rec, dict):
                continue
            title = rec.get("title") or rec.get("titulo") or ""
            if not title:
                continue
            year = rec.get("year") or rec.get("anio") or rec.get("año")
            try:
                year = int(year) if year else None
            except (ValueError, TypeError):
                year = None
            if year_start and year_end and year:
                if not (year_start <= year <= year_end):
                    continue
            authors_raw = rec.get("authors") or rec.get("autores") or []
            if isinstance(authors_raw, str):
                authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
            else:
                authors = list(authors_raw) if authors_raw else []
            items.append({
                "title": title.strip(),
                "authors": authors,
                "year": year,
                "venue": rec.get("venue") or rec.get("revista") or rec.get("journal"),
                "language": (rec.get("language") or rec.get("idioma") or "").lower()[:2] or "und",
                "country": rec.get("country") or rec.get("pais") or "regional",
                "url": rec.get("url") or rec.get("link"),
                "doi": rec.get("doi"),
                "is_oa": True,
                "abstract_excerpt": (rec.get("abstract") or rec.get("resumen") or "")[:400],
            })
        if items:
            return items
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    # Tentativa 2: HTML estruturado (regex conservadora)
    html = raw.decode("utf-8", errors="replace")
    # Procurar blocos de artigo: padrão variável; usar combinação de heurísticas
    article_blocks = re.findall(
        r'<(?:article|div)[^>]*class="[^"]*(?:articulo|article|item)[^"]*"[^>]*>(.*?)</(?:article|div)>',
        html, re.DOTALL | re.IGNORECASE,
    )
    for block in article_blocks[:200]:
        title_m = re.search(
            r'<(?:a[^>]*|h\d[^>]*)>([^<]+)</(?:a|h\d)>', block, re.IGNORECASE,
        )
        title = title_m.group(1).strip() if title_m else ""
        if not title or len(title) < 5:
            continue
        year_m = re.search(r'\b(19[5-9]\d|20[0-3]\d)\b', block)
        year = int(year_m.group(1)) if year_m else None
        if year_start and year_end and year:
            if not (year_start <= year <= year_end):
                continue
        url_m = re.search(r'href="([^"]+)"', block)
        url = url_m.group(1) if url_m else ""
        if url and not url.startswith("http"):
            url = "https://www.redalyc.org" + url
        items.append({
            "title": title,
            "authors": [],
            "year": year,
            "venue": None,
            "language": "es",  # Redalyc é predominantemente espanhol/português
            "country": "regional",
            "url": url,
            "doi": None,
            "is_oa": True,
            "abstract_excerpt": "",
        })

    return items


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    params = {"q": query, "tipo": "articulo", "limit": max_results}
    qs = urllib.parse.urlencode(params)
    url = f"{API}?{qs}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # B7 (v2.21.0): parser implementado com fallback honesto
        parsed_items = _parse_redalyc_response(raw, year_start, year_end)
        return {
            "source": "redalyc", "source_tier": "tier1", "method": "REDALYC_REAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "raw_size_bytes": len(raw), "url_consulted": url,
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
            "note": ("Parser conservador (JSON+HTML regex). Estrutura do "
                     "endpoint Redalyc pode mudar; em caso de zero resultados, "
                     "considere triangular via SciELO/CLACSO."),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "redalyc", "source_tier": "tier1",
                "method": "REDALYC_REAL_ERROR", "error": str(exc), "query": query}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = 1.0, timeout: float = 30.0) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Redalyc search adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int)
    p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[redalyc] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "redalyc")


if __name__ == "__main__":
    sys.exit(_cli())
