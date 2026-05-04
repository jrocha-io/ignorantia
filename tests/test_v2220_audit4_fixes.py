"""Testes v2.22.0 — auditoria #4 (C1 a C8).

C1+C2: schema unificado dos 4 retrofitted (year_range top-level + item-level)
C3: parsers reais para 4 ibero (clacso, dialnet, pepsic via LILACS, scielo_preprints)
C4: README.md tem contadores quantitativos
C5: render_manuscript emite DeprecationWarning ao importar
C6: adapters sem parser declaram REAL_PARTIAL (não REAL)
C7: referências cross-doc atualizadas
C8: DD-13 documenta renderer canônico
"""
from __future__ import annotations

import json
import sys
import subprocess
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# ============ C1+C2: schema unificado retrofitted ============

def test_arxiv_top_level_has_year_range(tmp_path):
    """C2: arxiv inclui year_range no top-level (paridade com 3 outros)."""
    out = tmp_path / "x.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_arxiv.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert "year_range" in d


def test_all_retrofitted_have_year_range(tmp_path):
    """C2: 4 retrofitted (arxiv, crossref, dblp, semantic_scholar) têm year_range."""
    for adapter in ["arxiv", "crossref", "dblp", "semantic_scholar"]:
        out = tmp_path / f"{adapter}.json"
        subprocess.run([
            sys.executable, str(ROOT / "scripts" / "searches" / f"search_{adapter}.py"),
            "--query", "test", "--mock", "--output", str(out),
        ], capture_output=True, timeout=10)
        d = json.loads(out.read_text())
        assert "year_range" in d, f"{adapter} sem year_range"


def test_arxiv_items_have_year_field(tmp_path):
    """C1: arxiv items têm 'year' (paridade com paywall/legacy)."""
    out = tmp_path / "x.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_arxiv.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert d["results"]
    for item in d["results"]:
        assert "year" in item


def test_dblp_items_have_doi_field(tmp_path):
    """C1: dblp items têm 'doi' (paridade com paywall/legacy/crossref)."""
    out = tmp_path / "x.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "searches" / "search_dblp.py"),
        "--query", "test", "--mock", "--output", str(out),
    ], capture_output=True, timeout=10)
    d = json.loads(out.read_text())
    assert d["results"]
    for item in d["results"]:
        assert "doi" in item


def test_all_retrofitted_items_have_language_and_is_oa(tmp_path):
    """C1: 4 retrofitted items têm 'language' e 'is_oa' (paridade)."""
    for adapter in ["arxiv", "crossref", "dblp", "semantic_scholar"]:
        out = tmp_path / f"{adapter}.json"
        subprocess.run([
            sys.executable, str(ROOT / "scripts" / "searches" / f"search_{adapter}.py"),
            "--query", "test", "--mock", "--output", str(out),
        ], capture_output=True, timeout=10)
        d = json.loads(out.read_text())
        for item in d["results"]:
            assert "language" in item, f"{adapter} item sem language"
            assert "is_oa" in item, f"{adapter} item sem is_oa"


# ============ C3: parsers reais ibero ============

def test_clacso_parser_extracts_dspace_items():
    """C3: parser CLACSO extrai DSpace artifact-description blocks."""
    import search_clacso as sc
    mock_html = b'''<html><body>
<div class="artifact-description">
  <a class="artifact-title" href="/handle/CLACSO/12345">Tecnologias e exclusao</a>
  <span class="publisher">Martinez, C.</span>
  <span>2022</span>
  <span>spa</span>
</div>
</body></html>'''
    items = sc._parse_clacso_html(mock_html, 2020, 2026)
    assert len(items) == 1
    assert items[0]["title"].startswith("Tecnologias")
    assert items[0]["year"] == 2022
    assert items[0]["language"] == "es"
    assert items[0]["is_oa"] is True


def test_clacso_parser_handles_unparseable_html():
    """C3: CLACSO retorna lista vazia honestamente quando HTML não bate padrão."""
    import search_clacso as sc
    items = sc._parse_clacso_html(b"<html>nothing</html>", 0, 0)
    assert items == []


def test_dialnet_parser_extracts_documento_items():
    """C3: parser Dialnet extrai <li class='documento'> blocks."""
    import search_dialnet as sd
    mock = b'''<html><body>
<li class="documento">
  <a class="titulo" href="/servlet/articulo?codigo=12345">Educacion digital</a>
  <span class="autores">Garcia, M.; Lopez, A.</span>
  <span>2023</span>
</li>
</body></html>'''
    items = sd._parse_dialnet_html(mock, 2020, 2026)
    assert len(items) == 1
    assert items[0]["title"] == "Educacion digital"
    assert items[0]["year"] == 2023
    assert items[0]["url"].startswith("https://dialnet.unirioja.es")


