#!/usr/bin/env python3
"""
search_dblp.py — Search dblp via its public API.

Free, no auth. Best for CS bibliographic completeness.
dblp returns no abstracts — pair with Semantic Scholar to enrich.

Usage:
    python search_dblp.py --query "transformer time series anomaly" \
                           --year-start 2020 --year-end 2026 \
                           --max-results 1000 \
                           --output results_dblp.json
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://dblp.org/search/publ/api"


def fetch_page(query, first, hits):
    params = {"q": query, "format": "json", "f": first, "h": hits}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize(hit):
    info = hit.get("info") or {}
    authors_raw = (info.get("authors") or {}).get("author", [])
    if isinstance(authors_raw, dict):
        authors_raw = [authors_raw]
    authors = [a.get("text", "") if isinstance(a, dict) else str(a)
               for a in authors_raw]
    return {
        "source": "dblp",
        "source_tier": "tier1",  # DBLP = Tier 1 (metadados livres; full-text frequentemente em arXiv também Tier 1). Sem abstracts — pareie com Semantic Scholar (Tier 2).
        "id": hit.get("@id"),
        "dblp_key": info.get("key"),
        "title": info.get("title", "").rstrip("."),
        "abstract": "",  # dblp doesn't carry abstracts
        "authors": authors,
        "year": int(info["year"]) if "year" in info else None,
        "venue": info.get("venue", "") or None,
        "language": "en",  # D3 (v2.23.0): DBLP é predominantemente CS/inglês
        "is_oa": False,  # D3: DBLP indexa metadados; OA depende do venue
        "doi": info.get("doi", "") or None,  # D3: None em vez de string vazia
        "type": info.get("type", ""),
        "url": info.get("url", "") or None,
        "ee": info.get("ee", "") or None,  # external link, often the publisher
    }


def in_year_range(item, ys, ye):
    y = item.get("year")
    if y is None:
        return False
    if ys and y < ys:
        return False
    if ye and y > ye:
        return False
    return True


def search(query, year_start=None, year_end=None, max_results=1000,
           page_size=1000, throttle=1.0):
    """dblp pages by 'first' offset; max page size is 1000."""
    results = []
    first = 0
    while first < max_results:
        hits_this_page = min(page_size, max_results - first)
        data = fetch_page(query, first, hits_this_page)
        hits = (((data.get("result") or {}).get("hits") or {}).get("hit") or [])
        if not hits:
            break
        for h in hits:
            n = normalize(h)
            if in_year_range(n, year_start, year_end):
                results.append(n)
        if len(hits) < hits_this_page:
            break
        first += hits_this_page
        time.sleep(throttle)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True,
                   help="dblp query syntax: 'term1 term2$ year:2020:2026'")
    p.add_argument("--year-start", type=int, default=None)
    p.add_argument("--year-end", type=int, default=None)
    p.add_argument("--max-results", type=int, default=1000)
    p.add_argument("--mock", action="store_true",
                   help="A6 (v2.20.0): retorna fixture determinística para CI.")
    p.add_argument("--output", default="results_dblp.json")
    args = p.parse_args()

    if args.mock:
        # C1 (v2.22.0): item-level schema com doi, language, is_oa para paridade.
        res = [
            {"key": "conf/mock/2024-1", "title": f"[mock] DBLP result for {args.query[:40]}",
             "authors": ["Doe, J.", "Smith, A."], "year": 2024,
             "venue": "Proc. Mock Conf 2024", "type": "Conference",
             "doi": "10.1000/mock-dblp-001",  # C1
             "language": "en",  # C1
             "is_oa": False,  # C1: DBLP indexa metadados; OA depende do venue
             "url": "https://dblp.org/rec/conf/mock/2024-1"},
            {"key": "journals/mock/2023-2", "title": "[mock] Another DBLP result",
             "authors": ["Pereira, B."], "year": 2023,
             "venue": "Mock Journal of Computing", "type": "Journal",
             "doi": "10.1000/mock-dblp-002",  # C1
             "language": "en",
             "is_oa": False,
             "url": "https://dblp.org/rec/journals/mock/2023-2"},
        ]
    else:
        print(f"[dblp] Query: {args.query!r}")
        res = search(args.query, args.year_start, args.year_end, args.max_results)
        print(f"[dblp] Got {len(res)} results (after year filter).")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"source": "dblp", "source_tier": "tier1", "query": args.query,
                   "year_range": [args.year_start, args.year_end],
                   "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                   "method": "MOCK" if args.mock else "REAL",
                   "total_results": len(res), "n": len(res), "results": res}, f, indent=2, ensure_ascii=False)
    print(f"[dblp] Wrote {args.output}")


if __name__ == "__main__":
    main()
