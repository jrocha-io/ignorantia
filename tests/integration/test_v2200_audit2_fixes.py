"""Testes v2.20.0 — auditoria #2 (A1 a A9).

A1: version stamps consistentes
A2: Markdown→LaTeX completo (italic, bold, listas, links)
A3: arxiv aceita --year-start/--year-end
A4: SKILL.md com contadores numéricos
A5: DOIs mock la_referencia padronizados
A6: --mock em 4 adapters legacy
A7: grey_lit imprime erro em stderr
A8: arxiv backoff exponencial em 429
A9: parser HTML real para LILACS
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# ============ A1: version stamps ============

def test_readme_version_is_2_20():
    """A1: README declara versão >= 2.20.0 (não 2.18.1 da v2.19.0)."""
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    # Aceita 2.20.x ou 2.21.x ou superior
    import re
    m = re.search(r"\*\*Versão:\*\*\s*(\d+)\.(\d+)\.(\d+)", content)
    assert m is not None, "Não encontrou linha 'Versão' no README"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor) >= (2, 20), f"Versão {major}.{minor}.{patch} < 2.20"


def test_contextual_preamble_version_is_2_20():
    """A1: contextual_preamble.py declara VERSION >= 2.20.0."""
    from contextual_preamble import VERSION
    parts = VERSION.split(".")
    major, minor = int(parts[0]), int(parts[1])
    assert (major, minor) >= (2, 20), f"VERSION={VERSION} < 2.20"


def test_user_agent_has_correct_version():
    """A1: User-Agent enviado para Wikimedia inclui versão atual da skill."""
    from contextual_preamble import VERSION, _build_user_agent
    ua = _build_user_agent("test@example.org")
    assert f"ignorantia-skill/{VERSION}" in ua


# ============ A2: Markdown→LaTeX completo ============

def test_markdown_to_latex_converts_italic():
    """A2: *texto* → \\textit{texto}."""
    from render_latex import _markdown_to_latex
    out = _markdown_to_latex("Esta é *uma frase italica* aqui.")
    assert "\\textit{uma frase italica}" in out
    assert "*uma frase" not in out


def test_markdown_to_latex_converts_bold():
    """A2: **texto** → \\textbf{texto}."""
    from render_latex import _markdown_to_latex
    out = _markdown_to_latex("Aqui é **negrito** ok.")
    assert "\\textbf{negrito}" in out
    assert "**negrito**" not in out


def test_markdown_to_latex_converts_links():
    """A2: [text](url) → \\href{url}{text} para URLs http/https."""
    from render_latex import _markdown_to_latex
    out = _markdown_to_latex("Veja [Wikipedia](https://pt.wikipedia.org/wiki/Test).")
    assert "\\href{https://pt.wikipedia.org/wiki/Test}{Wikipedia}" in out


def test_markdown_to_latex_preserves_brackets_not_links():
    """A2: [foo] sem URL não é tratado como link (URL deve ser http/https)."""
    from render_latex import _markdown_to_latex
    out = _markdown_to_latex("Item [mock] aqui.")
    # [mock] é texto literal — deve ser preservado (escaped) sem virar \href
    assert "\\href" not in out
    assert "[mock]" in out


def test_markdown_to_latex_handles_bold_and_italic_together():
    """A2: bold tem precedência sobre italic (**bold** parseado primeiro)."""
    from render_latex import _markdown_to_latex
    out = _markdown_to_latex("**bold** e *italic* juntos.")
    assert "\\textbf{bold}" in out
    assert "\\textit{italic}" in out


def test_markdown_to_latex_avoids_escaping_inside_href():
    """A2: dentro de \\href{url}{text}, URL preserva % e _."""
    from render_latex import _markdown_to_latex
    out = _markdown_to_latex(
        "[link](https://example.com/path_with_under%percent)"
    )
    # URL escape só de % e #; _ deve ficar intacto
    assert "https://example.com/path_with_under" in out
    assert "\\%percent" in out


def test_render_latex_preamble_has_no_raw_markdown(tmp_path):
    """A2 E2E: render_latex com --contextual-preamble produz TeX sem Markdown cru."""
    content_path = tmp_path / "content.json"
    content_path.write_text(json.dumps({
        "abstract": "Teste.", "sections": [], "references": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.tex"
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "render_latex.py"),
        "--content-json", str(content_path),
        "--output-tex", str(out_path),
        "--title", "Test",
        "--no-pdf",
        "--contextual-preamble",
        "--preamble-mock",
        "--preamble-area", "educacao",
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    tex = out_path.read_text(encoding="utf-8")
    # Pelo menos uma conversão LaTeX deve estar presente
    assert "\\textit{" in tex or "\\textbf{" in tex
    assert "\\begin{itemize}" in tex
    # Sem **markdown** cru
    assert "**" not in tex
    # Sem itálico Markdown cru no início de linha
    raw_italic_lines = [ln for ln in tex.split("\n")
                          if ln.startswith("*") and not ln.startswith("\\")]
    assert raw_italic_lines == [], f"Markdown italic cru: {raw_italic_lines}"


# ============ A3: arxiv argparse ============

def test_arxiv_accepts_year_start_year_end(tmp_path):
    """A3: search_arxiv.py --year-start/--year-end (compatível com orquestrador)."""
    out = tmp_path / "arxiv.json"
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_arxiv.py"),
        "--query", "test",
        "--year-start", "2023", "--year-end", "2024",
        "--mock", "--output", str(out),
    ], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    data = json.loads(out.read_text())
    assert data["source"] == "arxiv"
    assert data["method"] == "MOCK"


def test_arxiv_still_accepts_legacy_start_date(tmp_path):
    """A3: arxiv mantém retrocompat com --start-date YYYY-MM-DD."""
    out = tmp_path / "arxiv.json"
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_arxiv.py"),
        "--query", "test",
        "--start-date", "2023-01-01", "--end-date", "2024-12-31",
        "--mock", "--output", str(out),
    ], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


# ============ A4: SKILL.md contadores ============

def test_skill_md_has_quantitative_section():
    """A4: SKILL.md tem seção 'Estado quantitativo da skill'."""
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Estado quantitativo" in content


def test_skill_md_mentions_57_runners():
    """A4: SKILL.md menciona '57 TIER1_RUNNERS' explicitamente."""
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "57 TIER1_RUNNERS" in content or "57** TIER1" in content


def test_skill_md_mentions_correct_adapter_count():
    """A4 + DIM 4 (v2.23.0): SKILL.md menciona contagem real de adapters.

    Anteriormente hardcoded em '61 adapters'; v2.23.0 corrigiu para 62.
    Este teste agora valida que a contagem em SKILL.md bate com filesystem.
    """
    import os
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    actual = len([f for f in os.listdir(ROOT / "scripts" / "searches")
                   if f.startswith("search_") and f.endswith(".py")])
    assert f"{actual} adapters" in content, (
        f"SKILL.md não declara {actual} adapters (contagem real)"
    )


def test_skill_md_mentions_6_pipeline_stages():
    """A4: SKILL.md menciona 6 etapas do pipeline_finalize."""
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "6 etapas" in content


# ============ A5: DOIs mock la_referencia ============

def test_la_referencia_mock_dois_use_underscore_form():
    """A5: DOIs mock usam la_referencia (underscore), não lareferencia."""
    content = (ROOT / "scripts" / "searches" / "search_la_referencia.py").read_text()
    assert "10.0000/lareferencia-mock" not in content
    assert "10.0000/la_referencia-mock" in content


# ============ A6: --mock em 4 adapters legacy ============

def test_crossref_supports_mock(tmp_path):
    """A6: search_crossref.py --mock funciona."""
    out = tmp_path / "cr.json"
    r = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_crossref.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text())
    assert d["source"] == "crossref"
    assert d["method"] == "MOCK"


def test_dblp_supports_mock(tmp_path):
    """A6: search_dblp.py --mock funciona."""
    out = tmp_path / "dblp.json"
    r = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_dblp.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text())
    assert d["source"] == "dblp"


def test_semantic_scholar_supports_mock(tmp_path):
    """A6: search_semantic_scholar.py --mock funciona."""
    out = tmp_path / "s2.json"
    r = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_semantic_scholar.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text())
    assert d["source"] == "semantic_scholar"


# ============ A7: grey_lit stderr ============

def test_grey_lit_prints_error_on_stderr_for_failed_provider():
    """A7: grey_lit emite mensagem em stderr antes de return 1.

    Usa um provider real que dá 404 atualmente (ipea).
    Esse teste pode ficar irrelevante se ipea voltar a funcionar — esperado.

    O teste tolera ``TimeoutExpired`` (ipea.gov.br pode estar lento ou
    bloqueando IPs de runners CI): nesse caso o teste é ``skip``ado, já
    que o objetivo é validar o comportamento de stderr quando o provider
    de fato responde com falha — não medir disponibilidade do ipea.
    """
    import tempfile
    out = tempfile.mktemp(suffix=".json")
    try:
        r = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "searches" / "search_grey_lit.py"),
            "--query", "test", "--provider", "ipea",
            "--year-start", "2023", "--year-end", "2024",
            "--output", out,
        ], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        import pytest
        pytest.skip("ipea.gov.br não respondeu em 60s — flake de rede, teste skipado")
    if r.returncode == 1:
        # Provider falhou (esperado para ipea atualmente) — stderr deve conter mensagem
        assert "error" in r.stderr.lower() or "ipea" in r.stderr.lower()


# ============ A9: parser LILACS ============

def test_lilacs_parser_returns_list_for_empty_html():
    """A9: parser LILACS lida graciosamente com HTML não-reconhecido (zero items)."""
    from search_lilacs import _parse_bvs_html
    result = _parse_bvs_html(b"<html><body>nothing here</body></html>", 0, 0)
    assert isinstance(result, list)
    assert result == []


def test_lilacs_parser_extracts_from_reference_blocks():
    """A9: parser LILACS extrai items quando HTML tem padrão reconhecível."""
    from search_lilacs import _parse_bvs_html
    mock_html = '''<html><body>
<div class="reference">
  <h3><a href="/portal/resource/12345">Saúde digital de idosos no Brasil</a></h3>
  <span class="data-meta">2023</span>
  <span class="author">Silva, A.; Souza, B.</span>
  <span>por</span>
</div>
<div class="reference">
  <h3><a href="/portal/resource/67890">Atención primaria digital</a></h3>
  <span class="data-meta">2022</span>
  <span class="author">Gonzalez, M.</span>
  <span>spa</span>
</div>
</body></html>'''.encode()
    result = _parse_bvs_html(mock_html, 2020, 2026)
    assert len(result) == 2
    assert result[0]["title"].startswith("Saúde")
    assert result[0]["year"] == 2023
    assert result[0]["language"] == "pt"
    assert result[1]["language"] == "es"


def test_lilacs_parser_filters_by_year_window():
    """A9: parser LILACS filtra por janela temporal."""
    from search_lilacs import _parse_bvs_html
    mock_html = b'''<html><body>
<div class="reference">
  <h3><a href="/p/1">Paper 1</a></h3>
  <span>2018</span>
  <span class="author">A</span>
</div>
<div class="reference">
  <h3><a href="/p/2">Paper 2</a></h3>
  <span>2024</span>
  <span class="author">B</span>
</div>
</body></html>'''
    result = _parse_bvs_html(mock_html, 2023, 2025)
    assert len(result) == 1
    assert result[0]["year"] == 2024


def test_lilacs_parser_handles_malformed_html():
    """A9: parser LILACS não falha com HTML malformado."""
    from search_lilacs import _parse_bvs_html
    result = _parse_bvs_html(b"<broken><html<<<", 0, 0)
    assert isinstance(result, list)
