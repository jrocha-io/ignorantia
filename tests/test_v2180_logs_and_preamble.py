"""Smoke tests v2.18.0 — Logs detalhados (R7/DD-10) + preâmbulo Wikipedia/Wikidata (R8/DD-11)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# ============ R7: Camada 1 — _log_enrichment ============

def test_log_enrichment_imports():
    from _log_enrichment import enrich_log_camada1, enrich_directory
    assert enrich_log_camada1 is not None
    assert enrich_directory is not None


def test_log_enrichment_generates_jsonl(tmp_path):
    """Camada 1: enrichment gera .jsonl com fetched/kept/discarded events."""
    # Criar fixture de results.json
    fake_result = {
        "source": "test_source",
        "method": "TEST_REAL",
        "total_results": 3,
        "results": [
            {"title": "Item 2020", "year": 2020, "language": "en", "doi": "10.1/a"},
            {"title": "Item 2018", "year": 2018, "language": "en", "doi": "10.1/b"},
            {"title": "Item 2024 ja", "year": 2024, "language": "ja", "doi": "10.1/c"},
        ],
    }
    json_path = tmp_path / "results_test.json"
    json_path.write_text(json.dumps(fake_result), encoding="utf-8")

    from _log_enrichment import enrich_log_camada1
    out = enrich_log_camada1(json_path,
                              year_start=2019, year_end=2025,
                              accepted_languages=["en", "pt", "es"])
    assert out is not None
    assert out.exists()

    events = [json.loads(line) for line in
              out.read_text(encoding="utf-8").strip().split("\n")]
    # Espera: fetched + kept + discarded_local
    assert len(events) >= 3
    fetched = next(e for e in events if e["event"] == "fetched")
    assert fetched["n"] == 3

    kept = next(e for e in events if e["event"] == "kept_after_local_filter")
    # Item 2018 sai por out_of_temporal_window; Item 2024 ja sai por language_not_accepted
    assert kept["n"] == 1
    assert kept["filter_reasons"]["out_of_temporal_window"] == 1
    assert kept["filter_reasons"]["language_not_accepted"] == 1

    discarded = next(e for e in events if e["event"] == "discarded_local")
    assert discarded["n"] == 2


def test_log_enrichment_uses_native_log_camada1(tmp_path):
    """Para PaywallAdapter results, native log_camada1 é incluído."""
    fake_result = {
        "source": "scopus_full",
        "method": "FALLBACK_MD",
        "total_results": 0,
        "results": [],
        "log_camada1": {
            "cascade_attempts": ["KEY_no_credential", "PROXY_no_credential",
                                  "FALLBACK_MD_generated: citations_to_obtain.md"],
        },
    }
    json_path = tmp_path / "results_scopus_full.json"
    json_path.write_text(json.dumps(fake_result), encoding="utf-8")

    from _log_enrichment import enrich_log_camada1
    out = enrich_log_camada1(json_path)
    events = [json.loads(line) for line in
              out.read_text(encoding="utf-8").strip().split("\n")]
    native = next((e for e in events
                   if e["event"] == "native_log_camada1_from_adapter"), None)
    assert native is not None
    assert "cascade_attempts" in native["data"]


def test_log_enrichment_directory_processes_all(tmp_path):
    """enrich_directory processa todos os results_*.json."""
    for src in ["alpha", "beta", "gamma"]:
        path = tmp_path / f"results_{src}.json"
        path.write_text(json.dumps({"source": src, "results": []}), encoding="utf-8")

    from _log_enrichment import enrich_directory
    enriched = enrich_directory(tmp_path)
    assert len(enriched) == 3
    for src in ["alpha", "beta", "gamma"]:
        assert (tmp_path / "logs" / f"logs_{src}.jsonl").exists()


# ============ R7: Camada 2 — screening_pipeline ============

def test_screening_pipeline_imports():
    from screening_pipeline import ScreeningPipeline, ScreeningEvent
    assert ScreeningPipeline is not None


def test_screening_pipeline_three_stages(tmp_path):
    """Screening em 3 estágios (title/abstract/full_text)."""
    studies = {"results": [
        {"study_id": "S001", "doi": "10.1/a", "title": "Mock 1", "year": 2023},
        {"study_id": "S002", "doi": "10.1/b", "title": "Mock 2", "year": 2024},
    ]}
    studies_path = tmp_path / "studies.json"
    studies_path.write_text(json.dumps(studies), encoding="utf-8")

    from screening_pipeline import ScreeningPipeline
    sp = ScreeningPipeline(tmp_path)
    sp.load_studies(studies_path)
    sp.decide("S001", "title", "kept", "relevant", "human")
    sp.decide("S002", "title", "discarded", "off_topic", "human")
    sp.decide("S001", "abstract", "kept", "good_design", "human")
    sp.decide("S001", "full_text", "kept", "high_quality", "human")

    csv_path = sp.export_csv()
    counts_path = sp.export_prisma_counts()

    assert csv_path.exists()
    assert counts_path.exists()

    # CSV tem 4 linhas (1 header + 4 events) — wait, 4 events
    csv_content = csv_path.read_text(encoding="utf-8")
    lines = csv_content.strip().split("\n")
    assert len(lines) == 5  # header + 4 events

    # Counts: title 1k+1d, abstract 1k+0d, full_text 1k+0d
    counts = json.loads(counts_path.read_text(encoding="utf-8"))
    assert counts["title_kept"] == 1
    assert counts["title_discarded"] == 1
    assert counts["abstract_kept"] == 1
    assert counts["full_text_kept"] == 1
    assert counts["discarded_reasons_by_stage"]["title"] == {"off_topic": 1}


def test_screening_pipeline_demo_cli(tmp_path):
    """CLI --demo aplica kept a todos."""
    studies = {"results": [
        {"study_id": "S001", "doi": "10.1/a", "title": "M", "year": 2023},
    ]}
    studies_path = tmp_path / "studies.json"
    studies_path.write_text(json.dumps(studies), encoding="utf-8")

    cmd = [sys.executable, str(ROOT / "scripts/screening_pipeline.py"),
           "--studies", str(studies_path),
           "--output-dir", str(tmp_path), "--demo"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert res.returncode == 0
    assert (tmp_path / "screening_log.csv").exists()


# ============ R8: contextual_preamble ============

def test_contextual_preamble_imports():
    from contextual_preamble import (ContextualPreamble, WikipediaSnippet,
                                       WikidataEntity)
    assert ContextualPreamble is not None


def test_contextual_preamble_mock_initializes(tmp_path):
    """Mock preamble cria fixtures determinísticas."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("letramento digital", area="educacao", language="pt-BR")
    assert cp.topic == "letramento digital"
    assert len(cp.wikipedia_snippets) == 2
    assert len(cp.wikidata_entities) == 1


