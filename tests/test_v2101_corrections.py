"""Smoke tests v2.10.1 — correções de coerência operacional + pipeline_finalize."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# --- CRIT-1: TIER1_RUNNERS registra todos os adapters --------------------------

def test_tier1_runners_registers_all_iberoamerican_adapters():
    """Todos os adapters da Decisão 25 devem estar registrados em TIER1_RUNNERS."""
    import search_orchestrator
    runners = search_orchestrator.TIER1_RUNNERS
    expected = {"arxiv", "scielo", "dblp", "crossref", "semantic_scholar",
                "la_referencia", "redalyc", "clacso", "bdtd", "scioteca",
                "doaj", "lilacs", "core"}
    assert expected.issubset(set(runners.keys())), (
        f"TIER1_RUNNERS faltando: {expected - set(runners.keys())}"
    )


def test_tier1_runners_excludes_periodicos_capes():
    """Periódicos CAPES não roda automaticamente — é gateway com instruções."""
    import search_orchestrator
    assert "periodicos_capes" not in search_orchestrator.TIER1_RUNNERS


def test_tier1_runners_scripts_actually_exist():
    """Cada runner registrado aponta para um arquivo .py existente."""
    import search_orchestrator
    scripts_dir = search_orchestrator.SCRIPTS_DIR
    for db, runner in search_orchestrator.TIER1_RUNNERS.items():
        path = scripts_dir / runner
        assert path.exists(), f"runner '{runner}' (db={db}) não existe em {path}"


# --- CRIT-2: search_scielo trata 403 graciosamente -----------------------------

def test_search_scielo_has_mock_mode():
    """search_scielo aceita --mock e retorna fixture determinística."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "scielo.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/searches/search_scielo.py"),
             "--query", "teste", "--mock", "--output", str(out)],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, f"search_scielo --mock falhou: {result.stderr}"
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["source"] == "scielo"
        assert data["n"] >= 1


# --- CRIT-3: render_v2 sem path absoluto hardcoded -----------------------------

def test_render_v2_has_no_hardcoded_absolute_path():
    src = (ROOT / "scripts" / "render_v2.py").read_text(encoding="utf-8")
    # O path antigo era "/home/claude/ignorantia/assets/templates/manuscript-template-v2.html"
    assert "/home/claude/ignorantia/assets" not in src, (
        "VIOLAÇÃO CRIT-3: path absoluto hardcoded ainda presente em render_v2.py"
    )


# --- CRIT-4: DOAJ e LILACS adapters existem ------------------------------------

def test_doaj_adapter_mock():
    import search_doaj
    r = search_doaj.search("teste", 2020, 2026, mock=True)
    assert r["source"] == "doaj"
    assert r["source_tier"] == "tier1"
    assert all(res.get("is_oa") for res in r["results"])


def test_lilacs_adapter_mock():
    import search_lilacs
    r = search_lilacs.search("teste", 2020, 2026, mock=True)
    assert r["source"] == "lilacs"
    assert r["source_tier"] == "tier1"
    # LILACS é cobertura ibero-americana de saúde
    langs = {res.get("language") for res in r["results"]}
    assert {"pt", "es"} & langs


# --- IMP-1: vocabulário "Tier 3" → "priority_0_routing" ------------------------