def test_pepsic_reuses_lilacs_parser():
    """C3: PePSIC reusa _parse_bvs_html de LILACS."""
    import search_lilacs as sl
    mock = b'''<html><body>
<div class="reference">
  <h3><a href="/portal/resource/12345">Saude mental</a></h3>
  <span>2024</span>
  <span class="author">Silva, A.</span>
  <span>por</span>
</div>
</body></html>'''
    items = sl._parse_bvs_html(mock, 2020, 2026)
    assert len(items) == 1
    assert items[0]["language"] == "pt"
    assert items[0]["year"] == 2024


def test_scielo_preprints_parser_extracts_ojs_items():
    """C3: parser SciELO Preprints extrai obj_article_summary blocks (OJS)."""
    import search_scielo_preprints as ssp
    mock = b'''<html><body>
<div class="obj_article_summary">
  <h3 class="title"><a href="/index.php/scielo/preprint/123">Pre-print sobre educacao digital</a></h3>
  <div class="meta authors">Santos, J.; Pereira, M.</div>
  <div class="published">2024</div>
</div>
</body></html>'''
    items = ssp._parse_scielo_preprints_html(mock, 2020, 2026)
    assert len(items) == 1
    assert items[0]["title"].startswith("Pre-print")
    assert items[0]["year"] == 2024
    assert items[0]["is_oa"] is True
    assert items[0]["publication_type"] == "preprint"


def test_scielo_preprints_filters_by_year():
    """C3: SciELO Preprints filtra por janela temporal."""
    import search_scielo_preprints as ssp
    mock = b'''<html><body>
<div class="obj_article_summary">
  <h3 class="title"><a href="/p/1">Old article</a></h3>
  <div class="published">2010</div>
</div>
<div class="obj_article_summary">
  <h3 class="title"><a href="/p/2">Recent article</a></h3>
  <div class="published">2023</div>
</div>
</body></html>'''
    items = ssp._parse_scielo_preprints_html(mock, 2020, 2026)
    assert len(items) == 1
    assert items[0]["year"] == 2023


# ============ C4: README contadores ============

def test_readme_has_quantitative_state():
    """C4: README declara estado quantitativo (≥4 contadores)."""
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    counters = ["61 adapters", "57 TIER1", "16 paywall", "6 etapas", "315",
                "33 decisões", "12 DDs", "13 DDs"]
    found = sum(1 for c in counters if c in content)
    assert found >= 4, f"Apenas {found} contadores em README; esperado ≥4"


# ============ C5: DeprecationWarning render_manuscript ============

def test_render_manuscript_emits_deprecation_warning():
    """C5: import render_manuscript emite DeprecationWarning."""
    # Limpar import cache para garantir que warning seja emitido
    if "render_manuscript" in sys.modules:
        del sys.modules["render_manuscript"]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import render_manuscript  # noqa: F401
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1, (
            "render_manuscript deveria emitir DeprecationWarning ao importar"
        )
        msg = str(deprecation_warnings[0].message)
        assert "DEPRECATED" in msg
        assert "render_chunks" in msg or "v3.0.0" in msg


# ============ C6: REAL_PARTIAL honesto ============

def test_bdtd_declares_real_partial_when_no_parser(tmp_path):
    """C6: bdtd retorna method=BDTD_REAL_PARTIAL (não BDTD_REAL) quando results=[].

    Esperado em smoke real OU quando parser falha — testa só o code change.
    """
    src = (ROOT / "scripts" / "searches" / "search_bdtd.py").read_text()
    assert '"BDTD_REAL_PARTIAL"' in src
    assert '"BDTD_REAL"' not in src.replace('"BDTD_REAL_PARTIAL"', '').replace(
        '"BDTD_REAL_ERROR"', ''
    )


def test_scioteca_declares_real_partial_when_no_parser():
    """C6: scioteca retorna method=SCIOTECA_REAL_PARTIAL."""
    src = (ROOT / "scripts" / "searches" / "search_scioteca.py").read_text()
    assert '"SCIOTECA_REAL_PARTIAL"' in src


def test_grey_lit_declares_real_partial_when_no_parser():
    """C6: grey_lit retorna method=GREY_LIT_<X>_REAL_PARTIAL."""
    src = (ROOT / "scripts" / "searches" / "search_grey_lit.py").read_text()
    assert "_REAL_PARTIAL" in src


# ============ C8: DD-13 ============

def test_dd13_documented():
    """C8: DD-13 documentada em DECISIONS.md."""
    content = (ROOT / "references" / "DECISIONS.md").read_text(encoding="utf-8")
    assert "### DD-13" in content
    assert "Renderer HTML canônico" in content or "render_chunks" in content


def test_skill_md_mentions_13_dds():
    """C8: SKILL.md menciona 13 DDs (não mais 12)."""
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "13 decisões de design" in content or "DD-1 a DD-13" in content