def test_contextual_preamble_renders_html_with_section_id(tmp_path):
    """HTML render tem section id 'contextual-preamble' (DD-11)."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("test topic", area="multi", language="pt-BR")
    html = cp.render_html()
    assert 'id="contextual-preamble"' in html
    assert "O campo onde este artigo vive" in html
    assert "WIKIPEDIA" in html
    assert "WIKIDATA" in html


def test_contextual_preamble_html_in_english(tmp_path):
    """English language gera título adequado."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("test", area="multi", language="en-US")
    html = cp.render_html()
    assert "The field where this article lives" in html


def test_contextual_preamble_markdown_format():
    """Markdown render tem citações ABNT clicáveis."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("test", area="educacao", language="pt-BR")
    md = cp.render_markdown()
    assert "## O campo onde este artigo vive" in md
    assert "WIKIPEDIA" in md
    assert "[(WIKIPEDIA" in md  # citação clicável Markdown
    assert "Acesso em:" in md  # data de acesso ABNT


def test_contextual_preamble_pptx_slides_structure():
    """PPTX renderer gera slides com estrutura adequada."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("test", area="multi", language="pt-BR")
    slides = cp.render_pptx_slides()
    assert len(slides) >= 1
    # Primeiro slide é section_header
    assert slides[0]["type"] == "section_header"
    assert "O campo onde este artigo vive" in slides[0]["title"]