def test_disclosure_pre_uses_priority_0_vocabulary():
    """Disclosure usa 'priority_0_routing' / 'Tier 0' / 'Tier 2 paywall' (v2.15.0), não 'Tier 3'."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "saude", "scoping_review", 2020, 2026, "letramento digital"
    )
    # Não deve dizer "Tier 3" como vocabulário do usuário
    occurrences = msg.lower().count("tier 3")
    assert occurrences == 0, (
        f"Decisão 24: 'Tier 3' apareceu {occurrences}x na disclosure user-facing.\n{msg}"
    )
    # v2.15.0: deve mencionar priority_0, Tier 0, OU Tier 2 paywall (cascata DD-8)
    msg_lower = msg.lower()
    assert (
        "priority_0" in msg_lower
        or "tier 0" in msg_lower
        or "tier 2 paywall" in msg_lower
    ), "Disclosure deveria mencionar bases pagas (priority_0 / Tier 0 / Tier 2 paywall)"


def test_mode_tier_policy_has_backward_compat_aliases():
    """Decisão 24: alias retro-compat tier3_via_user_only + priority_0_via_tier0_routing."""
    import search_orchestrator
    for mode, pol in search_orchestrator.MODE_TIER_POLICY.items():
        assert "priority_0_via_tier0_routing" in pol, f"falta priority_0_via_tier0_routing em {mode}"
        assert "tier3_via_user_only" in pol, f"falta alias tier3_via_user_only em {mode}"
        assert pol["priority_0_via_tier0_routing"] == pol["tier3_via_user_only"]


# --- IMP-2: phase4_exclusions_review no manifest -------------------------------

def test_record_phase4_consent(tmp_path):
    import manifest_helpers
    manifest = {}
    manifest = manifest_helpers.record_phase4_consent(
        manifest, n_excluded_title=1646, n_excluded_abstract=326,
    )
    assert manifest["phase4_exclusions_review"]["mode"] == "implicit_consent"
    assert manifest["phase4_exclusions_review"]["n_excluded_title_abstract"] == 1646
    assert manifest["phase4_exclusions_review"]["n_excluded_abstract_full"] == 326
    assert "consented_at" in manifest["phase4_exclusions_review"]


def test_manifest_save_load_roundtrip(tmp_path):
    import manifest_helpers
    p = tmp_path / "manifest.yaml"
    manifest = {"version": "1.0.0", "search_runs": []}
    manifest = manifest_helpers.record_phase4_consent(manifest)
    manifest_helpers.save_manifest(manifest, p)
    assert p.exists()
    loaded = manifest_helpers.load_manifest(p)
    assert loaded["phase4_exclusions_review"]["mode"] == "implicit_consent"


# --- IMP-3: Decisão 22 — search_runs + needs_rerun -----------------------------

def test_record_search_run_appends():
    import manifest_helpers
    manifest = {}
    manifest = manifest_helpers.record_search_run(
        manifest, query="x", area="saude", year_start=2020, year_end=2026,
    )
    assert len(manifest["search_runs"]) == 1
    assert manifest["search_runs"][0]["query"] == "x"
    assert "query_hash" in manifest["search_runs"][0]
    assert "last_run_date" in manifest


def test_needs_rerun_first_run():
    import manifest_helpers
    need, reason = manifest_helpers.needs_rerun(
        {}, "x", "saude", 2020, 2026, bumping_version=False,
    )
    assert need is True
    assert "primeira" in reason.lower()


def test_needs_rerun_query_changed():
    import manifest_helpers
    manifest = {}
    manifest = manifest_helpers.record_search_run(
        manifest, query="x", area="saude", year_start=2020, year_end=2026,
    )
    need, reason = manifest_helpers.needs_rerun(
        manifest, "y", "saude", 2020, 2026, bumping_version=False,
    )
    assert need is True
    assert "mudaram" in reason.lower() or "hash" in reason.lower()


def test_needs_rerun_same_query_no_bump():
    import manifest_helpers
    manifest = {}
    manifest = manifest_helpers.record_search_run(
        manifest, query="x", area="saude", year_start=2020, year_end=2026,
    )
    need, reason = manifest_helpers.needs_rerun(
        manifest, "x", "saude", 2020, 2026, bumping_version=False,
    )
    assert need is False


# --- CRIT-5: pipeline_finalize encadeia os 5 outputs ---------------------------

def _make_minimal_content(extra: dict | None = None) -> dict:
    """Cria content.json mínimo válido para o pipeline."""
    base = {
        "abstract": "Resumo de teste do pipeline finalize.",
        "keywords": ["pipeline", "teste"],
        "authors": ["Pesquisador, X."],
        "sections": [
            {
                "id": "01", "title": "Introdução",
                "content_html": "<p>Texto introdutório.</p>",
                "paragraphs": [{"text": "Texto introdutório.", "type": "body"}],
            },
            {
                "id": "02", "title": "Métodos",
                "content_html": "<p>Métodos PRISMA.</p>",
                "paragraphs": [{"text": "Métodos PRISMA.", "type": "body"}],
            },
        ],
        "references": [
            "SILVA, J. P. **Teste**. *Revista Brasileira*, v. 1, p. 1-10, 2023.",
        ],
    }
    if extra:
        base.update(extra)
    return base


def test_pipeline_finalize_runs_all_steps(tmp_path):
    """Pipeline executa as 5 etapas; falhas individuais não interrompem o todo."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    content = _make_minimal_content()
    (output_dir / "content.json").write_text(json.dumps(content), encoding="utf-8")
    # extraction.csv mínimo para cross-tab
    (output_dir / "extraction.csv").write_text(
        "model,task\nBERT,classification\nGPT,generation\n", encoding="utf-8"
    )

    import pipeline_finalize
    import argparse
    args = argparse.Namespace(
        title="Teste Pipeline", title_short="Pipeline", version="1.0.0",
        lang="pt-BR", date_iso="2026-05-03", license_str="CC-BY-4.0",
        file_hash="abc123",
        cross_tab_x="model", cross_tab_y="task", cross_tab_z=None,
        latex_engine="pdflatex",
        resume_from_chunk=None,
        skip_cross_tab=False, skip_format_abnt=False,
        skip_html=False, skip_docx=False, skip_tex=False, skip_pdf=False, skip_screening=True, screening_demo=False,
    )
    result = pipeline_finalize.run_pipeline(output_dir, args)
    assert result.n_ok >= 3, (
        f"esperava ≥3 etapas ok, obteve {result.n_ok}; "
        f"steps: {[(s.name, s.status, s.message) for s in result.steps]}"
    )
    # pipeline_summary.json deve existir
    assert (output_dir / "pipeline_summary.json").exists()
    # HTML, .docx ou .tex devem ter sido gerados
    artifact_names = {a.name for a in result.final_artifacts}
    assert any(name in artifact_names for name in
               ["manuscript.html", "manuscript.docx", "manuscript.tex"])


