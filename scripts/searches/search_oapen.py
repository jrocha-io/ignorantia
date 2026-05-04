#!/usr/bin/env python3
"""
search_oapen.py — OAPEN (Open Access Publishing in European Networks).

OAPEN é o repositório principal de livros OA acadêmicos peer-reviewed em humanidades
e ciências sociais. ~22k títulos de >130 publishers (Brill, De Gruyter, Springer,
Routledge, Bloomsbury, etc.). Para SR em humanidades/ciências sociais, **livro é
unidade primária** — não artigo. Sem OAPEN, ghostwriter falha em humanidades.

API: https://library.oapen.org/rest/search (REST DSpace-based).
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

API = "https://library.oapen.org/rest/search"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "oapen", "source_tier": "tier1", "method": "OAPEN_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Digital Literacy in Aging Societies: A Comparative Study",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.0000/oapen-mock-001",
                "isbn": "978-0-000000-01-1",
                "venue": "Routledge",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://library.oapen.org/handle/20.500.12657/MOCK001",
                "license": "cc-by",
                "resource_type": "book",
                "subjects": ["Sociology", "Aging"],
            },
            {
                "title": "[mock] Letramento digital e cidadania: estudos brasileiros",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.0000/oapen-mock-002",
                "isbn": "978-0-000000-02-2",
                "venue": "Editora UFMG",
                "language": "pt", "is_oa": True,
                "url_for_pdf": "https://library.oapen.org/handle/20.500.12657/MOCK002",
                "license": "cc-by-nc",
                "resource_type": "book",
                "subjects": ["Education", "Brazil"],
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # OAPEN usa DSpace REST; busca via /search com expand=metadata
    params = {
        "query": query,
        "expand": "metadata,bitstreams",
        "limit": min(max_results, 100),
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            items = json.loads(resp.read().decode("utf-8"))
        if not isinstance(items, list):
            return {"source": "oapen", "source_tier": "tier1", "method": "OAPEN_REAL_PARTIAL",
                    "query": query, "results": [],
                    "note": "Resposta inesperada da API; parser detalhado é TODO."}
        results = []
        for item in items[:max_results]:
            md = {m.get("key"): m.get("value") for m in (item.get("metadata") or [])}
            md_list = {}
            for m in (item.get("metadata") or []):
                k = m.get("key")
                v = m.get("value")
                if k:
                    md_list.setdefault(k, []).append(v)

            title = md.get("dc.title")
            authors = md_list.get("dc.contributor.author", []) or md_list.get("dc.creator", [])
            year_pub = None
            issued = md.get("dc.date.issued")
            if issued:
                try:
                    year_pub = int(issued[:4])
                except ValueError:
                    pass
            # Filtrar fora da janela temporal (a API não tem filtro temporal nativo)
            if year_start and year_end and year_pub:
                if year_pub < year_start or year_pub > year_end:
                    continue
            doi = md.get("dc.identifier.doi") or md.get("dc.identifier.uri")
            isbn = md.get("dc.identifier.isbn")
            publisher = md.get("dc.publisher")
            lang = md.get("dc.language.iso") or md.get("dc.language")
            license_id = md.get("dc.rights")
            subjects = md_list.get("dc.subject", [])
            # PDF URL: extrair de bitstreams se disponível
            url_pdf = None
            for bs in (item.get("bitstreams") or []):
                if (bs.get("format") or "").lower() == "pdf":
                    url_pdf = bs.get("retrieveLink")
                    if url_pdf and not url_pdf.startswith("http"):
                        url_pdf = f"https://library.oapen.org{url_pdf}"
                    break
            if not url_pdf and item.get("handle"):
                url_pdf = f"https://library.oapen.org/handle/{item['handle']}"
            results.append({
                "title": title,
                "authors": authors,
                "year": year_pub,
                "doi": doi if doi and "doi" in (doi or "").lower() else None,
                "isbn": isbn,
                "venue": publisher,
                "language": lang,
                "is_oa": True,  # OAPEN = OA por definição
                "url_for_pdf": url_pdf,
                "license": license_id,
                "resource_type": "book",
                "subjects": subjects,
            })
        return {
            "source": "oapen", "source_tier": "tier1", "method": "OAPEN_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": len(results),
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "oapen", "source_tier": "tier1", "method": "OAPEN_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "oapen", "source_tier": "tier1", "method": "OAPEN_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="OAPEN adapter (Tier 1; livros OA peer-reviewed).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[oapen] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "oapen")


if __name__ == "__main__":
    sys.exit(_cli())
