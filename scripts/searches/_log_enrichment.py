#!/usr/bin/env python3
"""
_log_enrichment.py — Pós-processador para logs Camada 1 (DD-10).

Estratégia: em vez de modificar 45 adapters legados individualmente, este módulo
processa cada `results_<source>.json` gerado pelos adapters e gera um arquivo
companheiro `logs_<source>.jsonl` com eventos estruturados Camada 1:

- `fetched`: registros recuperados pelo adapter
- `kept_after_local_filter`: passaram filtros locais (janela temporal, idioma, DOI)
- `discarded_local`: descartados localmente, com razão técnica

Para adapters que herdam de `PaywallAdapter` (v2.12+), o log já é gerado nativamente
pelo `LocalFilter` e fica em `result["log_camada1"]`. Este módulo serve aos 45+
adapters legados (v2.0-v2.11) que não têm essa instrumentação nativa.

Uso típico (chamado pelo orquestrador após cada adapter):

    from _log_enrichment import enrich_log_camada1
    enrich_log_camada1(Path("search_results/results_pubmed.json"))
    # gera: search_results/logs/logs_pubmed.jsonl

Filtros aplicados (espelham LocalFilter do _adapter_base.py):
- year_start/year_end: janela temporal
- accepted_languages (opcional): pt, en, es por default
- require_doi (opcional): descarta items sem DOI

Saída: arquivo .jsonl com 1 evento por linha.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _filter_record(record: dict, year_start: int | None,
                   year_end: int | None,
                   accepted_languages: list[str] | None,
                   require_doi: bool) -> str | None:
    """Aplica filtros locais; retorna razão de descarte ou None."""
    year = record.get("year")
    if year_start and year_end and isinstance(year, (int, str)):
        try:
            y = int(year)
            if y < year_start or y > year_end:
                return "out_of_temporal_window"
        except (ValueError, TypeError):
            pass

    lang = record.get("language", "").lower()
    if accepted_languages and lang and lang not in accepted_languages:
        return "language_not_accepted"

    doi = record.get("doi")
    if require_doi and not doi:
        return "missing_doi"

    return None


def enrich_log_camada1(json_path: Path,
                       year_start: int | None = None,
                       year_end: int | None = None,
                       accepted_languages: list[str] | None = None,
                       require_doi: bool = False,
                       output_dir: Path | None = None) -> Path | None:
    """Processa um result_<source>.json e gera logs_<source>.jsonl Camada 1.

    Args:
        json_path: caminho para results_<source>.json
        year_start, year_end: janela temporal (opcional)
        accepted_languages: lista de idiomas aceitos (opcional)
        require_doi: se True, descarta items sem DOI
        output_dir: onde gravar o .jsonl (default: <json_path.parent>/logs/)

    Returns:
        Path do .jsonl gerado, ou None se erro.
    """
    if not json_path.exists():
        return None
    try:
        with open(json_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None

    source = data.get("source", json_path.stem.replace("results_", ""))
    method = data.get("method", "UNKNOWN")
    total_fetched = data.get("total_results", 0)
    results = data.get("results", []) or []

    # Se o adapter já forneceu log_camada1 nativo (PaywallAdapter), usa esses dados
    native_log = data.get("log_camada1")

    # Se filtros foram passados, aplicar e contar
    discarded_reasons: dict[str, int] = {}
    discarded_items: list[dict] = []
    kept_count = len(results)

    if year_start or year_end or accepted_languages or require_doi:
        kept = []
        for rec in results:
            if not isinstance(rec, dict):
                continue
            reason = _filter_record(rec, year_start, year_end,
                                     accepted_languages, require_doi)
            if reason is None:
                kept.append(rec)
            else:
                discarded_reasons[reason] = discarded_reasons.get(reason, 0) + 1
                discarded_items.append({
                    "title": rec.get("title", "")[:200],
                    "doi": rec.get("doi"),
                    "year": rec.get("year"),
                    "reason": reason,
                })
        kept_count = len(kept)

    timestamp = datetime.now(timezone.utc).isoformat()

    out_dir = output_dir or (json_path.parent / "logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"logs_{source}.jsonl"

    events = [
        {
            "timestamp": timestamp,
            "source": source,
            "event": "fetched",
            "method": method,
            "n": len(results),
            "total_results_reported_by_adapter": total_fetched,
        },
        {
            "timestamp": timestamp,
            "source": source,
            "event": "kept_after_local_filter",
            "n": kept_count,
            "filtered_count": len(results) - kept_count,
            "filter_reasons": discarded_reasons,
        },
    ]
    if discarded_items:
        events.append({
            "timestamp": timestamp,
            "source": source,
            "event": "discarded_local",
            "n": len(discarded_items),
            "items": discarded_items,
        })
    if native_log:
        events.append({
            "timestamp": timestamp,
            "source": source,
            "event": "native_log_camada1_from_adapter",
            "data": native_log,
        })

    with open(out_path, "w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    return out_path


def enrich_directory(search_results_dir: Path,
                     year_start: int | None = None,
                     year_end: int | None = None,
                     accepted_languages: list[str] | None = None) -> dict[str, Path]:
    """Aplica enrichment a todos os results_*.json em um diretório."""
    enriched = {}
    for f in search_results_dir.glob("results_*.json"):
        out = enrich_log_camada1(f, year_start, year_end, accepted_languages)
        if out:
            enriched[f.name] = out
    return enriched


def _cli() -> int:
    p = argparse.ArgumentParser(
        description="Enrich adapter results with Camada 1 logs (DD-10).")
    p.add_argument("--input", required=True, help="Path to results_<source>.json or directory.")
    p.add_argument("--output-dir", default=None, help="Output dir for .jsonl files.")
    p.add_argument("--year-start", type=int)
    p.add_argument("--year-end", type=int)
    p.add_argument("--languages", default=None,
                   help="Comma-separated accepted languages (e.g., 'pt,en,es').")
    p.add_argument("--require-doi", action="store_true")
    args = p.parse_args()

    langs = args.languages.split(",") if args.languages else None
    out_dir = Path(args.output_dir) if args.output_dir else None

    inp = Path(args.input)
    if inp.is_dir():
        results = enrich_directory(inp, args.year_start, args.year_end, langs)
        print(f"Enriched {len(results)} files:")
        for name, path in sorted(results.items()):
            print(f"  {name} → {path}")
    else:
        out = enrich_log_camada1(inp, args.year_start, args.year_end, langs,
                                  args.require_doi, out_dir)
        if out:
            print(f"Enriched: {inp.name} → {out}")
        else:
            print(f"Failed to enrich {inp}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