def test_pipeline_finalize_respects_skip_flags(tmp_path):
    """Flags --skip-* pulam etapas sem falhar."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    content = _make_minimal_content()
    (output_dir / "content.json").write_text(json.dumps(content), encoding="utf-8")

    import pipeline_finalize
    import argparse
    args = argparse.Namespace(
        title="Teste", title_short=None, version="1.0.0",
        lang="pt-BR", date_iso="2026-05-03", license_str="CC-BY-4.0",
        file_hash="abc",
        cross_tab_x=None, cross_tab_y=None, cross_tab_z=None,
        latex_engine="pdflatex",
        resume_from_chunk=None,
        skip_cross_tab=True, skip_format_abnt=True,
        skip_html=False, skip_docx=True, skip_tex=True, skip_pdf=False, skip_screening=True, screening_demo=False,
    )
    result = pipeline_finalize.run_pipeline(output_dir, args)
    skipped = [s for s in result.steps if s.status == "skipped"]
    assert len(skipped) >= 4  # cross_tab, format_abnt, docx, tex
    # HTML deve ter rodado
    html_step = next((s for s in result.steps if s.name == "render_html_chunks"), None)
    assert html_step is not None
    assert html_step.status == "ok", html_step.message


def test_pipeline_finalize_fails_gracefully_on_missing_content(tmp_path):
    """Sem content.json, deve falhar com mensagem clara, não crash."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    import pipeline_finalize
    import argparse
    args = argparse.Namespace(
        title="X", title_short=None, version="1.0.0",
        lang="pt-BR", date_iso="2026-05-03", license_str="CC-BY-4.0",
        file_hash="x",
        cross_tab_x=None, cross_tab_y=None, cross_tab_z=None,
        latex_engine="pdflatex",
        resume_from_chunk=None,
        skip_cross_tab=False, skip_format_abnt=False,
        skip_html=False, skip_docx=False, skip_tex=False, skip_pdf=False, skip_screening=True, screening_demo=False,
    )
    import pytest
    with pytest.raises(FileNotFoundError):
        pipeline_finalize.run_pipeline(output_dir, args)


def test_pipeline_summary_json_well_formed(tmp_path):
    """pipeline_summary.json é um JSON válido com schema esperado."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    content = _make_minimal_content()
    (output_dir / "content.json").write_text(json.dumps(content), encoding="utf-8")

    import pipeline_finalize
    import argparse
    args = argparse.Namespace(
        title="X", title_short=None, version="1.0.0",
        lang="pt-BR", date_iso="2026-05-03", license_str="CC-BY-4.0",
        file_hash="x",
        cross_tab_x=None, cross_tab_y=None, cross_tab_z=None,
        latex_engine="pdflatex",
        resume_from_chunk=None,
        skip_cross_tab=True, skip_format_abnt=True,
        skip_html=True, skip_docx=True, skip_tex=True, skip_pdf=True,
        skip_screening=True, screening_demo=False,
    )
    pipeline_finalize.run_pipeline(output_dir, args)
    summary = json.loads((output_dir / "pipeline_summary.json").read_text(encoding="utf-8"))
    assert "schema_version" in summary
    assert "steps" in summary
    assert len(summary["steps"]) == 6  # 6 etapas no pipeline (v2.18.1+: + screening_pipeline)
    assert all("name" in s and "status" in s for s in summary["steps"])
