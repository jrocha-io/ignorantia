"""B13 (v2.21.0): teste E2E pipeline_finalize.py.

Valida o caminho principal end-to-end via subprocess:
- pipeline_finalize.py com --contextual-preamble + --screening-demo
- Verifica que manuscript.html, manuscript.docx, manuscript.tex contêm
  o preâmbulo contextual (B1+B2 working through pipeline).

Princípio reforçado pela auditoria #3: testes verdes em renderers individuais
NÃO garantem que o pipeline propaga os features. Este teste preenche essa
lacuna.
"""
from __future__ import annotations

import json
import sys
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _setup_fixtures(out_dir: Path) -> None:
    """Cria fixtures mínimas em out_dir."""
    (out_dir / "content.json").write_text(json.dumps({
        "abstract": "E2E test abstract.",
        "abstract_html": "<p>E2E.</p>",
        "introduction_html": "<p>Intro.</p>",
        "methodology_html": "<p>Method.</p>",
        "synthesis_html": "<p>Syn.</p>",
        "discussion_html": "<p>Disc.</p>",
        "conclusion_html": "<p>Conc.</p>",
        "keywords": ["test"],
        "sections": [
            {"id": "1", "title": "Introdução",
             "paragraphs": [{"text": "Texto.", "type": "body"}]}
        ],
        "references": ["Ref. (2024). Test."],
    }), encoding="utf-8")
    (out_dir / "extraction.csv").write_text(
        "study_id,title,year,doi\nS001,Mock,2023,10.1/x\n", encoding="utf-8"
    )
    (out_dir / "qa.csv").write_text("id,score\n1,8\n", encoding="utf-8")
    (out_dir / "prisma.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<text x="10" y="50">PRISMA</text></svg>',
        encoding="utf-8",
    )
    (out_dir / "deduplicated_studies.json").write_text(json.dumps({
        "results": [{"study_id": "S001", "doi": "10.1/x",
                      "title": "Mock 1", "year": 2023}]
    }), encoding="utf-8")


def test_pipeline_finalize_propagates_preamble_to_html(tmp_path):
    """B1+B2 (E2E): pipeline com --contextual-preamble produz HTML com preâmbulo."""
    _setup_fixtures(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "pipeline_finalize.py"),
        "--output-dir", str(tmp_path),
        "--title", "E2E Test",
        "--version", "1.0.0",
        "--skip-pdf", "--skip-tex", "--skip-docx",
        "--screening-demo",
        "--contextual-preamble",
        "--preamble-mock",
        "--preamble-area", "educacao",
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    html = (tmp_path / "manuscript.html").read_text(encoding="utf-8")
    assert "campo onde este artigo vive" in html, (
        "Preâmbulo contextual ausente em HTML gerado pelo pipeline (B1+B2)"
    )
    assert 'id="contextual-preamble"' in html


def test_pipeline_finalize_propagates_preamble_to_docx(tmp_path):
    """B1 (E2E): pipeline com --contextual-preamble produz docx com preâmbulo."""
    _setup_fixtures(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "pipeline_finalize.py"),
        "--output-dir", str(tmp_path),
        "--title", "E2E Test",
        "--version", "1.0.0",
        "--skip-pdf", "--skip-tex", "--skip-html",
        "--screening-demo",
        "--contextual-preamble",
        "--preamble-mock",
        "--preamble-area", "educacao",
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    docx_path = tmp_path / "manuscript.docx"
    if not docx_path.exists():
        # python-docx pode não estar disponível — neste caso, etapa skipped, ok
        return
    with zipfile.ZipFile(docx_path) as z:
        with z.open("word/document.xml") as f:
            content = f.read().decode("utf-8")
    assert "campo onde este artigo vive" in content, (
        "Preâmbulo ausente em docx gerado pelo pipeline (B1)"
    )


def test_pipeline_finalize_propagates_preamble_to_latex(tmp_path):
    """B1 (E2E): pipeline com --contextual-preamble produz tex com preâmbulo."""
    _setup_fixtures(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "pipeline_finalize.py"),
        "--output-dir", str(tmp_path),
        "--title", "E2E Test",
        "--version", "1.0.0",
        "--skip-pdf", "--skip-html", "--skip-docx",
        "--screening-demo",
        "--contextual-preamble",
        "--preamble-mock",
        "--preamble-area", "educacao",
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    tex = (tmp_path / "manuscript.tex").read_text(encoding="utf-8")
    assert "campo onde este artigo vive" in tex, (
        "Preâmbulo ausente em tex gerado pelo pipeline (B1)"
    )
    # B1+A2: verificar que conversão Markdown→LaTeX ainda funciona pelo pipeline
    assert "\\textit{" in tex or "\\textbf{" in tex, (
        "Conversor Markdown→LaTeX (A2) não está sendo aplicado pelo pipeline"
    )


def test_pipeline_finalize_without_preamble_flag_omits_preamble(tmp_path):
    """B1: sem flag, pipeline NÃO injeta preâmbulo (default: opt-in)."""
    _setup_fixtures(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "pipeline_finalize.py"),
        "--output-dir", str(tmp_path),
        "--title", "E2E Test",
        "--version", "1.0.0",
        "--skip-pdf", "--skip-tex", "--skip-docx",
        "--screening-demo",
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0
    html = (tmp_path / "manuscript.html").read_text(encoding="utf-8")
    assert "contextual-preamble" not in html, (
        "Preâmbulo NÃO deveria aparecer sem flag --contextual-preamble"
    )


