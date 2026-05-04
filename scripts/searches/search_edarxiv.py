#!/usr/bin/env python3
"""
search_edarxiv.py — Wrapper para search_osf_preprints com provider=edarxiv.

edArxiv é um dos providers temáticos do OSF Preprints (educação). Este wrapper
existe para manter o protocolo do orquestrador delegando ao adapter genérico.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import search_osf_preprints  # noqa: E402
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _adapter_base import cli_exit_with_error_message


def _cli() -> int:
    p = argparse.ArgumentParser(description="edArxiv adapter (Tier 1; via OSF).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search_osf_preprints.search(args.query, provider="edarxiv",
                                     year_start=args.year_start, year_end=args.year_end,
                                     max_results=args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[edarxiv] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "edarxiv")


if __name__ == "__main__":
    sys.exit(_cli())
