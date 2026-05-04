#!/usr/bin/env python3
"""
search_la_referencia.py — Adapter para LA Referencia.

LA Referencia é a rede federada de repositórios institucionais OA da América Latina,
agregando 13 países (Argentina, Brasil, Chile, Colômbia, Costa Rica, Equador,
El Salvador, México, Panamá, Peru, República Dominicana, Uruguai, Venezuela).

Endpoint OAI-PMH: https://www.lareferencia.info/vufind/oai
Site público: https://www.lareferencia.info/

Cobertura: ~5M de registros bibliográficos (artigos, teses, capítulos), todos OA por
política da rede. Importante para captura de literatura ibero-americana subindexada.

Usage:
    python search_la_referencia.py --query "letramento digital idosos" \\
                                    --year-start 2020 --year-end 2026 \\
                                    --output results_la_referencia.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

API_OAI = "https://www.lareferencia.info/vufind/oai"
API_SEARCH = "https://www.lareferencia.info/vufind/Search/Results"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock_results(query: str, year_start: int, year_end: int) -> dict:
    """Fixture determinística — usada em CI e quando rede não disponível."""
    return {
        "source": "la_referencia",
        "source_tier": "tier1",
        "method": "LA_REFERENCIA_MOCK",
        "query": query,
        "year_start": year_start,
        "year_end": year_end,
        "total_results": 3,
        "results": [
            {
                "title": "[mock] Letramento digital de idosos: revisão",
                "authors": ["Silva, A.", "Pereira, B."],
                "year": 2023,
                "doi": "10.0000/la_referencia-mock-001",
                "venue": "Revista Brasileira de Educação a Distância",
                "country": "BR",
                "language": "pt",
                "url": "https://www.lareferencia.info/vufind/Record/mock-001",
                "abstract_excerpt": "Mock determinístico — fixture de teste.",
                "is_oa": True,
                "license": "cc-by",
            },
            {
                "title": "[mock] Alfabetización digital en adultos mayores",
                "authors": ["González, M."],
                "year": 2022,
                "doi": "10.0000/la_referencia-mock-002",
                "venue": "Revista de Estudios Sociales",
                "country": "CO",
                "language": "es",
                "url": "https://www.lareferencia.info/vufind/Record/mock-002",
                "abstract_excerpt": "Mock determinístico — fixture de teste.",
                "is_oa": True,
                "license": "cc-by-nc",
            },
            {
                "title": "[mock] Inclusión digital y envejecimiento",
                "authors": ["Rodríguez, P."],
                "year": 2024,
                "doi": None,
                "venue": "Tesis doctoral, Universidad de Buenos Aires",
                "country": "AR",
                "language": "es",
                "url": "https://www.lareferencia.info/vufind/Record/mock-003",
                "abstract_excerpt": "Mock determinístico — fixture de teste.",
                "is_oa": True,
                "license": "cc-by",
            },
        ],
    }


def _parse_rss_xml(raw_bytes: bytes) -> list[dict]:
    """Parse RSS/XML do VuFind LA Referencia. F15 (v2.18.1, auditoria).

    Retorna lista de items normalizados com schema padrão:
        [{"title", "authors", "year", "venue", "language", "url",
          "abstract_excerpt", "is_oa"}, ...]

    VuFind RSS structure:
        <rss><channel><item>
            <title>...</title>
            <description>...</description>
            <pubDate>...</pubDate>
            <author>...</author>
            <link>...</link>
            <dc:creator>...</dc:creator>  (multiplos)
            <dc:date>YYYY-MM-DD</dc:date>
            <dc:language>...</dc:language>
        </item>...</channel></rss>
    """
    import xml.etree.ElementTree as ET
    items: list[dict] = []
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError:
        return items

    # Namespace VuFind RSS uses Dublin Core
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}

    channel = root.find("channel")
    if channel is None:
        return items

    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue

        # Authors via dc:creator (múltiplos) ou author
        authors = [c.text.strip() for c in item.findall("dc:creator", ns)
                    if c.text]
        if not authors:
            author_text = item.findtext("author") or ""
            if author_text:
                authors = [author_text.strip()]

        # Year via dc:date ou pubDate
        year = None
        date_text = item.findtext("dc:date", default="", namespaces=ns) or \
                    item.findtext("pubDate") or ""
        if date_text:
            import re
            m = re.search(r"(\d{4})", date_text)
            if m:
                try:
                    year = int(m.group(1))
                except ValueError:
                    pass

        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()[:400]
        language = (item.findtext("dc:language", default="",
                                    namespaces=ns) or "").strip().lower()
        # Normalizar idioma: "por" → "pt", "spa" → "es", "eng" → "en"
        lang_map = {"por": "pt", "spa": "es", "eng": "en"}
        language = lang_map.get(language, language)

        items.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": None,  # VuFind RSS não traz venue estruturado
            "language": language or "und",
            "url": link,
            "abstract_excerpt": description,
            "is_oa": True,  # LA Referencia agrega só OA
            "doi": None,
        })

    return items


def _real_request(query: str, year_start: int, year_end: int,
                  max_results: int, throttle: float, timeout: float) -> dict:
    """Consulta real ao endpoint VuFind do LA Referencia.

    F15 (v2.18.1): parser RSS real implementado via xml.etree.ElementTree.
    """
    fq = []
    if year_start and year_end:
        fq.append(f"publishDate:[{year_start} TO {year_end}]")
    params = {
        "lookfor": query,
        "type": "AllFields",
        "limit": max_results,
        "view": "rss",  # mais leve que html
    }
    if fq:
        params["filter[]"] = fq
    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{API_SEARCH}?{qs}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # F15 (v2.18.1): parser RSS implementado
        parsed_items = _parse_rss_xml(raw)
        # Filtro local por janela temporal
        if year_start and year_end:
            parsed_items = [
                it for it in parsed_items
                if it.get("year") is None or year_start <= it["year"] <= year_end
            ]
        return {
            "source": "la_referencia",
            "source_tier": "tier1",
            "method": "LA_REFERENCIA_REAL",
            "query": query,
            "year_start": year_start,
            "year_end": year_end,
            "raw_format": "rss_xml",
            "raw_size_bytes": len(raw),
            "url_consulted": url,
            "total_results": len(parsed_items),
            "results": parsed_items[:max_results],
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {
            "source": "la_referencia",
            "source_tier": "tier1",
            "method": "LA_REFERENCIA_REAL_ERROR",
            "error": str(exc),
            "query": query,
        }


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE,
           timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock_results(query, year_start or 0, year_end or 0)
    return _real_request(query, year_start or 0, year_end or 0,
                         max_results, throttle, timeout)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="LA Referencia search adapter (Tier 1).")
    parser.add_argument("--query", required=True)
    parser.add_argument("--year-start", type=int, default=None)
    parser.add_argument("--year-end", type=int, default=None)
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = search(args.query, args.year_start, args.year_end,
                    args.max_results, mock=args.mock)
    Path(args.output).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    n = result.get("total_results", len(result.get("results", [])))
    print(f"[la_referencia] {n} resultados → {args.output}")
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    sys.exit(_cli())