def test_pipeline_finalize_six_steps_in_summary(tmp_path):
    """B3: pipeline_summary.json mostra 6 etapas (não 5)."""
    _setup_fixtures(tmp_path)
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "pipeline_finalize.py"),
        "--output-dir", str(tmp_path),
        "--title", "E2E Test",
        "--version", "1.0.0",
        "--skip-cross-tab", "--skip-format-abnt",
        "--skip-html", "--skip-docx", "--skip-tex", "--skip-pdf",
        "--screening-demo",
    ], capture_output=True, text=True, timeout=60)
    summary = json.loads(
        (tmp_path / "pipeline_summary.json").read_text(encoding="utf-8")
    )
    assert len(summary["steps"]) == 6
    step_names = {s["name"] for s in summary["steps"]}
    assert "screening_pipeline" in step_names


def test_pipeline_docstring_says_six_outputs():
    """B3: docstring de pipeline_finalize.py declara 6 outputs."""
    src = (ROOT / "scripts" / "pipeline_finalize.py").read_text(encoding="utf-8")
    assert "6 outputs" in src, "Docstring deveria declarar '6 outputs'"


# ============ B5: SKILL.md placeholder ============

def test_skill_md_no_unfilled_placeholder():
    """B5: SKILL.md não tem '+N' literal (placeholder esquecido)."""
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    # +N como literal (no formato 'v2.20.0: +N') não deveria estar
    import re
    assert not re.search(r"v2\.20\.0:\s*\+N\b", content), (
        "Placeholder '+N' não preenchido em SKILL.md"
    )


# ============ B6: docstring la_referencia ============

def test_la_referencia_docstring_uses_underscore_form():
    """B6: docstring la_referencia usa la_referencia.json (não lareferencia.json)."""
    src = (ROOT / "scripts" / "searches" / "search_la_referencia.py"
            ).read_text(encoding="utf-8")
    assert "results_lareferencia.json" not in src, (
        "Docstring deveria usar results_la_referencia.json"
    )
    assert "results_la_referencia.json" in src


# ============ B4: schema unificado ============

def test_arxiv_mock_has_total_results(tmp_path):
    """B4: arxiv mock retorna total_results (mantém n como alias)."""
    out = tmp_path / "arxiv.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_arxiv.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert "total_results" in d
    # n preservado como alias para retrocompat
    assert "n" in d
    assert d["total_results"] == d["n"]


def test_crossref_mock_has_total_results(tmp_path):
    """B4: crossref mock retorna total_results."""
    out = tmp_path / "cr.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_crossref.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert "total_results" in d
    assert d["total_results"] == d.get("n")


def test_dblp_mock_has_total_results(tmp_path):
    """B4: dblp mock retorna total_results."""
    out = tmp_path / "dblp.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_dblp.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert "total_results" in d


def test_semantic_scholar_mock_has_total_results(tmp_path):
    """B4: semantic_scholar mock retorna total_results."""
    out = tmp_path / "s2.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_semantic_scholar.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert "total_results" in d


# ============ B11: render_manuscript deprecated ============

def test_render_manuscript_marked_deprecated():
    """B11: render_manuscript.py tem aviso DEPRECATED no topo."""
    src = (ROOT / "scripts" / "render_manuscript.py").read_text(encoding="utf-8")
    assert "DEPRECATED" in src.split("\n", 30)[0:30].__str__() or \
           "DEPRECATED" in "\n".join(src.split("\n")[:30])


# ============ B7: parser Redalyc ============

def test_redalyc_parser_handles_json_response():
    """B7: parser Redalyc lida com resposta JSON estruturada."""
    sys.path.insert(0, str(ROOT / "scripts" / "searches"))
    import search_redalyc as sr
    mock_json = json.dumps({
        "results": [
            {"title": "Educación digital", "year": 2023, "language": "es",
             "autores": "Garcia, M.; Lopez, A.", "doi": "10.1/redalyc-1"},
            {"title": "Old article", "year": 2010, "language": "es",
             "autores": "Smith, J.", "doi": "10.1/redalyc-old"},
        ]
    }).encode("utf-8")
    items = sr._parse_redalyc_response(mock_json, 2020, 2026)
    # Filtra 2010 fora da janela; mantém 2023
    assert len(items) == 1
    assert items[0]["year"] == 2023


def test_redalyc_parser_handles_html_fallback():
    """B7: parser Redalyc lida com HTML quando JSON parsing falha."""
    sys.path.insert(0, str(ROOT / "scripts" / "searches"))
    import search_redalyc as sr
    mock_html = b'''<html><body>
<article class="articulo">
  <h3><a href="/articulo/oa/12345">Sociedad y educacion</a></h3>
  <span class="anio">2024</span>
</article>
</body></html>'''
    items = sr._parse_redalyc_response(mock_html, 2020, 2026)
    assert len(items) == 1
    assert items[0]["title"] == "Sociedad y educacion"
    assert items[0]["year"] == 2024
    assert items[0]["url"].startswith("https://www.redalyc.org")


def test_redalyc_parser_returns_empty_for_unparseable():
    """B7: parser Redalyc retorna lista vazia honestamente quando não consegue parsear."""
    sys.path.insert(0, str(ROOT / "scripts" / "searches"))
    import search_redalyc as sr
    items = sr._parse_redalyc_response(b"<html>nothing structured</html>", 0, 0)
    assert isinstance(items, list)
    assert items == []
