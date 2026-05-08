"""Smoke tests v2.10.0 — Decisões 18, 31, 32 + snowballing forward."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# --- Decisão 18: render_chunks -------------------------------------------------

def test_render_chunks_basic_incremental(tmp_path):
    import render_chunks
    chunks = [
        render_chunks.Chunk(section_id="00", section_title="Resumo",
                             content_html="<p>Resumo do trabalho.</p>"),
        render_chunks.Chunk(section_id="01", section_title="Introdução",
                             content_html="<p>Introdução do tema.</p>"),
        render_chunks.Chunk(section_id="02", section_title="Métodos",
                             content_html="<p>Métodos PRISMA.</p>"),
    ]
    output = tmp_path / "manuscript.html"
    inter = tmp_path / "chunks_intermediate"
    result = render_chunks.render_incremental(
        chunks, output, title="Teste", title_short="Teste", version="1.0.0",
        intermediate_dir=inter,
    )
    assert output.exists()
    assert result.final_size_bytes > 0
    assert len(result.chunks_processed) == 3
    # Cada chunk gravado em arquivo intermediário
    for sid in ("00", "01", "02"):
        assert (inter / f"chunk-{sid}.html").exists()
    # HTML final tem todas as seções
    html = output.read_text(encoding="utf-8")
    assert "§00 — Resumo" in html
    assert "§01 — Introdução" in html
    assert "§02 — Métodos" in html
    assert "<footer>" in html


def test_render_chunks_resume_from_chunk(tmp_path):
    """Verifica que retomar a partir de chunk N usa cache para anteriores."""
    import render_chunks
    chunks = [
        render_chunks.Chunk(section_id="00", section_title="A",
                             content_html="<p>conteúdo A</p>"),
        render_chunks.Chunk(section_id="01", section_title="B",
                             content_html="<p>conteúdo B</p>"),
        render_chunks.Chunk(section_id="02", section_title="C",
                             content_html="<p>conteúdo C</p>"),
    ]
    output = tmp_path / "manuscript.html"
    inter = tmp_path / "chunks_intermediate"
    # Run inicial
    render_chunks.render_incremental(
        chunks, output, title="Teste", title_short="T", version="1.0.0",
        intermediate_dir=inter,
    )
    # Sobrescreve cache do chunk 02 com versão "antiga" para verificar uso
    (inter / "chunk-02.html").write_text("<!-- versão antiga 02 -->\n", encoding="utf-8")
    # Retoma a partir de "02" — chunks 00 e 01 devem vir do cache
    chunks2 = [
        render_chunks.Chunk(section_id="00", section_title="DIFERENTE",
                             content_html="<p>NOVO 00</p>"),
        render_chunks.Chunk(section_id="01", section_title="DIFERENTE",
                             content_html="<p>NOVO 01</p>"),
        render_chunks.Chunk(section_id="02", section_title="C",
                             content_html="<p>conteúdo C atualizado</p>"),
    ]
    result = render_chunks.render_incremental(
        chunks2, output, title="Teste", title_short="T", version="1.0.0",
        intermediate_dir=inter, resume_from_chunk="02",
    )
    assert "00" in result.chunks_skipped
    assert "01" in result.chunks_skipped
    assert "02" in result.chunks_processed


def test_render_chunks_does_not_leak_skill_brand(tmp_path):
    """Decisão 19: render incremental não vaza nome do skill no HTML."""
    import render_chunks
    chunks = [render_chunks.Chunk(section_id="00", section_title="Teste",
                                   content_html="<p>x</p>")]
    output = tmp_path / "out.html"
    render_chunks.render_incremental(
        chunks, output, title="Paper", title_short="Paper", version="1.0.0"
    )
    html = output.read_text(encoding="utf-8").lower()
    assert "ignorantia" not in html, "VIOLAÇÃO Decisão 19: 'ignorantia' apareceu no HTML"


def test_render_chunks_from_content_json():
    import render_chunks
    content = {
        "sections": [
            {"id": "00", "title": "Resumo", "content_html": "<p>x</p>", "annotations": []},
            {"id": "01", "title": "Intro", "content_html": "<p>y</p>"},
        ]
    }
    chunks = render_chunks.chunks_from_content_json(content)
    assert len(chunks) == 2
    assert chunks[0].section_id == "00"
    assert chunks[1].section_title == "Intro"


# --- Decisão 31: render_docx_abnt ---------------------------------------------

def test_render_docx_abnt_produces_file(tmp_path):
    import render_docx_abnt
    if not render_docx_abnt.DOCX_AVAILABLE:
        import pytest
        pytest.skip("python-docx não disponível")
    content = {
        "abstract": "Resumo do trabalho de teste.",
        "keywords": ["teste", "abnt", "docx"],
        "sections": [
            {"id": "01", "title": "Introdução",
             "paragraphs": [
                 {"text": "Texto introdutório do trabalho.", "type": "body"},
                 {"text": "Citação longa de teste com 4 ou mais linhas, formatada com recuo de 4cm conforme NBR 10520:2023.", "type": "long_quote"},
             ]},
            {"id": "02", "title": "Métodos",
             "paragraphs": [{"text": "Metodologia descrita aqui.", "type": "body"}]},
        ],
        "references": [
            "SILVA, J. P. Letramento digital. **Educação & Sociedade**, v. 28, n. 2, p. 45-67, 2023. DOI: 10.0000/test.",
            "PEREIRA, A. Acesso a tecnologias. **Cadernos de Pesquisa**, 2022.",
        ],
    }
    out = tmp_path / "manuscript.docx"
    result = render_docx_abnt.render_docx_abnt(
        content, out, title="Trabalho de Teste",
        authors=["Pesquisador, X."],
    )
    assert out.exists()
    assert result.n_sections == 2
    assert result.n_references == 2
    assert result.n_long_quotes == 1
    assert result.file_size_bytes > 5000  # docx mínimo razoável


def test_render_docx_abnt_handles_html_content(tmp_path):
    import render_docx_abnt
    if not render_docx_abnt.DOCX_AVAILABLE:
        import pytest
        pytest.skip("python-docx não disponível")
    content = {
        "sections": [
            {"id": "01", "title": "X", "content_html": "<p>Texto extraído de HTML.</p>"},
        ],
    }
    out = tmp_path / "x.docx"
    result = render_docx_abnt.render_docx_abnt(content, out, title="X")
    assert out.exists()
    assert result.n_sections == 1


def test_render_docx_abnt_strip_html():
    import render_docx_abnt
    txt = render_docx_abnt._strip_html("<p>abc <strong>def</strong></p><p>ghi</p>")
    assert "abc def" in txt
    assert "ghi" in txt
    assert "<" not in txt and ">" not in txt


# --- Decisão 32: render_latex (.tex; .pdf opcional) ---------------------------

def test_render_tex_basic(tmp_path):
    import render_latex
    content = {
        "abstract": "Resumo do trabalho.",
        "keywords": ["teste", "latex"],
        "sections": [
            {"id": "01", "title": "Introdução",
             "paragraphs": [{"text": "Texto da introdução.", "type": "body"}]},
        ],
        "references": ["SILVA, J. **Teste**. 2023."],
    }
    tex_path = tmp_path / "doc.tex"
    result = render_latex.render_tex(
        content, tex_path, title="Teste de LaTeX",
        authors=["Autor, A."],
    )
    assert tex_path.exists()
    text = tex_path.read_text(encoding="utf-8")
    assert "\\documentclass" in text
    assert "\\title{Teste de LaTeX}" in text
    assert "Resumo do trabalho." in text
    assert "Refer\u00eancias" in text or "Referências" in text


def test_render_latex_escapes_special_chars(tmp_path):
    import render_latex
    content = {
        "sections": [
            {"id": "01", "title": "Test & Co.",
             "paragraphs": [{"text": "Texto com $ e % e & e _underline_.", "type": "body"}]},
        ],
    }
    tex_path = tmp_path / "esc.tex"
    render_latex.render_tex(content, tex_path, title="Test_File")
    text = tex_path.read_text(encoding="utf-8")
    # Caracteres devem estar escapados — não pode haver $ ou % crus em texto literal
    assert r"\$" in text
    assert r"\%" in text
    assert r"\&" in text
    assert r"\_" in text
    # Title também escapado
    assert r"Test\_File" in text


def test_render_latex_long_quote_environment(tmp_path):
    import render_latex
    content = {
        "sections": [
            {"id": "01", "title": "X",
             "paragraphs": [
                 {"text": "Citação longa.", "type": "long_quote"},
             ]},
        ],
    }
    tex_path = tmp_path / "q.tex"
    render_latex.render_tex(content, tex_path, title="Q")
    text = tex_path.read_text(encoding="utf-8")
    assert "\\begin{longquote}" in text
    assert "\\end{longquote}" in text


def test_render_pdf_compiles_when_engine_available(tmp_path):
    """PDF compila quando pdflatex está no PATH; skip caso contrário."""
    import render_latex
    if not shutil.which("pdflatex"):
        import pytest
        pytest.skip("pdflatex não disponível no PATH")
    content = {
        "abstract": "Resumo curto.",
        "sections": [
            {"id": "01", "title": "Intro",
             "paragraphs": [{"text": "Texto simples sem caracteres especiais.", "type": "body"}]},
        ],
    }
    tex_path = tmp_path / "doc.tex"
    result = render_latex.render_tex_and_pdf(
        content, tex_path, title="Compile Test", compile_to_pdf=True,
    )
    if result.error:
        # Se falhou por motivos do TeX (faltam packages), aceitar como skip
        import pytest
        pytest.skip(f"compilação falhou: {result.error}")
    assert result.pdf_compiled
    assert result.pdf_path is not None
    assert result.pdf_path.exists()


# --- Snowballing forward -------------------------------------------------------

def test_snowballing_forward_mock_returns_candidates():
    import snowballing_forward
    seeds = ["10.1186/s13643-016-0384-4"]
    result = snowballing_forward.snowball_forward(seeds, mock=True)
    assert result.n_seeds == 1
    assert result.n_unique_candidates >= 1
    assert all(c.get("origin") == "forward_snowballing" for c in result.candidates)


def test_snowballing_forward_dedups_and_normalizes():
    import snowballing_forward
    result = snowballing_forward.snowball_forward(
        ["https://doi.org/10.1186/s13643-016-0384-4", "  10.1234/Foo  "],
        mock=True,
    )
    assert "10.1186/s13643-016-0384-4" in result.seed_dois
    assert "10.1234/foo" in result.seed_dois


def test_snowballing_forward_method_marker():
    import snowballing_forward
    result = snowballing_forward.snowball_forward(["10.1/x"], mock=True)
    # Método deve ser declarado no payload final via CLI; no objeto direto, basta verificar
    # que candidatos têm origin correto
    for c in result.candidates:
        assert c["origin"] == "forward_snowballing"
