"""Ingestor de snapshots manuais — para baselines sem API pública.

Conforme PROTOCOL.md §4.4 do mapeamento de baselines, ferramentas como Penelope.ai,
Elsevier Journal Finder, Springer Nature Suggester, Wiley JF, T&F Suggester, IEEE
Recommender e Web of Science Manuscript Matcher NÃO têm API REST pública. A única
abordagem reprodutível é submissão manual à UI + extração + JSON datado.

Este módulo carrega esses snapshots e os normaliza para o schema unificado.

Convenção de nomeação:
- `snapshots/<vendor>_<manuscript_id>_<YYYYMMDD>.json`
- vendor ∈ {penelope, elsevier_jf, springer_suggester, wiley_jf, tf_suggester,
            ieee_recommender, wos_manuscript_matcher}

Schema esperado de cada snapshot:
```json
{
  "vendor": "penelope",
  "snapshot_date": "2026-04-20",
  "manuscript_id": "ms_001",
  "venue_ranking": [...]                     // para recommenders
  "compliance_checks": {                     // para Penelope/GoodReports
    "passed": 18, "failed": 2, "details": [...]
  }
}
```
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_VENDORS = {
    "penelope", "goodreports",  # compliance
    "elsevier_jf", "springer_suggester", "wiley_jf", "tf_suggester",
    "ieee_recommender", "wos_manuscript_matcher",  # recommenders
}


@dataclass
class SnapshotResult:
    vendor: str
    snapshot_date: str
    manuscript_id: str
    venue_ranking: list[dict[str, Any]] = field(default_factory=list)
    compliance_checks: dict[str, Any] | None = None
    error: str | None = None


def load_snapshot(path: Path) -> SnapshotResult:
    """Carrega snapshot JSON e valida formato mínimo."""
    if not path.exists():
        return SnapshotResult(
            vendor="?", snapshot_date="?", manuscript_id="?",
            error=f"snapshot file not found: {path}",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return SnapshotResult(
            vendor="?", snapshot_date="?", manuscript_id="?",
            error=f"invalid JSON: {exc}",
        )

    vendor = data.get("vendor", "?")
    if vendor not in VALID_VENDORS:
        return SnapshotResult(
            vendor=vendor, snapshot_date=data.get("snapshot_date", "?"),
            manuscript_id=data.get("manuscript_id", "?"),
            error=f"unknown vendor '{vendor}' (valid: {sorted(VALID_VENDORS)})",
        )

    return SnapshotResult(
        vendor=vendor,
        snapshot_date=data.get("snapshot_date", "?"),
        manuscript_id=data.get("manuscript_id", "?"),
        venue_ranking=data.get("venue_ranking", []),
        compliance_checks=data.get("compliance_checks"),
    )


def load_all_snapshots(snapshots_dir: Path, manuscript_id: str) -> dict[str, SnapshotResult]:
    """Carrega todos os snapshots de um manuscrito específico, indexados por vendor."""
    if not snapshots_dir.exists():
        return {}
    out: dict[str, SnapshotResult] = {}
    for p in sorted(snapshots_dir.glob(f"*_{manuscript_id}_*.json")):
        snap = load_snapshot(p)
        if snap.error:
            print(f"[snapshot] WARNING in {p.name}: {snap.error}", file=sys.stderr)
            continue
        out[snap.vendor] = snap
    return out


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Ingestor de snapshots manuais.")
    parser.add_argument("--snapshots-dir", required=True,
                        help="Diretório com snapshots: <vendor>_<msid>_<date>.json")
    parser.add_argument("--manuscript-id", required=True)
    parser.add_argument("--out", required=True, help="Output consolidado JSON.")
    args = parser.parse_args()

    snaps = load_all_snapshots(Path(args.snapshots_dir), args.manuscript_id)
    out = {vendor: asdict(snap) for vendor, snap in snaps.items()}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[snapshot] {len(snaps)} vendors loaded for {args.manuscript_id} → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