def test_contextual_preamble_distinct_from_introduction():
    """Preâmbulo declara explicitamente não substituir Introdução."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("test", area="multi", language="pt-BR")
    html = cp.render_html()
    assert ("não substitui a Introdução" in html.lower()
            or "Não substitui a Introdução" in html
            or "não-especialistas" in html.lower()
            or "não são especialistas" in html.lower())


def test_contextual_preamble_cli_html(tmp_path):
    """CLI gera HTML válido."""
    out_path = tmp_path / "p.html"
    cmd = [sys.executable, str(ROOT / "scripts/contextual_preamble.py"),
           "--topic", "test topic",
           "--area", "multi",
           "--language", "pt-BR",
           "--mock", "--format", "html",
           "--output", str(out_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert res.returncode == 0
    content = out_path.read_text(encoding="utf-8")
    assert "<section" in content
    assert "WIKIPEDIA" in content


def test_contextual_preamble_cli_markdown(tmp_path):
    """CLI gera Markdown válido."""
    out_path = tmp_path / "p.md"
    cmd = [sys.executable, str(ROOT / "scripts/contextual_preamble.py"),
           "--topic", "test", "--mock", "--format", "markdown",
           "--output", str(out_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert res.returncode == 0


def test_contextual_preamble_cli_json(tmp_path):
    """CLI gera JSON serializável."""
    out_path = tmp_path / "p.json"
    cmd = [sys.executable, str(ROOT / "scripts/contextual_preamble.py"),
           "--topic", "test", "--mock", "--format", "json",
           "--output", str(out_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert res.returncode == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "wikipedia_snippets" in data
    assert "wikidata_entities" in data
    assert data["topic"] == "test"


def test_contextual_preamble_cli_pptx_slides(tmp_path):
    """CLI gera estrutura de slides PPTX (JSON intermediário)."""
    out_path = tmp_path / "p.pptx.json"
    cmd = [sys.executable, str(ROOT / "scripts/contextual_preamble.py"),
           "--topic", "test", "--mock", "--format", "pptx",
           "--output", str(out_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert res.returncode == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "slides" in data
    assert len(data["slides"]) >= 1


def test_contextual_preamble_citation_format_abnt():
    """Citações no formato ABNT NBR 10520: (FONTE, "termo", acesso em DATA)."""
    from contextual_preamble import _mock_preamble
    cp = _mock_preamble("test", area="multi", language="pt-BR")
    snip = cp.wikipedia_snippets[0]
    cite = snip.to_citation()
    assert cite.startswith("(WIKIPEDIA")
    assert "acesso em" in cite
    # YYYY-MM-DD format
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}", cite)


def test_contextual_preamble_handles_empty_results():
    """Se Wikipedia/Wikidata retornarem vazio, declara honestamente."""
    from contextual_preamble import ContextualPreamble
    cp = ContextualPreamble(language="pt-BR")
    cp.set_topic("topic muito específico inexistente")
    # Não chama fetch_*, então listas ficam vazias
    html = cp.render_html()
    assert "Não foi possível recuperar contexto" in html or "contextual-warning" in html


# ============ Integração: TIER1_RUNNERS continua estável ============

def test_log_enrichment_does_not_break_orchestrator_runners():
    """Importar _log_enrichment não introduz erros no orchestrator."""
    import search_orchestrator
    # 57 runners deveria continuar (16 paywall + 41 v2.11.0)
    n = len(search_orchestrator.TIER1_RUNNERS)
    assert n == 57, f"esperado 57 runners (estado v2.15.0), encontrado {n}"
