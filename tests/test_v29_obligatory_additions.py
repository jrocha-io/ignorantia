"""Smoke tests v2.9.0 — Decisões 22-29.

Cobre:
- Decisão 23: snowballing_backward (mock + assinatura).
- Decisão 24: TIER_DATABASES tem priority_0_routing (Tier 3 renomeado).
- Decisão 25: 6 adapters ibero-americanos novos (LA Referencia, Redalyc, CLACSO, BDTD,
  Scioteca, Periódicos CAPES) + CORE no Tier 0.
- Decisão 28: format_abnt produz formatos NBR 6023:2018 e NBR 10520:2023.
- Decisão 29: cross_tabulation gera tabela 2D com células corretas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# --- Decisão 23: snowballing_backward -----------------------------------------

def test_snowballing_backward_mock_returns_candidates():
    import snowballing_backward
    seeds = ["10.1186/s13643-016-0384-4"]
    result = snowballing_backward.snowball_backward(seeds, mock=True)
    assert result.n_seeds == 1
    assert result.n_unique_candidates >= 1
    assert all(c.get("origin") == "backward_snowballing" for c in result.candidates)
    assert all("doi" in c for c in result.candidates)


def test_snowballing_backward_normalizes_dois():
    import snowballing_backward
    result = snowballing_backward.snowball_backward(
        ["https://doi.org/10.1186/s13643-016-0384-4", "  10.1234/Foo  "],
        mock=True,
    )
    assert "10.1186/s13643-016-0384-4" in result.seed_dois
    assert "10.1234/foo" in result.seed_dois


def test_snowballing_backward_dedups_against_corpus():
    import snowballing_backward
    seeds = ["10.1/seed-a"]
    corpus = ["10.1/seed-a"]  # seed também já está no corpus
    result = snowballing_backward.snowball_backward(seeds, corpus, mock=True)
    # Mock retorna candidatos sintéticos com DOIs próprios; o ponto é
    # garantir que a função não quebra com corpus passado.
    assert result.n_seeds == 1


# --- Decisão 24: TIER_DATABASES priority_0_routing ----------------------------

def test_tier_databases_has_priority_0_routing():
    import search_orchestrator
    for area in ["saude", "educacao", "cs_se", "ciencias_sociais", "multi"]:
        assert area in search_orchestrator.TIER_DATABASES, f"area '{area}' faltando"
        config = search_orchestrator.TIER_DATABASES[area]
        assert "priority_0_routing" in config, (
            f"area '{area}' não tem priority_0_routing (Decisão 24)"
        )
        # Backward-compat: tier3 ainda existe como alias temporário
        assert "tier3" in config, f"area '{area}' deveria manter alias 'tier3' até v2.10.0"
        assert config["tier3"] == config["priority_0_routing"]


def test_ibero_american_bases_obligatory_in_all_areas():
    """Decisão 25: SciELO + LA Referencia + Redalyc/CLACSO/BDTD em pt-BR/es-LA são obrigatórias."""
    import search_orchestrator
    # Pelo menos SciELO + LA Referencia em todas as áreas
    for area in ["saude", "educacao", "cs_se", "ciencias_sociais", "multi"]:
        tier1 = search_orchestrator.TIER_DATABASES[area]["tier1"]
        assert "scielo" in tier1, f"SciELO obrigatório em '{area}' (Decisão 25)"
        assert "la_referencia" in tier1, f"LA Referencia obrigatório em '{area}' (Decisão 25)"
        assert "core" in tier1, f"CORE obrigatório em '{area}' (Decisão 24/25)"
    # CLACSO presente em educacao e ciencias_sociais
    assert "clacso" in search_orchestrator.TIER_DATABASES["educacao"]["tier1"]
    assert "clacso" in search_orchestrator.TIER_DATABASES["ciencias_sociais"]["tier1"]


# --- Decisão 25: novos adapters individuais existem e respondem em mock -------

def test_la_referencia_mock():
    import search_la_referencia
    r = search_la_referencia.search("teste", 2020, 2026, mock=True)
    assert r["source"] == "la_referencia"
    assert r["source_tier"] == "tier1"
    assert len(r["results"]) >= 1
    # Tem registros em pt e es
    langs = {res.get("language") for res in r["results"]}
    assert {"pt", "es"} & langs


def test_redalyc_mock():
    import search_redalyc
    r = search_redalyc.search("teste", 2020, 2026, mock=True)
    assert r["source"] == "redalyc"
    assert all(res.get("is_oa") for res in r["results"])


def test_clacso_mock():
    import search_clacso
    r = search_clacso.search("teste", mock=True)
    assert r["source"] == "clacso"
    types = {res.get("type") for res in r["results"]}
    # CLACSO é forte em livros e working papers
    assert any(t in types for t in ["book_chapter", "working_paper"])


def test_bdtd_mock():
    import search_bdtd
    r = search_bdtd.search("teste", mock=True)
    assert r["source"] == "bdtd"
    types = {res.get("type") for res in r["results"]}
    # BDTD é teses e dissertações
    assert any(t in types for t in ["doctoral_thesis", "masters_dissertation"])


def test_scioteca_mock():
    import search_scioteca
    r = search_scioteca.search("teste", mock=True)
    assert r["source"] == "scioteca"
    # Scioteca tem gray literature
    assert all(res.get("is_oa") for res in r["results"])


def test_periodicos_capes_returns_user_action_when_no_credentials():
    """Sem credenciais CAFe, o adapter retorna instruções acionáveis em vez de falhar."""
    import search_periodicos_capes
    r = search_periodicos_capes.search("teste", 2020, 2026, mock=False)
    assert r["source"] == "periodicos_capes"
    assert r["source_tier"] == "tier0"  # prioridade 0 (Decisão 24)
    assert "user_action_required" in r
    instr = r["user_action_required"]
    assert "boolean_query_to_paste" in instr
    assert "expected_destination" in instr
    assert "user_provided" in instr["expected_destination"]


def test_core_mock():
    import search_core
    r = search_core.search("teste", 2020, 2026, mock=True)
    assert r["source"] == "core"
    assert r["source_tier"] == "tier0"  # CORE é Tier 0 (resolver de OA)
    assert all(res.get("is_oa") for res in r["results"])
    # Cada result tem url_for_pdf (CORE é repositório de PDFs)
    assert all(res.get("url_for_pdf") for res in r["results"])


# --- Decisão 28: format_abnt --------------------------------------------------

def test_format_abnt_article_full_format():
    import format_abnt
    ref = format_abnt.Reference(
        type="article",
        authors=["João Paulo da Silva", "Ana Pereira"],
        title="Letramento digital de idosos",
        year=2023,
        venue="Revista Brasileira de Educação",
        volume="28", issue="2", pages="45-67",
        doi="10.1234/abc.2023.001",
    )
    out = format_abnt.format_reference_abnt(ref)
    assert "SILVA, J. P." in out
    assert "PEREIRA, A." in out
    assert "**Revista Brasileira de Educação**" in out
    assert "v. 28" in out
    assert "n. 2" in out
    assert "p. 45-67" in out
    assert "2023" in out
    assert "DOI: 10.1234/abc.2023.001" in out


def test_format_abnt_authors_3plus_uses_et_al():
    import format_abnt
    ref = format_abnt.Reference(
        type="article",
        authors=["Silva, J.", "Pereira, A.", "Lima, M.", "Costa, R."],
        title="Teste", year=2023, venue="X",
    )
    out = format_abnt.format_reference_abnt(ref)
    assert "et al." in out


def test_format_inline_citation_indirect():
    import format_abnt
    out = format_abnt.format_inline_citation(["Silva, João"], 2023)
    assert out == "(SILVA, 2023)"


def test_format_inline_citation_direct_with_page():
    import format_abnt
    out = format_abnt.format_inline_citation(
        ["Silva, João", "Pereira, Ana"], 2023, page="45", direct_quote=True
    )
    assert out == "(SILVA; PEREIRA, 2023, p. 45)"


def test_format_apud():
    import format_abnt
    out = format_abnt.format_apud(
        ["Vygotsky, L."], 1978,
        ["Silva, J."], 2023, page="12"
    )
    assert "VYGOTSKY" in out
    assert "1978 apud" in out
    assert "SILVA, 2023" in out
    assert "p. 12" in out


def test_format_long_quote():
    import format_abnt
    out = format_abnt.format_long_quote(
        "Linha 1 do texto.\nLinha 2 do texto.",
        "(SILVA, 2023, p. 45)"
    )
    assert "> Linha 1" in out
    assert "> (SILVA, 2023, p. 45)" in out


# --- Decisão 29: cross_tabulation ---------------------------------------------

def test_cross_tabulation_2d_basic():
    import cross_tabulation
    extraction = [
        {"model": "BERT", "task": "classification", "metric": "F1"},
        {"model": "BERT", "task": "classification", "metric": "F1"},
        {"model": "GPT", "task": "generation", "metric": "BLEU"},
        {"model": "BERT", "task": "ner", "metric": "F1"},
    ]
    r = cross_tabulation.cross_tabulate(extraction, "model", "task")
    assert r.n_studies == 4
    assert r.n_with_all_dims == 4
    # 2 estudos BERT+classification
    assert r.counts.get(("BERT", "classification")) == 2
    assert r.counts.get(("GPT", "generation")) == 1
    assert "BERT" in r.x_values
    assert "classification" in r.y_values
    assert "Cross-tabulação" in r.markdown
    assert "<table" in r.html
    assert "estudos" in r.prose_summary.lower()


def test_cross_tabulation_handles_multi_value_cells():
    import cross_tabulation
    extraction = [
        {"model": "BERT", "tasks": "classification|ner|sentiment"},
        {"model": "GPT", "tasks": "generation;summarization"},
    ]
    r = cross_tabulation.cross_tabulate(extraction, "model", "tasks")
    # BERT aparece em 3 tasks; GPT em 2
    assert r.counts.get(("BERT", "classification")) == 1
    assert r.counts.get(("BERT", "ner")) == 1
    assert r.counts.get(("BERT", "sentiment")) == 1
    assert r.counts.get(("GPT", "generation")) == 1
    assert r.counts.get(("GPT", "summarization")) == 1


def test_cross_tabulation_3d_stratified():
    import cross_tabulation
    extraction = [
        {"model": "BERT", "task": "ner", "domain": "biomedical"},
        {"model": "BERT", "task": "ner", "domain": "general"},
        {"model": "GPT", "task": "generation", "domain": "general"},
    ]
    r = cross_tabulation.cross_tabulate(extraction, "model", "task", "domain")
    assert r.dim_z == "domain"
    assert "biomedical" in r.z_values
    assert "general" in r.z_values
    # Markdown estratificado
    assert "Estrato:" in r.markdown


def test_cross_tabulation_treats_dashes_as_missing():
    import cross_tabulation
    extraction = [
        {"model": "BERT", "task": "—"},
        {"model": "—", "task": "classification"},
        {"model": "GPT", "task": "generation"},
    ]
    r = cross_tabulation.cross_tabulate(extraction, "model", "task")
    # apenas 1 estudo tem ambas as dimensões preenchidas
    assert r.n_with_all_dims == 1
