"""Gera relatório markdown comparativo a partir do JSON unificado."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def render_md(unified: dict) -> str:
    """Renderiza JSON unificado como markdown."""
    msid = unified["manuscript_id"]
    meta = unified.get("manuscript_meta", {})
    gt = unified.get("ground_truth", {})
    metrics = unified.get("metrics", {})
    results = unified.get("results", {})

    lines = []
    lines.append(f"# Comparison Report — `{msid}`")
    lines.append("")
    lines.append(f"- **Generated:** {unified.get('timestamp', '?')}")
    lines.append(f"- **Schema version:** {unified.get('schema_version')}")
    lines.append(f"- **ignorantia version:** {unified.get('ignorantia_version')}")
    lines.append(f"- **Title:** {meta.get('title', '?')}")
    lines.append(f"- **Language:** {meta.get('language', '?')} | **Mode:** {meta.get('mode', '?')}")
    lines.append(f"- **Ground truth venue:** `{gt.get('venue_id', '?')}` ({gt.get('tier', '?')})")
    lines.append("")

    lines.append("## Métricas")
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Top-1 match (ignorantia) | {metrics.get('venue_top1_match')} |")
    lines.append(f"| Top-5 match (ignorantia) | {metrics.get('venue_top5_match')} |")
    lines.append(f"| Top-10 match (ignorantia) | {metrics.get('venue_top10_match')} |")
    lines.append(f"| MRR (ignorantia) | {_fmt_num(metrics.get('venue_mrr_ignorantia'))} |")
    lines.append(f"| MRR (B!SON) | {_fmt_num(metrics.get('venue_mrr_bson'))} |")
    lines.append(f"| MRR (JANE) | {_fmt_num(metrics.get('venue_mrr_jane'))} |")
    lines.append(f"| nDCG@10 (ignorantia) | {_fmt_num(metrics.get('venue_ndcg10_ignorantia'))} |")
    lines.append(f"| F1 compliance (ignorantia vs human) | {_fmt_num(metrics.get('compliance_f1_ignorantia_vs_human'))} |")
    lines.append(f"| Cohen's κ compliance | {_fmt_num(metrics.get('compliance_kappa_ignorantia_vs_human'))} |")
    lines.append("")

    # Ignorantia ranking (se houver)
    ign = results.get("ignorantia") or {}
    if ign.get("venue_ranking"):
        lines.append("## ignorantia — Top-10 venues")
        lines.append("")
        lines.append("| # | venue_id | score | tier |")
        lines.append("|---|---|---|---|")
        for i, item in enumerate(ign["venue_ranking"][:10], start=1):
            lines.append(f"| {i} | `{item.get('venue_id', '?')}` | "
                         f"{_fmt_num(item.get('score'))} | "
                         f"{item.get('fallback_tier', '?')} |")
        lines.append("")

    # BSON ranking
    bson = results.get("bson") or {}
    if bson.get("venue_ranking"):
        lines.append(f"## B!SON — Top-10 ({bson.get('method', '?')})")
        lines.append("")
        lines.append("| # | venue_name | issn | score | APC USD |")
        lines.append("|---|---|---|---|---|")
        for i, item in enumerate(bson["venue_ranking"][:10], start=1):
            lines.append(f"| {i} | {item.get('venue_name', '?')} | "
                         f"`{item.get('issn', '?')}` | "
                         f"{_fmt_num(item.get('score'))} | "
                         f"{item.get('apc_usd', '?')} |")
        lines.append("")

    # ASReview
    asr = results.get("asreview_sim") or {}
    if asr and asr.get("dataset"):
        lines.append("## ASReview LAB v2 — Simulação")
        lines.append("")
        lines.append(f"- **Dataset:** {asr.get('dataset')}")
        lines.append(f"- **Method:** {asr.get('method')}")
        lines.append(f"- **WSS@95:** {_fmt_num(asr.get('wss_at_95'))}")
        lines.append(f"- **Recall@10%:** {_fmt_num(asr.get('recall_at_10pct'))}")
        lines.append(f"- **ATD:** {asr.get('atd')}")
        if asr.get("error"):
            lines.append(f"- **Error/note:** {asr['error']}")
        lines.append("")

    # Snapshots manuais
    snaps = results.get("snapshots") or {}
    if snaps:
        lines.append("## Snapshots manuais")
        lines.append("")
        for vendor, snap in snaps.items():
            lines.append(f"### {vendor} (snapshot {snap.get('snapshot_date', '?')})")
            ranking = snap.get("venue_ranking") or []
            comp = snap.get("compliance_checks")
            if ranking:
                lines.append("")
                lines.append("| # | venue_name |")
                lines.append("|---|---|")
                for i, item in enumerate(ranking[:10], start=1):
                    lines.append(f"| {i} | {item.get('venue_name', item.get('name', '?'))} |")
            if comp:
                lines.append("")
                lines.append(f"- Checks passed: {comp.get('passed')}")
                lines.append(f"- Checks failed: {comp.get('failed')}")
            lines.append("")

    # Limitações
    lims = unified.get("limitations") or []
    if lims:
        lines.append("## Limitações declaradas")
        lines.append("")
        for lim in lims:
            lines.append(f"- {lim}")
        lines.append("")

    return "\n".join(lines)


def _fmt_num(x) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, (int, float)):
        return f"{x:.4f}" if isinstance(x, float) else str(x)
    return str(x)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Render relatório markdown.")
    parser.add_argument("--input", required=True, help="JSON unificado.")
    parser.add_argument("--out", required=True, help="Output markdown.")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    md = render_md(data)
    Path(args.out).write_text(md, encoding="utf-8")
    print(f"[report] {len(md)} chars → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
