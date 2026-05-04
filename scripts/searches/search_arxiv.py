#!/usr/bin/env python3
"""
search_arxiv.py — Search arXiv via the official API.

Usage:
    python search_arxiv.py --query 'cat:cs.AI AND abs:transformer AND abs:"time series"' \
                           --start-date 2020-01-01 --end-date 2026-04-27 \
                           --max-results 1000 \
                           --output results_arxiv.json

The arXiv API returns Atom feeds. We parse and emit a normalized JSON.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ATOM_NS = {"a": "http://www.w3.org/2005/Atom",
           "arxiv": "http://arxiv.org/schemas/atom"}

API = "https://export.arxiv.org/api/query"


def build_query(user_query, start_date, end_date):
    """Combine a user-provided Boolean query with a date filter."""
    if start_date and end_date:
        sd = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%d") + "0000"
        ed = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y%m%d") + "2359"
        date_clause = f"submittedDate:[{sd} TO {ed}]"
        return f"({user_query}) AND {date_clause}"
    return user_query


def fetch_page(query, start, max_per_page):
    """Fetch a page from arXiv API with exponential backoff on rate limits.

    A8 (v2.20.0, auditoria #2): retry com backoff exponencial em HTTP 429
    (Too Many Requests). arXiv tem rate limit estrito — antes da v2.20.0,
    o adapter falhava imediatamente em 429.
    """
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_per_page,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < max_attempts - 1:
                # Backoff exponencial: 2s, 4s, 8s
                wait = 2 ** (attempt + 1)
                print(f"[arxiv] HTTP 429; aguardando {wait}s (attempt {attempt + 1}/{max_attempts})",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def parse_entry(entry):
    def t(tag, ns="a"):
        el = entry.find(f"{ns}:{tag}", ATOM_NS)
        return el.text.strip() if el is not None and el.text else ""

    authors = [a.find("a:name", ATOM_NS).text.strip()
               for a in entry.findall("a:author", ATOM_NS)
               if a.find("a:name", ATOM_NS) is not None]
    cats = [c.attrib.get("term", "") for c in entry.findall("a:category", ATOM_NS)]

    pdf = ""
    abs_url = ""  # D3 (v2.23.0): URL canônica (página de aterrissagem)
    for link in entry.findall("a:link", ATOM_NS):
        if link.attrib.get("title") == "pdf":
            pdf = link.attrib.get("href", "")
        elif link.attrib.get("rel") == "alternate":
            abs_url = link.attrib.get("href", "")

    arxiv_id = t("id").rsplit("/", 1)[-1]
    # D3 (v2.23.0, auditoria #5): year como int (paridade com mock + outros adapters);
    # adicionar language, is_oa, url, venue para schema item-level unificado.
    year_str = t("published")[:4]
    try:
        year_int = int(year_str) if year_str else None
    except ValueError:
        year_int = None

    return {
        "source": "arxiv",
        "source_tier": "tier1",  # arXiv = Tier 1 (OA full-text gratuito)
        "id": arxiv_id,
        "title": " ".join(t("title").split()),
        "abstract": " ".join(t("summary").split()),
        "authors": authors,
        "year": year_int,  # D3: int (era str)
        "submitted_date": t("published"),
        "categories": cats,
        "venue": "arXiv preprint",  # D3: paridade com mock
        "language": "en",  # D3: arXiv é predominantemente inglês
        "is_oa": True,  # D3: arXiv é OA por design
        "url": abs_url or f"https://arxiv.org/abs/{arxiv_id}",  # D3: URL canônica
        "pdf_url": pdf,
        "doi": t("doi", "arxiv") or None,  # D3: None em vez de string vazia
    }


def search(query, max_results=1000, page_size=100, throttle=3.0):
    """Iterate paginated results from arXiv."""
    results = []
    start = 0
    while start < max_results:
        page = min(page_size, max_results - start)
        xml_text = fetch_page(query, start, page)
        root = ET.fromstring(xml_text)
        entries = root.findall("a:entry", ATOM_NS)
        if not entries:
            break
        for e in entries:
            results.append(parse_entry(e))
        if len(entries) < page:
            break
        start += page
        time.sleep(throttle)  # arXiv asks for >=3s between requests
    return results


def main():
    p = argparse.ArgumentParser(description="arXiv search adapter.")
    p.add_argument("--query", required=True)
    # A3 (v2.20.0, auditoria #2): aceita --year-start/--year-end (orquestrador)
    # E mantém --start-date/--end-date (retrocompat).
    p.add_argument("--start-date", default=None,
                   help="YYYY-MM-DD (alternativa: --year-start NNNN).")
    p.add_argument("--end-date", default=None,
                   help="YYYY-MM-DD (alternativa: --year-end NNNN).")
    p.add_argument("--year-start", type=int, default=None,
                   help="Ano-início. Convertido internamente para "
                        "YYYY-01-01. Compatível com search_orchestrator.py.")
    p.add_argument("--year-end", type=int, default=None,
                   help="Ano-fim. Convertido internamente para YYYY-12-31.")
    p.add_argument("--max-results", type=int, default=1000)
    p.add_argument("--mock", action="store_true",
                   help="Retorna fixture determinística para CI.")
    p.add_argument("--output", default="results_arxiv.json")
    args = p.parse_args()

    # Resolver datas: --year-start/--year-end têm precedência se passados
    start_date = args.start_date
    end_date = args.end_date
    if args.year_start is not None and start_date is None:
        start_date = f"{args.year_start:04d}-01-01"
    if args.year_end is not None and end_date is None:
        end_date = f"{args.year_end:04d}-12-31"

    if args.mock:
        # Fixture determinística (A6)
        res = _mock_results(args.query, start_date, end_date)
        full_q = f"[mock] {args.query}"
    else:
        full_q = build_query(args.query, start_date, end_date)
        print(f"[arxiv] Query: {full_q}")
        res = search(full_q, max_results=args.max_results)
        print(f"[arxiv] Got {len(res)} results.")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"source": "arxiv", "source_tier": "tier1", "query": full_q,
                   "year_start": args.year_start,
                   "year_end": args.year_end,
                   "year_range": [args.year_start, args.year_end],  # C2: paridade
                   "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                   "total_results": len(res), "n": len(res),
                   "results": res,
                   "method": "MOCK" if args.mock else "REAL"}, f,
                  indent=2, ensure_ascii=False)
    print(f"[arxiv] Wrote {args.output}")


def _mock_results(query: str, start_date: str | None, end_date: str | None) -> list:
    """A6 (v2.20.0): fixture determinística para CI/offline. Mock comum a
    todos os 4 adapters legacy retrofitted em v2.20.0.

    C1 (v2.22.0): item-level schema agora inclui `year`, `language`, `is_oa`,
    `venue` para paridade com paywall/legacy adapters.
    """
    return [
        {
            "id": "arxiv:2401.00001v1",
            "title": f"[mock] arXiv result 1 for query: {query[:40]}",
            "authors": ["Doe, J.", "Smith, A."],
            "abstract": "Mock abstract for testing.",
            "submitted": "2024-01-01",
            "updated": "2024-01-02",
            "year": 2024,  # C1: paridade com paywall/legacy
            "language": "en",  # C1
            "is_oa": True,  # C1: arXiv é OA por design
            "venue": "arXiv preprint",  # C1
            "primary_category": "cs.AI",
            "categories": ["cs.AI", "cs.LG"],
            "url": "https://arxiv.org/abs/2401.00001",
            "doi": None,
        },
        {
            "id": "arxiv:2401.00002v1",
            "title": f"[mock] arXiv result 2 for query: {query[:40]}",
            "authors": ["Pereira, B."],
            "abstract": "Another mock abstract.",
            "submitted": "2024-02-15",
            "updated": "2024-02-16",
            "year": 2024,
            "language": "en",
            "is_oa": True,
            "venue": "arXiv preprint",
            "primary_category": "cs.LG",
            "categories": ["cs.LG"],
            "url": "https://arxiv.org/abs/2401.00002",
            "doi": None,
        },
    ]


if __name__ == "__main__":
    main()
