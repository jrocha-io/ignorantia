#!/usr/bin/env python3
"""
deduplicate.py — Deduplicate results across multiple per-database JSON files.

Strategy (in order):
  1. DOI exact match (lowercased, stripped)
  2. ArXiv ID exact match
  3. Normalized title + first author last name + year

Outputs:
  - merged_unique.json: deduped list with provenance (which sources had each paper)
  - dedup_report.json: counts before/after, examples of merges

Usage:
    python deduplicate.py results_arxiv.json results_s2.json results_dblp.json \
                          --output merged_unique.json --report dedup_report.json
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict


def normalize_title(title):
    if not title:
        return ""
    t = unicodedata.normalize("NFKD", title)
    t = t.encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9 ]", " ", t).lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_doi(doi):
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def first_author_lastname(authors):
    if not authors:
        return ""
    a = authors[0]
    parts = a.replace(",", " ").split()
    return parts[-1].lower() if parts else ""


def fuse(records):
    """Combine multiple records of the same paper into one with provenance."""
    sources = sorted({r.get("source", "unknown") for r in records})
    base = max(records, key=lambda r: len(r.get("abstract", "") or ""))
    merged = dict(base)
    merged["sources"] = sources
    merged["source_ids"] = {r.get("source", "unknown"): r.get("id") for r in records}

    # Backfill missing fields from other records
    for k in ("doi", "abstract", "venue", "year", "pdf_url", "citation_count"):
        if not merged.get(k):
            for r in records:
                if r.get(k):
                    merged[k] = r[k]
                    break
    return merged


def dedupe(all_records):
    by_doi = defaultdict(list)
    by_arxiv = defaultdict(list)
    by_signature = defaultdict(list)
    no_key = []

    for r in all_records:
        doi = normalize_doi(r.get("doi", ""))
        arxiv = (r.get("arxiv_id") or "").strip().lower()
        if not arxiv and r.get("source") == "arxiv":
            arxiv = (r.get("id") or "").strip().lower()
        nt = normalize_title(r.get("title", ""))
        fa = first_author_lastname(r.get("authors") or [])
        yr = str(r.get("year") or "")

        if doi:
            by_doi[doi].append(r)
        elif arxiv:
            by_arxiv[arxiv].append(r)
        elif nt and fa and yr:
            sig = f"{nt}|{fa}|{yr}"
            by_signature[sig].append(r)
        else:
            no_key.append(r)

    merged = []
    merge_examples = []

    for doi, group in by_doi.items():
        m = fuse(group)
        merged.append(m)
        if len(group) > 1:
            merge_examples.append({"key": "doi:" + doi, "n": len(group),
                                   "title": m.get("title", "")[:100]})

    for ax, group in by_arxiv.items():
        m = fuse(group)
        merged.append(m)
        if len(group) > 1:
            merge_examples.append({"key": "arxiv:" + ax, "n": len(group),
                                   "title": m.get("title", "")[:100]})

    for sig, group in by_signature.items():
        m = fuse(group)
        merged.append(m)
        if len(group) > 1:
            merge_examples.append({"key": "sig:" + sig[:60], "n": len(group),
                                   "title": m.get("title", "")[:100]})

    for r in no_key:
        merged.append(r)

    return merged, merge_examples


def load(files):
    out = []
    for p in files:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        out.extend(data.get("results", []))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="+", help="Per-database results JSON files")
    p.add_argument("--output", default="merged_unique.json")
    p.add_argument("--report", default="dedup_report.json")
    args = p.parse_args()

    all_records = load(args.inputs)
    print(f"[dedup] Loaded {len(all_records)} total records from {len(args.inputs)} files")

    merged, examples = dedupe(all_records)
    print(f"[dedup] After dedup: {len(merged)} unique records")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"n": len(merged), "results": merged}, f, indent=2, ensure_ascii=False)

    by_source_in = defaultdict(int)
    for r in all_records:
        by_source_in[r.get("source", "unknown")] += 1

    report = {
        "total_in": len(all_records),
        "total_out": len(merged),
        "duplicates_removed": len(all_records) - len(merged),
        "by_source_in": dict(by_source_in),
        "merges_top": sorted(examples, key=lambda e: -e["n"])[:30],
        "input_files": args.inputs,
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[dedup] Wrote {args.output} and {args.report}")


if __name__ == "__main__":
    main()
