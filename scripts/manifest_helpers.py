#!/usr/bin/env python3
"""
manifest_helpers.py — Utilitários para `reproducibility_manifest.yaml` (Decisões 21 e 22).

Implementa:

- **Decisão 21 (v2.8.0):** ao prosseguir da Fase 4 (screening) para Fase 5 (extração),
  o manifest registra automaticamente `phase4_exclusions_review: implicit_consent`.
  Isso substitui o spot-check separado que a rubrica antiga exigia.

- **Decisão 22 (v2.9.0):** cada execução de busca registra timestamp e hash da query
  efetiva. O orquestrador detecta `today != last_run_date` e dispara re-execução
  obrigatória ao avançar para nova subversão.

Uso programático:

    from manifest_helpers import (
        record_phase4_consent, record_search_run, days_since_last_run,
        load_manifest, save_manifest,
    )

    manifest = load_manifest("output_dir/reproducibility_manifest.yaml")
    manifest = record_search_run(manifest, query="...", area="saude")
    manifest = record_phase4_consent(manifest, n_excluded_title=1646, n_excluded_abstract=326)
    save_manifest(manifest, "output_dir/reproducibility_manifest.yaml")
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# YAML é opcional — fallback para JSON se PyYAML não estiver disponível
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Carrega manifest YAML (ou JSON como fallback). Retorna dict vazio se não existir."""
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8")
    if YAML_AVAILABLE and (p.suffix in (".yaml", ".yml") or text.lstrip().startswith("schema_version:")):
        return yaml.safe_load(text) or {}
    return json.loads(text) if text.strip() else {}


