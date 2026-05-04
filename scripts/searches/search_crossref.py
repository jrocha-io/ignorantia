#!/usr/bin/env python3
"""
search_crossref.py — Search Crossref via the public API.

Free, no auth required, but include a polite User-Agent with email.

Usage:
    python search_crossref.py --query "letramento digital idosos" \
                               --year-start 2020 --year-end 2026 \
                               --max-results 500 \
                               --type journal-article \
                               --email you@example.org \
                               --output results_crossref.json
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.crossref.org/works"


def fetch_page(query, year_start, year_end, doc_type, rows, offset, email):
    params = {"query": query, "rows": rows, "offset": offset}
    filters = []
    if year_start:
        filters.append(f"from-pub-date:{year_start}-01-01")
    if year_end:
        filters.append(f"until-pub-date:{year_end}-12-31")
    if doc_type:
        filters.append(f"type:{doc_type}")
    if filters:
        params["filter"] = ",".join(filters)
    url = f"{API}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url)
    ua = f"slr-skill/1.0 (mailto:{email})" if email else "slr-skill/1.0"
    req.add_header("User-Agent", ua)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize(it):
    title = (it.get("title") or [""])[0]
    container = (it.get("container-title") or [""])[0]
    authors = []
    for a in it.get("author") or []:
        nm = " ".join(filter(None, [a.get("given", ""), a.get("family", "")]))
        if nm:
            authors.append(nm.strip())
    issued = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
    year = issued[0] if issued else None
    # D3 (v2.23.0, auditoria #5): adicionar language, is_oa para schema unificado.
    # language: Crossref expõe via `language` field (BCP 47); fallback "en".
    language = (it.get("language") or "en").lower()[:2] or "en"
    # is_oa: Crossref expõe via license[].URL incluir Creative Commons,
    # ou via "license" array com URL contendo creativecommons.org
    is_oa = False
    for lic in it.get("license") or []:
        url = (lic.get("URL") or "").lower()
        if "creativecommons" in url or "/cc-" in url or "/by" in url or "/by-" in url:
            is_oa = True
            break
    return {
        "source": "crossref",
        "source_tier": "tier2",  # Crossref geral = Tier 2 (metadados livres; full-text varia conforme licença)
        "id": it.get("DOI", "") or None,
        "title": title,
        "abstract": it.get("abstract", "") or "",
        "authors": authors,
        "year": year,
        "venue": container or None,  # D3: None em vez de string vazia
        "container_title": container,  # D3: alias para retrocompat
        "language": language,  # D3: paridade com mock
        "is_oa": is_oa,  # D3: paridade com mock
        "doi": it.get("DOI", "") or None,
        "type": it.get("type", ""),
        "publisher": it.get("publisher", ""),
        "url": it.get("URL", "") or None,
        "citation_count": it.get("is-referenced-by-count", 0),
    }


def search(query, year_start=None, year_end=None, doc_type=None,
           max_results=500, page_size=100, email=None, throttle=0.5):
    results = []
    offset = 0
    while offset < max_results:
        rows = min(page_size, max_results - offset)
        data = fetch_page(query, year_start, year_end, doc_type, rows, offset, email)
        msg = data.get("message") or {}
        items = msg.get("items") or []
        if not items:
            break
        results.extend(normalize(it) for it in items)
        if len(items) < rows:
            break
        offset += rows
        time.sleep(throttle)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int, default=None)
    p.add_argument("--year-end", type=int, default=None)
    p.add_argument("--type", default=None,
                   help="e.g. journal-article, proceedings-article, book-chapter")
    p.add_argument("--max-results", type=int, default=500)
    p.add_argument("--email", default=None,
                   help="Polite User-Agent email recommended by Crossref")
    p.add_argument("--mock", action="store_true",
                   help="A6 (v2.20.0): retorna fixture determinística para CI.")
    p.add_argument("--output", default="results_crossref.json")
    args = p.parse_args()

    if args.mock:
        # C1 (v2.22.0): item-level schema com language, is_oa, venue para paridade.
        res = [
            {"doi": "10.1000/mock-cr-001", "title": f"[mock] Crossref result for {args.query[:40]}",
             "authors": ["Doe, J."], "year": 2024,
             "container_title": "Mock Journal", "venue": "Mock Journal",  # C1: alias
             "type": "journal-article",
             "language": "en",  # C1
             "is_oa": False,  # C1: Crossref não declara OA; default False
             "url": "https://doi.org/10.1000/mock-cr-001"},
            {"doi": "10.1000/mock-cr-002", "title": "[mock] Another Crossref result",
             "authors": ["Smith, A."], "year": 2023,
             "container_title": "Mock Conference Proceedings",
             "venue": "Mock Conference Proceedings",
             "type": "proceedings-article",
             "language": "en",
             "is_oa": False,
             "url": "https://doi.org/10.1000/mock-cr-002"},
        ]
    else:
        print(f"[crossref] Query: {args.query!r}")
        res = search(args.query, args.year_start, args.year_end, args.type,
                     args.max_results, email=args.email)
        print(f"[crossref] Got {len(res)} results.")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"source": "crossref", "source_tier": "tier2", "query": args.query,
                   "year_range": [args.year_start, args.year_end],
                   "type": args.type,
                   "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                   "method": "MOCK" if args.mock else "REAL",
                   "total_results": len(res), "n": len(res), "results": res}, f, indent=2, ensure_ascii=False)
    print(f"[crossref] Wrote {args.output}")


if __name__ == "__main__":
    main()
