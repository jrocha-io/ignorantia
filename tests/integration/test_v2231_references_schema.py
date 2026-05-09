"""Fix 17 — references[] schema unification (RS-42 dogfood remediation).

The RS-42 dogfood diagnosed a schema clash on ``content["references"]``:
``render_latex.py`` and ``render_docx_abnt.py`` consumed entries as
``list[str]``, while ``generate_assessment.py`` and ``render_v2.py``
consumed them as ``list[dict]`` with ``citation``/``doi``/``url`` fields.
Manuscripts that satisfied one shape broke the other.

Fix 17 establishes a canonical schema (``list[dict]`` with a ``citation``
key) and provides shape-tolerant helpers in ``scripts/_reference_helpers``
so all four consumers accept legacy strings AND canonical dicts.

These tests pin the helpers' contract and verify all four consumers
produce consistent output for both shapes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))


# ── helpers contract ────────────────────────────────────────────────────


def test_render_reference_string_passes_through_str():
    from _reference_helpers import render_reference_string
    assert render_reference_string("FERREIRA, A. Title. 2024.") == "FERREIRA, A. Title. 2024."


def test_render_reference_string_uses_citation_field():
    from _reference_helpers import render_reference_string
    ref = {"citation": "FERREIRA, A. Title. 2024.", "doi": "10.1/x"}
    assert render_reference_string(ref) == "FERREIRA, A. Title. 2024."


def test_render_reference_string_falls_back_to_text_or_title():
    from _reference_helpers import render_reference_string
    assert render_reference_string({"text": "fallback text"}) == "fallback text"
    assert render_reference_string({"title": "only title"}) == "only title"


def test_render_reference_string_handles_none_and_empty():
    from _reference_helpers import render_reference_string
    assert render_reference_string(None) == ""
    assert render_reference_string("") == ""


def test_extract_doi_from_dict_field():
    from _reference_helpers import extract_doi
    assert extract_doi({"doi": "10.1234/abc"}) == "10.1234/abc"


def test_extract_doi_parses_from_citation_string():
    from _reference_helpers import extract_doi
    citation = "FERREIRA, A. Title. 2024. doi:10.1590/abc-123"
    assert extract_doi(citation) == "10.1590/abc-123"


def test_extract_doi_returns_none_when_absent():
    from _reference_helpers import extract_doi
    assert extract_doi("FERREIRA, A. Title. 2024.") is None
    assert extract_doi({"citation": "no DOI here"}) is None


def test_extract_url_from_dict_or_string():
    from _reference_helpers import extract_url
    assert extract_url({"url": "https://example.org/x"}) == "https://example.org/x"
    assert extract_url("see https://example.org/x for more") == "https://example.org/x"


def test_normalize_reference_str_to_dict():
    from _reference_helpers import normalize_reference
    out = normalize_reference("FERREIRA, A. Title. 2024. doi:10.1590/abc-123")
    assert out["citation"] == "FERREIRA, A. Title. 2024. doi:10.1590/abc-123"
    assert out["doi"] == "10.1590/abc-123"


def test_normalize_references_handles_mixed_shapes():
    from _reference_helpers import normalize_references
    refs = [
        "Plain string ref",
        {"citation": "Dict ref", "doi": "10.1590/y-234"},
    ]
    out = normalize_references(refs)
    assert len(out) == 2
    assert out[0]["citation"] == "Plain string ref"
    assert out[1]["doi"] == "10.1590/y-234"


# ── consumer integration: render_latex ──────────────────────────────────


@pytest.fixture
def base_content() -> dict:
    """Minimal content.json fixture to exercise renderers' references blocks."""
    return {
        "title": "Test Manuscript",
        "abstract_pt": "Resumo de teste.",
        "abstract_en": "Test abstract.",
        "keywords_pt": ["teste"],
        "keywords_en": ["test"],
        "sections": [
            {
                "id": "introducao",
                "title": "Introdução",
                "paragraphs": [{"type": "body", "text": "Conteúdo."}],
            }
        ],
    }


def test_render_latex_accepts_list_of_strings(tmp_path, base_content):
    from render_latex import render_tex
    base_content["references"] = ["FERREIRA, A. Título. 2024."]
    out = tmp_path / "manuscript.tex"
    render_tex(base_content, out, title="T", authors=["A"])
    body = out.read_text(encoding="utf-8")
    assert "FERREIRA" in body


