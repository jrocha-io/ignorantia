#!/usr/bin/env python3
"""
search_medrxiv.py — Wrapper para search_biorxiv com --server medrxiv.

medRxiv compartilha a API api.biorxiv.org com bioRxiv. Este wrapper existe para
manter o protocolo do orquestrador (`search_X.py --query --output ...` por base)
delegando ao adapter genérico.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import search_biorxiv  # noqa: E402
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _adapter_base import cli_exit_with_error_message


def _cli() -> int:
    p = argparse.ArgumentParser(description="medRxiv adapter (Tier 1; via search_biorxiv).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search_biorxiv.search("medrxiv", args.query, args.year_start, args.year_end,
                               args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[medrxiv] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "medrxiv")


if __name__ == "__main__":
    sys.exit(_cli())
