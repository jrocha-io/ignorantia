"""Unifica outputs de baselines + ignorantia + ground truth em JSON único.

Schema: schemas/unified_output.schema.json (versão 1.0.0).
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Permitir import dos módulos do package quando rodado como script
if __package__ is None or __package__ == "":
    SCRIPT_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from comparison.metrics import topk as topk_metrics  # noqa: E402
from comparison.metrics import compliance as compliance_metrics  # noqa: E402

SCHEMA_VERSION = "1.0.0"
IGNORANTIA_VERSION = "2.5.0"


def _safe_load(path: str | None) -> dict | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[unify] WARNING: could not parse {path}: {exc}", file=sys.stderr)
        return None


def _extract_venue_ids(ranking: list[dict] | None) -> list[str]:
    """Extrai venue_ids/issns/names em ordem para uso em métricas top-k.

    Convenção: usar `venue_id` se disponível, senão `issn`, senão `venue_name`.
    """
    if not ranking:
        return []
    out = []
    for item in ranking:
        if not isinstance(item, dict):
            continue
        vid = item.get("venue_id") or item.get("issn") or item.get("venue_name") or item.get("name")
        if vid:
            out.append(str(vid))
    return out


def unify(manuscript_path: str,
          ignorantia_output_path: str | None = None,
          bson_output_path: str | None = None,
          jane_output_path: str | None = None,
          asreview_output_path: str | None = None,
          snapshots_dir: str | None = None,
          out_path: str = "/tmp/unified.json") -> dict:
    """Consolida tudo em JSON unificado e calcula métricas."""
    manuscript = json.loads(Path(manuscript_path).read_text(encoding="utf-8"))
    msid = manuscript["manuscript_id"]
    gt = manuscript.get("ground_truth", {})
    gt_venue_id = gt.get("venue_id", "")

    ign = _safe_load(ignorantia_output_path) or {}
    bson = _safe_load(bson_output_path) or {}
    jane = _safe_load(jane_output_path) or {}
    asr = _safe_load(asreview_output_path) or {}

    # Snapshots
    snapshots: dict = {}
    if snapshots_dir:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from comparison.clients.snapshot import load_all_snapshots  # noqa: E402
        loaded = load_all_snapshots(Path(snapshots_dir), msid)
        for vendor, snap in loaded.items():
            snapshots[vendor] = {
                "vendor": snap.vendor, "snapshot_date": snap.snapshot_date,
                "venue_ranking": snap.venue_ranking,
                "compliance_checks": snap.compliance_checks,
            }

    # Métricas: top-k (recommenders)
    ign_ranking_ids = _extract_venue_ids(ign.get("venue_ranking"))
    bson_ranking_ids = _extract_venue_ids(bson.get("venue_ranking"))
    jane_ranking_ids = _extract_venue_ids(jane.get("venue_ranking"))

    metrics = {
        "venue_top1_match": topk_metrics.topk_match(ign_ranking_ids, gt_venue_id, 1),
        "venue_top5_match": topk_metrics.topk_match(ign_ranking_ids, gt_venue_id, 5),
        "venue_top10_match": topk_metrics.topk_match(ign_ranking_ids, gt_venue_id, 10),
        "venue_mrr_ignorantia": topk_metrics.mrr(ign_ranking_ids, gt_venue_id),
        "venue_mrr_bson": topk_metrics.mrr(bson_ranking_ids, gt_venue_id) if bson_ranking_ids else None,
        "venue_mrr_jane": topk_metrics.mrr(jane_ranking_ids, gt_venue_id) if jane_ranking_ids else None,
        "venue_ndcg10_ignorantia": topk_metrics.ndcg_at_k(ign_ranking_ids, gt_venue_id, 10),
        "compliance_f1_ignorantia_vs_human": None,
        "compliance_kappa_ignorantia_vs_human": None,
    }

    # Compliance (se houver anotação humana)
    human_annot = manuscript.get("compliance_annotation")
    if human_annot and ign.get("compliance_per_item"):
        human_dict = {k: v["compliant"] for k, v in human_annot.items()}
        tool_dict = {k: v.get("compliant", False) for k, v in ign["compliance_per_item"].items()}
        comp_eval = compliance_metrics.evaluate_compliance(human_dict, tool_dict)
        metrics["compliance_f1_ignorantia_vs_human"] = comp_eval.get("f1")
        metrics["compliance_kappa_ignorantia_vs_human"] = comp_eval.get("kappa")

    limitations = []
    if not bson:
        limitations.append("BSON não foi executado para este manuscrito.")
    elif bson.get("error"):
        limitations.append(f"BSON: {bson['error']}")
    if not jane:
        limitations.append("JANE não foi executado para este manuscrito.")
    elif jane.get("error"):
        limitations.append(f"JANE: {jane['error']}")
    if not snapshots:
        limitations.append("Nenhum snapshot manual carregado (Penelope/Elsevier/etc.).")

    unified = {
        "evaluation_id": str(uuid.uuid4()),
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ignorantia_version": IGNORANTIA_VERSION,
        "manuscript_id": msid,
        "manuscript_meta": {
            "title": manuscript.get("title"),
            "language": manuscript.get("language"),
            "mode": manuscript.get("mode"),
        },
        "ground_truth": gt,
        "results": {
            "ignorantia": ign,
            "bson": bson,
            "jane": jane,
            "asreview_sim": asr,
            "snapshots": snapshots,
        },
        "metrics": metrics,
        "limitations": limitations,
    }
    Path(out_path).write_text(json.dumps(unified, indent=2, ensure_ascii=False), encoding="utf-8")
    return unified


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Unifica outputs em JSON unificado.")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--ignorantia", help="Path para output do ignorantia engine.")
    parser.add_argument("--bson", help="Path para output BSON.")
    parser.add_argument("--jane", help="Path para output JANE.")
    parser.add_argument("--asreview", help="Path para output ASReview.")
    parser.add_argument("--snapshots-dir", help="Diretório com snapshots manuais.")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    unified = unify(
        manuscript_path=args.manuscript,
        ignorantia_output_path=args.ignorantia,
        bson_output_path=args.bson,
        jane_output_path=args.jane,
        asreview_output_path=args.asreview,
        snapshots_dir=args.snapshots_dir,
        out_path=args.out,
    )
    print(f"[unify] {len(unified['limitations'])} limitations declared → {args.out}")
    for lim in unified["limitations"]:
        print(f"  · {lim}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