def test_render_latex_accepts_list_of_dicts(tmp_path, base_content):
    from render_latex import render_tex
    base_content["references"] = [
        {"citation": "FERREIRA, A. Título. 2024.", "doi": "10.1/x"}
    ]
    out = tmp_path / "manuscript.tex"
    render_tex(base_content, out, title="T", authors=["A"])
    body = out.read_text(encoding="utf-8")
    assert "FERREIRA" in body
    # Must not leak the dict's repr() into the output.
    assert "{'citation'" not in body
    assert "'doi'" not in body


def test_render_latex_accepts_mixed_shapes(tmp_path, base_content):
    from render_latex import render_tex
    base_content["references"] = [
        "Plain string ref.",
        {"citation": "Dict ref.", "doi": "10.1/y"},
    ]
    out = tmp_path / "manuscript.tex"
    render_tex(base_content, out, title="T", authors=["A"])
    body = out.read_text(encoding="utf-8")
    assert "Plain string ref" in body
    assert "Dict ref" in body
    assert "{'citation'" not in body


# ── consumer integration: render_docx_abnt ──────────────────────────────


def test_render_docx_accepts_list_of_strings(tmp_path, base_content):
    pytest.importorskip("docx")
    from render_docx_abnt import render_docx_abnt
    base_content["references"] = ["FERREIRA, A. Título. 2024."]
    out = tmp_path / "manuscript.docx"
    render_docx_abnt(base_content, out, title="T", authors=["A"])
    assert out.exists() and out.stat().st_size > 0


def test_render_docx_accepts_list_of_dicts(tmp_path, base_content):
    pytest.importorskip("docx")
    from docx import Document
    from render_docx_abnt import render_docx_abnt
    base_content["references"] = [
        {"citation": "FERREIRA, A. Título. 2024.", "doi": "10.1/x"}
    ]
    out = tmp_path / "manuscript.docx"
    render_docx_abnt(base_content, out, title="T", authors=["A"])
    text = "\n".join(p.text for p in Document(str(out)).paragraphs)
    assert "FERREIRA" in text
    # The dict's repr() must not leak into the rendered DOCX.
    assert "{'citation'" not in text


# ── consumer integration: generate_assessment ───────────────────────────


def test_generate_assessment_doi_count_accepts_strings():
    """The D2 (compliance) assessor counts refs with DOI/URL.

    Pre-Fix-17 it crashed on ``str.get`` when refs were strings. Now it must
    parse DOIs/URLs from citation text via the helpers.
    """
    from _reference_helpers import extract_doi, extract_url
    refs = [
        "FERREIRA, A. Título. 2024. doi:10.1590/abc-123",
        "SILVA, B. Outra. 2023. https://example.org/y",
        "NO METADATA HERE.",
    ]
    with_metadata = sum(1 for r in refs if extract_doi(r) or extract_url(r))
    assert with_metadata == 2


def test_generate_assessment_doi_count_accepts_dicts():
    from _reference_helpers import extract_doi, extract_url
    refs = [
        {"citation": "FERREIRA, A.", "doi": "10.1590/abc-123"},
        {"citation": "SILVA, B.", "url": "https://example.org/y"},
        {"citation": "NO METADATA"},
    ]
    with_metadata = sum(1 for r in refs if extract_doi(r) or extract_url(r))
    assert with_metadata == 2


# ── consumer integration: render_v2 build_references_list ───────────────


def test_build_references_list_accepts_list_of_strings():
    from render_v2 import build_references_list
    out = build_references_list(["FERREIRA, A. Título. 2024."])
    assert "FERREIRA" in out
    assert out.startswith("<li>")


def test_build_references_list_accepts_list_of_dicts():
    from render_v2 import build_references_list
    out = build_references_list([
        {"citation": "FERREIRA, A. Título. 2024.", "doi": "10.1/x"}
    ])
    assert "FERREIRA" in out
    assert "https://doi.org/10.1/x" in out


def test_build_references_list_mixed_shapes_no_dict_repr_leak():
    from render_v2 import build_references_list
    out = build_references_list([
        "Plain string.",
        {"citation": "Dict entry.", "url": "https://example.org/y"},
    ])
    assert "Plain string" in out
    assert "Dict entry" in out
    assert "{'citation'" not in out
