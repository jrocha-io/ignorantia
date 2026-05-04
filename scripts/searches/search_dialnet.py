#!/usr/bin/env python3
"""
search_dialnet.py — Dialnet (Universidad de La Rioja).

Dialnet é o portal bibliográfico hispânico mais relevante: ~7M referências em
humanidades, direito, ciências sociais, educação. Forte em produção espanhola e
ibero-americana. Diferente do Redalyc (que é repositório OA), Dialnet é catálogo
bibliográfico (algumas referências OA, outras só metadados).

API REST oficial requer registro acadêmico em https://dialnet.unirioja.es/
Sem registro, busca pública via interface HTML.

Para SR de PT-BR/ES em humanidades, direito, educação: Dialnet é referência cultural
esperada por banca brasileira (notadamente em programas multidisciplinares com
cooperação ibérica).
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
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

API_PUBLIC = "https://dialnet.unirioja.es/buscar/documentos"
API_REST = "https://dialnet.unirioja.es/api/v1"

DEFAULT_THROTTLE = 1.5
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "dialnet", "source_tier": "tier1",
        "method": "DIALNET_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Alfabetización digital en mayores: revisión hispanoamericana",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "dialnet_id": "12345678",
                "doi": "10.0000/dialnet-mock-001",
                "venue": "Revista de Educación (Madrid)",
                "language": "es", "is_oa": True,
                "url": "https://dialnet.unirioja.es/servlet/articulo?codigo=12345678",
                "resource_type": "article",
                "country": "ES",
            },
            {
                "title": "[mock] Direito digital e cidadania: análise comparativa Brasil-Portugal",
                "authors": ["Mock, C."], "year": 2024,
                "dialnet_id": "12345679",
                "doi": "10.0000/dialnet-mock-002",
                "venue": "Revista de Direito Público",
                "language": "pt", "is_oa": False,
                "url": "https://dialnet.unirioja.es/servlet/articulo?codigo=12345679",
                "resource_type": "article",
                "country": "PT",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          api_key: str | None,
          throttle: float, timeout: float) -> dict:
    if api_key:
        # Modo com chave: usa endpoint REST oficial (formatos JSON estruturado)
        params = {
            "query": query,
            "key": api_key,
            "format": "json",
        }
        if year_start and year_end:
            params["fechaDesde"] = year_start
            params["fechaHasta"] = year_end
        url = f"{API_REST}/articulos?{urllib.parse.urlencode(params)}"
    else:
        # Modo sem chave: busca pública HTML (parser detalhado é TODO)
        params = {
            "querysDismax.DOCUMENTAL_TODO": query,
        }
        if year_start and year_end:
            params["filtros.AÑO_PUBLICACION"] = f"{year_start}-{year_end}"
        url = f"{API_PUBLIC}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json,text/html"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        if api_key:
            try:
                data = json.loads(raw.decode("utf-8"))
                results = []
                for item in (data.get("articulos") or [])[:max_results]:
                    authors = [a.get("nombre", "") for a in (item.get("autores") or [])]
                    results.append({
                        "title": item.get("titulo"),
                        "authors": authors,
                        "year": item.get("anio"),
                        "dialnet_id": item.get("id"),
                        "doi": item.get("doi"),
                        "venue": (item.get("revista") or {}).get("titulo"),
                        "language": item.get("idioma", "es"),
                        "is_oa": (item.get("textoCompleto") is not None),
                        "url": item.get("url"),
                        "resource_type": item.get("tipo", "article"),
                    })
                return {
                    "source": "dialnet", "source_tier": "tier1", "method": "DIALNET_REAL",
                    "query": query, "year_start": year_start, "year_end": year_end,
                    "total_results": data.get("total", len(results)),
                    "results": results,
                }
            except (json.JSONDecodeError, ValueError):
                pass
        # C3 (v2.22.0): Fallback (sem chave ou JSON inválido) — agora COM parser HTML
        parsed_items = _parse_dialnet_html(raw, year_start, year_end)
        return {
            "source": "dialnet", "source_tier": "tier1", "method": "DIALNET_REAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "year_range": [year_start, year_end],
            "url_consulted": url, "raw_size_bytes": len(raw),
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
            "note": ("Parser HTML público implementado em v2.22.0. Para acesso "
                     "programático mais rico (resumos, indexação completa), "
                     "registre-se em https://dialnet.unirioja.es/registroapi "
                     "e defina DIALNET_API_KEY."),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        return {"source": "dialnet", "source_tier": "tier1",
                "method": "DIALNET_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def _parse_dialnet_html(raw: bytes, year_start: int, year_end: int) -> list[dict]:
    """C3 (v2.22.0, auditoria #4): parser HTML para busca pública Dialnet.

    Dialnet busca pública usa estrutura `<li class="documento">` com título
    em `<a class="titulo">`, autores em `<span class="autores">`, ano em
    `<span class="fechaPublicacion">`. Estratégia conservadora via regex.
    """
    import re
    html = raw.decode("utf-8", errors="replace")

    items: list[dict] = []

    # Padrão típico Dialnet: <li class="documento"> ... </li>
    blocks = re.findall(
        r'<li[^>]*class="[^"]*documento[^"]*"[^>]*>(.*?)</li>',
        html, re.DOTALL | re.IGNORECASE,
    )

    for block in blocks[:200]:
        title_m = re.search(
            r'<a[^>]*class="[^"]*titulo[^"]*"[^>]*>([^<]+)</a>',
            block, re.IGNORECASE,
        ) or re.search(r'<(?:a|h\d)[^>]*>([^<]+)</(?:a|h\d)>', block, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else ""
        if not title or len(title) < 5:
            continue

        url_m = re.search(r'href="(/servlet/[^"]+|https?://dialnet[^"]+)"', block)
        url = url_m.group(1) if url_m else ""
        if url and not url.startswith("http"):
            url = "https://dialnet.unirioja.es" + url

        authors_m = re.search(
            r'<(?:span|div)[^>]*(?:autores|author)[^>]*>([^<]+)</(?:span|div)>',
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

        # Dialnet é predominantemente espanhol; alguns português
        is_pt = any(token in block.lower()
                    for token in ['português', 'portugu&ecirc;s'])
        language = "pt" if is_pt else "es"

        items.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": None,  # Dialnet HTML público raramente expõe venue estruturado
            "language": language,
            "country": "regional",
            "url": url,
            "doi": None,
            "is_oa": False,  # Dialnet indexa metadados; OA depende do venue
        })

    return items


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           api_key: str | None = None,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    api_key = api_key or os.environ.get("DIALNET_API_KEY")
    return _real(query, year_start or 0, year_end or 0, max_results, api_key,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Dialnet adapter (Tier 1; hispano-americano).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--api-key", default=None,
                   help="Chave Dialnet; lê DIALNET_API_KEY do ambiente.")
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, api_key=args.api_key)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[dialnet] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "dialnet")


if __name__ == "__main__":
    sys.exit(_cli())
