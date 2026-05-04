#!/usr/bin/env python3
"""
search_hal.py — Adapter para HAL (Hyper Articles en Ligne — CCSD/CNRS).

HAL é o repositório institucional francês mantido pelo CCSD (CNRS). ~1.5M registros
em todas as disciplinas, com forte cobertura de ciências sociais europeias e CS
francófona. Crítico para captura de literatura europeia subindexada em bases
anglo-centradas.

API: https://api.archives-ouvertes.fr/search/
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

API = "https://api.archives-ouvertes.fr/search/"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "hal", "source_tier": "tier1", "method": "HAL_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Littératie numérique des seniors: revue européenne",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "hal_id": "hal-mock-001",
                "doi": "10.0000/hal-mock-001",
                "venue": "Revue Européenne de Recherche en Éducation",
                "language": "fr", "is_oa": True,
                "url_for_pdf": "https://hal.science/hal-mock-001/document",
                "document_type": "ART",
            },
            {
                "title": "[mock] Digital divide in aging populations",
                "authors": ["Mock, C."], "year": 2024,
                "hal_id": "hal-mock-002",
                "doi": "10.0000/hal-mock-002",
                "venue": "Conférence Internationale sur le Numérique Éducatif",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://hal.science/hal-mock-002/document",
                "document_type": "COMM",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # HAL usa Solr; sintaxe Lucene
    q = query
    fq = []
    if year_start and year_end:
        fq.append(f"producedDateY_i:[{year_start} TO {year_end}]")
    params = {
        "q": q, "wt": "json",
        "rows": min(max_results, 100),
        "fl": ("title_s,authFullName_s,producedDateY_i,doiId_s,halId_s,"
               "uri_s,fileMain_s,journalTitle_s,docType_s,abstract_s,language_s"),
    }
    if fq:
        params["fq"] = fq
    url = f"{API}?{urllib.parse.urlencode(params, doseq=True)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        docs = (data.get("response") or {}).get("docs", []) or []
        results = []
        for d in docs[:max_results]:
            title = d.get("title_s")
            if isinstance(title, list):
                title = title[0] if title else ""
            authors = d.get("authFullName_s") or []
            if isinstance(authors, str):
                authors = [authors]
            year_pub = d.get("producedDateY_i")
            doi = d.get("doiId_s")
            url_pdf = d.get("fileMain_s") or d.get("uri_s")
            languages = d.get("language_s") or []
            lang = languages[0] if isinstance(languages, list) and languages else "fr"
            abstract = d.get("abstract_s")
            if isinstance(abstract, list):
                abstract = abstract[0] if abstract else ""
            venue = d.get("journalTitle_s")
            if isinstance(venue, list):
                venue = venue[0] if venue else None
            doc_type = d.get("docType_s")
            results.append({
                "title": title,
                "authors": authors,
                "year": year_pub,
                "hal_id": d.get("halId_s"),
                "doi": doi,
                "venue": venue,
                "language": lang,
                "is_oa": True,  # HAL é OA por definição
                "url_for_pdf": url_pdf,
                "document_type": doc_type,
                "abstract": (abstract or "")[:500],
            })
        total = (data.get("response") or {}).get("numFound", len(results))
        return {
            "source": "hal", "source_tier": "tier1", "method": "HAL_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": total,
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "hal", "source_tier": "tier1", "method": "HAL_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "hal", "source_tier": "tier1", "method": "HAL_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="HAL adapter (Tier 1; CCSD/CNRS).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[hal] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "hal")


if __name__ == "__main__":
    sys.exit(_cli())
