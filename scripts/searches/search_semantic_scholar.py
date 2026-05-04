#!/usr/bin/env python3
"""
search_semantic_scholar.py — Search Semantic Scholar via the Graph API.

Free; rate-limited. With an API key (env var S2_API_KEY) the limit is much higher.

Usage:
    python search_semantic_scholar.py --query "transformer time series anomaly" \
                                       --year-start 2020 --year-end 2026 \
                                       --max-results 500 \
                                       --output results_s2.json
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = ("paperId,title,abstract,year,venue,publicationVenue,authors,"
          "externalIds,openAccessPdf,citationCount,influentialCitationCount,"
          "publicationTypes,fieldsOfStudy")


def fetch_page(query, year_start, year_end, fields_of_study, offset, limit):
    params = {"query": query, "fields": FIELDS, "offset": offset, "limit": limit}
    if year_start and year_end:
        params["year"] = f"{year_start}-{year_end}"
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    api_key = os.environ.get("S2_API_KEY")
    if api_key:
        req.add_header("x-api-key", api_key)

    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize(p):
    ext = p.get("externalIds") or {}
    pdf = (p.get("openAccessPdf") or {}).get("url", "")
    authors = [a.get("name", "") for a in (p.get("authors") or [])]
    # D3 (v2.23.0, auditoria #5): is_oa derivado de openAccessPdf presente.
    # language: S2 não expõe campo language consistente; default "en" para inglês
    # (predominância do corpus de papers em ciência).
    is_oa = bool(pdf)
    return {
        "source": "semantic_scholar",
        "source_tier": "tier2",  # S2 = Tier 2 (metadados + abstracts livres; full-text varia conforme licença)
        "id": p.get("paperId"),
        "title": p.get("title", ""),
        "abstract": p.get("abstract") or "",
        "authors": authors,
        "year": p.get("year"),
        "venue": p.get("venue", "") or None,
        "language": "en",  # D3: paridade com mock (S2 não expõe language consistente)
        "is_oa": is_oa,  # D3: derivado de openAccessPdf presente
        "doi": ext.get("DOI", "") or None,
        "url": pdf or f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}",  # D3: URL canônica
        "arxiv_id": ext.get("ArXiv", "") or None,
        "pubmed_id": ext.get("PubMed", "") or None,
        "pdf_url": pdf,
        "citation_count": p.get("citationCount", 0),
        "influential_citations": p.get("influentialCitationCount", 0),
        "publication_types": p.get("publicationTypes") or [],
        "fields_of_study": p.get("fieldsOfStudy") or [],
    }


def search(query, year_start=None, year_end=None, fields_of_study=None,
           max_results=500, page_size=100, throttle=1.5):
    results = []
    offset = 0
    while offset < max_results:
        limit = min(page_size, max_results - offset)
        try:
            data = fetch_page(query, year_start, year_end, fields_of_study,
                              offset, limit)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("[s2] Rate limited. Sleeping 60s...")
                time.sleep(60)
                continue
            raise
        items = data.get("data") or []
        if not items:
            break
        results.extend(normalize(p) for p in items)
        if "next" not in data:
            break
        offset = data["next"]
        time.sleep(throttle)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int, default=None)
    p.add_argument("--year-end", type=int, default=None)
    p.add_argument("--fields-of-study", nargs="*", default=None,
                   help="e.g. Computer Science, Education, Medicine")
    p.add_argument("--max-results", type=int, default=500)
    p.add_argument("--mock", action="store_true",
                   help="A6 (v2.20.0): retorna fixture determinística para CI.")
    p.add_argument("--output", default="results_s2.json")
    args = p.parse_args()

    if args.mock:
        # C1 (v2.22.0): item-level schema com language e is_oa para paridade.
        res = [
            {"paperId": "mock-s2-001", "title": f"[mock] S2 result for {args.query[:40]}",
             "authors": [{"name": "Doe, J."}], "year": 2024,
             "venue": "Mock Semantic Scholar Journal", "doi": "10.1000/mock-s2-001",
             "language": "en",  # C1
             "is_oa": True,  # C1: S2 frequentemente tem versões OA via openAccessPdf
             "url": "https://www.semanticscholar.org/paper/mock-s2-001",
             "citationCount": 42, "abstract": "Mock abstract for CI."},
            {"paperId": "mock-s2-002", "title": "[mock] Second S2 result",
             "authors": [{"name": "Smith, A."}, {"name": "Pereira, B."}],
             "year": 2023, "venue": "Mock Conference",
             "doi": "10.1000/mock-s2-002",
             "language": "en",
             "is_oa": False,
             "url": "https://www.semanticscholar.org/paper/mock-s2-002",
             "citationCount": 7, "abstract": "Another mock abstract."},
        ]
    else:
        print(f"[s2] Query: {args.query!r} years={args.year_start}-{args.year_end}")
        res = search(args.query, args.year_start, args.year_end,
                     args.fields_of_study, args.max_results)
        print(f"[s2] Got {len(res)} results.")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"source": "semantic_scholar", "source_tier": "tier2", "query": args.query,
                   "year_range": [args.year_start, args.year_end],
                   "fields_of_study": args.fields_of_study,
                   "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                   "method": "MOCK" if args.mock else "REAL",
                   "total_results": len(res), "n": len(res), "results": res}, f, indent=2, ensure_ascii=False)
    print(f"[s2] Wrote {args.output}")


if __name__ == "__main__":
    main()