def save_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    """Grava manifest. Usa YAML se disponível e extensão for .yaml/.yml; senão JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if YAML_AVAILABLE and p.suffix in (".yaml", ".yml"):
        p.write_text(
            yaml.dump(manifest, sort_keys=False, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    else:
        p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _hash_query(query: str, area: str = "", year_start: int | None = None,
                year_end: int | None = None) -> str:
    """SHA-256 curto (12 hex) do tuple efetivo da busca, para detectar mudanças."""
    payload = f"{query}|{area}|{year_start}|{year_end}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


# ---- Decisão 21: consentimento implícito Fase 4 ----

def record_phase4_consent(manifest: dict[str, Any],
                           n_excluded_title: int = 0,
                           n_excluded_abstract: int = 0,
                           rationale: str | None = None) -> dict[str, Any]:
    """Registra `phase4_exclusions_review: implicit_consent` no manifest.

    Chamado quando o usuário avança da Fase 4 (screening) para a Fase 5 (extração).
    Substitui o spot-check separado que a rubrica antiga exigia (Decisão 21).
    """
    manifest["phase4_exclusions_review"] = {
        "mode": "implicit_consent",
        "consented_at": _now_iso(),
        "n_excluded_title_abstract": n_excluded_title,
        "n_excluded_abstract_full": n_excluded_abstract,
        "rationale": (rationale or
                      "Ao prosseguir para extração, o autor aceita as exclusões da Fase 4. "
                      "Decisão 21 (v2.8.0): spot-check separado é redundante."),
    }
    return manifest


# ---- Decisão 22: re-execução por subversão ----

def record_search_run(manifest: dict[str, Any], *,
                      query: str, area: str,
                      year_start: int | None = None,
                      year_end: int | None = None,
                      version: str | None = None,
                      databases_searched: list[str] | None = None) -> dict[str, Any]:
    """Registra uma execução de busca em `search_runs[]`.

    Cada entrada captura: timestamp, hash da query efetiva, versão do paper,
    e bases efetivamente consultadas (para auditoria de estabilidade entre runs).
    """
    runs = manifest.setdefault("search_runs", [])
    runs.append({
        "ran_at": _now_iso(),
        "ran_on_date": _today_iso(),
        "version": version or manifest.get("version"),
        "query": query,
        "area": area,
        "year_start": year_start,
        "year_end": year_end,
        "query_hash": _hash_query(query, area, year_start, year_end),
        "databases_searched": databases_searched or [],
    })
    manifest["last_run_date"] = _today_iso()
    return manifest


def days_since_last_run(manifest: dict[str, Any]) -> int | None:
    """Retorna nº de dias desde a última execução de busca (Decisão 22).

    Usado pelo orquestrador para decidir se uma re-execução é obrigatória ao
    incrementar versão. Retorna None se nunca houve execução.
    """
    runs = manifest.get("search_runs", [])
    if not runs:
        last = manifest.get("last_run_date")
        if not last:
            return None
        last_date = last
    else:
        last_date = runs[-1].get("ran_on_date") or runs[-1].get("ran_at", "")[:10]
    if not last_date:
        return None
    try:
        last_dt = datetime.fromisoformat(last_date)
    except ValueError:
        return None
    today_dt = datetime.fromisoformat(_today_iso())
    return (today_dt - last_dt).days


def needs_rerun(manifest: dict[str, Any], current_query: str, current_area: str,
                year_start: int | None = None, year_end: int | None = None,
                bumping_version: bool = False) -> tuple[bool, str]:
    """Decide se a busca precisa ser re-executada (Decisão 22).

    Retorna (precisa_rerodar, motivo). Critérios:
    - Query/area/janela mudaram desde a última execução → sim.
    - Versão sendo incrementada (`bumping_version=True`) e última execução foi em
      data anterior à de hoje → sim.
    - Caso contrário, não.
    """
    runs = manifest.get("search_runs", [])
    if not runs:
        return True, "primeira execução de busca para este projeto"
    last = runs[-1]
    current_hash = _hash_query(current_query, current_area, year_start, year_end)
    if last.get("query_hash") != current_hash:
        return True, f"query/area/janela mudaram (hash {last.get('query_hash')} → {current_hash})"
    if bumping_version:
        last_date = last.get("ran_on_date") or last.get("ran_at", "")[:10]
        if last_date and last_date != _today_iso():
            return True, (f"incrementando versão e última busca foi em {last_date}; "
                          f"Decisão 22 exige re-execução em data nova")
    return False, "última execução está atualizada"


# ---- CLI ----

def _cli() -> int:
    p = argparse.ArgumentParser(description="Helpers para reproducibility_manifest.yaml.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("record-consent", help="Registra phase4_exclusions_review (Decisão 21).")
    p1.add_argument("--manifest", required=True)
    p1.add_argument("--n-excluded-title", type=int, default=0)
    p1.add_argument("--n-excluded-abstract", type=int, default=0)

    p2 = sub.add_parser("record-search", help="Registra search_runs[] (Decisão 22).")
    p2.add_argument("--manifest", required=True)
    p2.add_argument("--query", required=True)
    p2.add_argument("--area", required=True)
    p2.add_argument("--year-start", type=int)
    p2.add_argument("--year-end", type=int)
    p2.add_argument("--version", default=None)

    p3 = sub.add_parser("check-rerun", help="Verifica se precisa re-executar busca.")
    p3.add_argument("--manifest", required=True)
    p3.add_argument("--query", required=True)
    p3.add_argument("--area", required=True)
    p3.add_argument("--year-start", type=int)
    p3.add_argument("--year-end", type=int)
    p3.add_argument("--bumping-version", action="store_true")

    args = p.parse_args()
    manifest = load_manifest(args.manifest)

    if args.cmd == "record-consent":
        manifest = record_phase4_consent(manifest, args.n_excluded_title, args.n_excluded_abstract)
        save_manifest(manifest, args.manifest)
        print(f"[manifest] phase4_exclusions_review registrado em {args.manifest}")
    elif args.cmd == "record-search":
        manifest = record_search_run(
            manifest, query=args.query, area=args.area,
            year_start=args.year_start, year_end=args.year_end,
            version=args.version,
        )
        save_manifest(manifest, args.manifest)
        print(f"[manifest] search_run #{len(manifest['search_runs'])} registrada em {args.manifest}")
    elif args.cmd == "check-rerun":
        need, reason = needs_rerun(
            manifest, args.query, args.area,
            args.year_start, args.year_end, args.bumping_version,
        )
        print(f"needs_rerun={need} reason={reason!r}")
        return 0 if not need else 10  # exit 10 = pausa intencional
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
