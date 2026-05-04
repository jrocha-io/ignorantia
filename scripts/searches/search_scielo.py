#!/usr/bin/env python3
"""
search_scielo.py — Search SciELO via its public site search.

SciELO doesn't have a clean JSON API for its meta-search, but the site search
returns a structured HTML/JSON-ish endpoint at /api/v1/article. This script
uses the user-facing search API (search.scielo.org) which returns JSON.

Usage:
    python search_scielo.py --query "letramento digital idosos" \
                             --year-start 2020 --year-end 2026 \
                             --max-results 200 \
                             --output results_scielo.json
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://search.scielo.org/"


def fetch_page(query, year_start, year_end, lang, page, count_per_page=50):
    fq = []
    if year_start and year_end:
        years = " OR ".join(f'"{y}"' for y in range(year_start, year_end + 1))
        fq.append(f"in:({years})")
    params = {
        "q": query,
        "lang": lang or "pt",
        "count": count_per_page,
        "from": (page - 1) * count_per_page + 1,
        "output": "site",
        "format": "json",
        "page": page,
    }
    if fq:
        params["fq"] = " AND ".join(fq)
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "slr-skill/1.0",
        "Accept": "application/json"
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="ignore")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # SciELO's interface sometimes returns HTML when format param ignored.
        return {"_raw_html": text}


def normalize(it):
    return {
        "source": "scielo",
        "source_tier": "tier1",  # v2.1: SciELO = Tier 1 (full-text OA gratuito; cobertura forte em PT-BR/ES Latam)
        "id": it.get("id") or it.get("doi") or "",
        "title": it.get("title", ""),
        "abstract": it.get("abstract", "") or "",
        "authors": it.get("author", []) or [],
        "year": it.get("year"),
        "venue": it.get("source", "") or it.get("journal_title", ""),
        "doi": it.get("doi", ""),
        "language": it.get("language", ""),
        "url": it.get("url", ""),
        "issn": it.get("issn", ""),
    }


def search(query, year_start=None, year_end=None, lang="pt",
           max_results=200, page_size=50, throttle=1.5):
    results = []
    page = 1
    while len(results) < max_results:
        data = fetch_page(query, year_start, year_end, lang, page, page_size)
        if "_raw_html" in data:
            print("[scielo] WARNING: SciELO returned HTML instead of JSON.")
            print("[scielo] Falling back: instruct user to search manually at")
            print(f"[scielo]   https://search.scielo.org/?q={urllib.parse.quote(query)}")
            break
        items = (data.get("response") or {}).get("docs", [])
        if not items:
            break
        for it in items:
            results.append(normalize(it))
            if len(results) >= max_results:
                break
        if len(items) < page_size:
            break
        page += 1
        time.sleep(throttle)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int, default=None)
    p.add_argument("--year-end", type=int, default=None)
    p.add_argument("--lang", default="pt")
    p.add_argument("--max-results", type=int, default=200)
    p.add_argument("--output", default="results_scielo.json")
    p.add_argument("--mock", action="store_true")
    args = p.parse_args()

    print(f"[scielo] Query: {args.query!r}")
    if args.mock:
        res = [{
            "source": "scielo", "source_tier": "tier1",
            "id": "scielo-mock-001", "title": "[mock] Letramento digital de idosos",
            "authors": ["Silva, A."], "year": 2023,
            "venue": "Ciência & Saúde Coletiva", "doi": "10.0000/scielo-mock-001",
            "language": "pt", "url": "https://scielo.br/mock-001", "issn": "1413-8123",
        }]
        error = None
    else:
        try:
            res = search(args.query, args.year_start, args.year_end, args.lang,
                         args.max_results)
            error = None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"[scielo] [warn] erro de rede: {exc}", file=sys.stderr)
            res = []
            error = str(exc)
    print(f"[scielo] Got {len(res)} results.")
    # D1 (v2.23.0, auditoria #5): schema unificado.
    # total_results é canônico; n mantido como alias retrocompat.
    # method/year_start/year_end adicionados para paridade.
    payload = {"source": "scielo", "source_tier": "tier1", "query": args.query,
               "year_start": args.year_start,
               "year_end": args.year_end,
               "year_range": [args.year_start, args.year_end],
               "method": "SCIELO_MOCK" if args.mock else "SCIELO_REAL",
               "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
               "total_results": len(res), "n": len(res), "results": res}
    if error:
        payload["error"] = error
        payload["method"] = "SCIELO_REAL_ERROR"
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[scielo] Wrote {args.output}")


if __name__ == "__main__":
    main()
