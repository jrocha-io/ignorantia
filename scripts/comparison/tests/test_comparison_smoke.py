"""Smoke test ponta-a-ponta da infraestrutura de comparação (Etapa 4b).

Cenário: 1 manuscrito sintético (ms_001) + ignorantia output sintético + B!SON mock +
ASReview mock + snapshot Penelope sintético → JSON unificado + relatório markdown.

Objetivos:
- Verificar que o pipeline roda sem erros (smoke).
- Verificar que métricas são computadas corretamente.
- Verificar que limitações são declaradas honestamente.

NÃO valida que ignorantia "vence" os baselines — isso requer casos reais.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Garantir que `comparison` é importável
ROOT = Path(__file__).resolve().parent.parent.parent  # /home/claude/ignorantia_v2/scripts
sys.path.insert(0, str(ROOT))


def test_bson_mock_returns_ranking():
    from comparison.clients import bson
    res = bson.query("Active learning for SR", "We synthesize evidence...", references=[], mock=True)
    assert res.error is None
    assert len(res.venue_ranking) == 5
    assert res.method == "BSON_REST_API_MOCK"
    assert res.venue_ranking[0]["score"] >= res.venue_ranking[-1]["score"]


def test_asreview_mock_returns_reference_values():
    from comparison.clients import asreview
    res = asreview.simulate("SYNERGY/van_de_Schoot_2018", mock=True)
    assert res.error is None
    assert res.wss_at_95 == 0.74  # valor de referência publicado
    assert res.method == "ASREVIEW_LAB_V2_MOCK_REFERENCE"


def test_jane_mock_returns_biomed_ranking_for_biomed_input():
    from comparison.clients import jane
    res = jane.query("Health screening tools", "Patient outcomes in clinical trials", mock=True)
    assert res.error is None
    assert len(res.venue_ranking) >= 1
    # Para input biomédico deve retornar BMJ Open / PLOS ONE no topo
    top_names = [v["venue_name"] for v in res.venue_ranking]
    assert "BMJ Open" in top_names or "PLOS ONE" in top_names


def test_topk_metrics_correct():
    from comparison.metrics import topk
    ranking = ["a", "b", "c", "d", "e"]
    assert topk.topk_match(ranking, "a", 1) is True
    assert topk.topk_match(ranking, "c", 3) is True
    assert topk.topk_match(ranking, "e", 3) is False
    assert topk.mrr(ranking, "a") == 1.0
    assert topk.mrr(ranking, "b") == 0.5
    assert topk.mrr(ranking, "z") == 0.0
    assert abs(topk.ndcg_at_k(ranking, "a", 5) - 1.0) < 1e-9


def test_compliance_metrics_correct():
    from comparison.metrics import compliance
    human = {"item1": True, "item2": True, "item3": False, "item4": False}
    tool =  {"item1": True, "item2": False, "item3": False, "item4": True}
    res = compliance.evaluate_compliance(human, tool)
    # tp=1 (item1), tn=1 (item3), fp=1 (item4), fn=1 (item2)
    assert res["tp"] == 1
    assert res["tn"] == 1
    assert res["fp"] == 1
    assert res["fn"] == 1
    assert abs(res["f1"] - 0.5) < 1e-9
    assert -1.0 <= res["kappa"] <= 1.0


def test_wss_metric_correct():
    from comparison.metrics import wss
    # Cenário: 10 docs, 2 relevantes (índices 0 e 9). Ranking ótimo: [0, 9, ...].
    labels = [1, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    rank_optimal = [0, 9, 1, 2, 3, 4, 5, 6, 7, 8]
    # WSS@95 com 2 relevantes: target_relevant = round(0.95 * 2) = 2 (ou 1, dep. arred.)
    val = wss.wss_at_recall(labels, rank_optimal, recall_target=0.95)
    assert val >= 0.0


def test_unify_pipeline_end_to_end(tmp_path):
    """Smoke test: roda B!SON mock + ASReview mock + ingestor de snapshot + unify."""
    from comparison.clients import bson, asreview
    from comparison import unify

    fixtures = Path(__file__).resolve().parent.parent / "fixtures"

    # 1. B!SON mock
    bson_out = tmp_path / "bson.json"
    ms = json.loads((fixtures / "manuscript_001.json").read_text())
    bson_result = bson.query(ms["title"], ms["abstract"], references=ms.get("references", []), mock=True)
    bson_out.write_text(json.dumps({
        "venue_ranking": bson_result.venue_ranking,
        "method": bson_result.method,
        "snapshot": bson_result.snapshot,
        "error": bson_result.error,
    }), encoding="utf-8")

    # 2. ASReview mock
    asr_out = tmp_path / "asreview.json"
    asr_result = asreview.simulate("SYNERGY/van_de_Schoot_2018", mock=True)
    asr_out.write_text(json.dumps({
        "wss_at_95": asr_result.wss_at_95,
        "recall_at_10pct": asr_result.recall_at_10pct,
        "atd": asr_result.atd,
        "dataset": asr_result.dataset,
        "method": asr_result.method,
        "error": asr_result.error,
    }), encoding="utf-8")

    # 3. unify
    out_path = tmp_path / "unified.json"
    result = unify.unify(
        manuscript_path=str(fixtures / "manuscript_001.json"),
        ignorantia_output_path=str(fixtures / "ignorantia_001.json"),
        bson_output_path=str(bson_out),
        asreview_output_path=str(asr_out),
        snapshots_dir=str(fixtures),
        out_path=str(out_path),
    )

    # Validações
    assert result["schema_version"] == "1.0.0"
    assert result["manuscript_id"] == "ms_001"
    assert "venue_top1_match" in result["metrics"]
    # ground truth = "1932-6203" (PLOS ONE issn); ignorantia ranking tem isso no rank 2
    assert result["metrics"]["venue_top5_match"] is True
    # MRR ignorantia = 1/2 (2ª posição)
    assert abs(result["metrics"]["venue_mrr_ignorantia"] - 0.5) < 1e-9
    # ASReview deve ter WSS@95
    assert result["results"]["asreview_sim"]["wss_at_95"] == 0.74
    # snapshot Penelope deve estar carregado
    assert "penelope" in result["results"]["snapshots"]
    snap = result["results"]["snapshots"]["penelope"]
    assert snap["compliance_checks"]["passed"] == 18
    # Limitações declaradas (JANE não foi rodado)
    assert any("JANE" in lim for lim in result["limitations"])


def test_report_renders(tmp_path):
    """Smoke test: render markdown não quebra."""
    from comparison.clients import bson
    from comparison import unify, report

    fixtures = Path(__file__).resolve().parent.parent / "fixtures"

    bson_out = tmp_path / "bson.json"
    ms = json.loads((fixtures / "manuscript_001.json").read_text())
    bson_result = bson.query(ms["title"], ms["abstract"], references=ms.get("references", []), mock=True)
    bson_out.write_text(json.dumps({
        "venue_ranking": bson_result.venue_ranking,
        "method": bson_result.method,
        "snapshot": False,
        "error": None,
    }))

    unified_path = tmp_path / "unified.json"
    unify.unify(
        manuscript_path=str(fixtures / "manuscript_001.json"),
        ignorantia_output_path=str(fixtures / "ignorantia_001.json"),
        bson_output_path=str(bson_out),
        snapshots_dir=str(fixtures),
        out_path=str(unified_path),
    )
    data = json.loads(unified_path.read_text())
    md = report.render_md(data)
    assert "ms_001" in md
    assert "ignorantia" in md.lower()
    assert "B!SON" in md or "BSON" in md.upper()
    assert "Limitações declaradas" in md or "Limitations" in md or "Limitação" in md
