"""Tests v2.23.1 (Fix 13 of RS-42 dogfood remediation) — paper/wiki schema split.

The dogfood RS-42 manuscripts produced PDFs and DOCX with section titles like
"§01 Introdução", "§02 Métodos", "§03 Resultados". The user flagged this as
the most visible symptom of schema confusion: the ``id="01"`` is appropriate
for the HTML wiki-style sidebar (where ``§ 01`` is intentional design), but
LaTeX/DOCX academic papers should use auto-numbered sections ("1 Introdução",
"2 Métodos", "3 Resultados") without the §-prefix.

Fix 13 introduces a ``paper_mode: bool = True`` parameter to both
:func:`render_tex` (in :mod:`scripts.render_latex`) and
:func:`render_docx_abnt` (in :mod:`scripts.render_docx_abnt`):

* ``paper_mode=True`` (default after Fix 13): ignores ``section.id`` and emits
  ``\\section{Title}`` (LaTeX, auto-numbered) or ``"<N> Title"`` (DOCX,
  manual numbering matching ABNT).
* ``paper_mode=False`` (legacy compat): preserves the previous behaviour
  ``\\section*{§<id> Title}`` (LaTeX, un-numbered) or ``"§<id> Title"`` (DOCX),
  appropriate for the HTML wiki-style path that uses the same content.json.

The CLI flag is ``--legacy-wiki-prefix`` (opt-in to the old behaviour).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import render_latex  # noqa: E402  — sys.path injection above


# ---------------------------------------------------------------------------
# render_tex paper_mode behaviour
# ---------------------------------------------------------------------------


def _content_with_ids() -> dict:
    """Return a content dict whose sections carry §-style ids."""
    return {
        "sections": [
            {
                "id": "01",
                "title": "Introdução",
                "paragraphs": [{"text": "Texto da introdução.", "type": "body"}],
            },
            {
                "id": "02",
                "title": "Métodos",
                "paragraphs": [{"text": "Texto dos métodos.", "type": "body"}],
            },
            {
                "id": "03",
                "title": "Resultados",
                "paragraphs": [{"text": "Texto dos resultados.", "type": "body"}],
            },
        ],
        "references": [],
    }


def test_paper_mode_default_emits_numbered_section_without_prefix(tmp_path: Path) -> None:
    """Default paper_mode=True emits ``\\section{Title}`` — no §-id prefix."""
    out = tmp_path / "manuscript.tex"
    render_latex.render_tex(
        _content_with_ids(),
        out,
        title="Test Paper Mode",
    )
    text = out.read_text(encoding="utf-8")
    # Numbered section (auto-numbered by LaTeX from \section{...}).
    assert "\\section{Introdução}" in text
    assert "\\section{Métodos}" in text
    assert "\\section{Resultados}" in text
    # No §-id prefix anywhere in section commands.
    assert "\\section*{\\S01" not in text
    assert "\\section*{\\S02" not in text
    assert "\\section*{\\S03" not in text


def test_paper_mode_explicit_true_matches_default(tmp_path: Path) -> None:
    out = tmp_path / "manuscript.tex"
    render_latex.render_tex(
        _content_with_ids(),
        out,
        title="Explicit Paper Mode",
        paper_mode=True,
    )
    text = out.read_text(encoding="utf-8")
    assert "\\section{Introdução}" in text
    assert "\\section*{\\S" not in text


def test_legacy_wiki_prefix_restores_old_behavior(tmp_path: Path) -> None:
    """paper_mode=False keeps the legacy ``\\section*{§<id> Title}`` shape."""
    out = tmp_path / "manuscript.tex"
    render_latex.render_tex(
        _content_with_ids(),
        out,
        title="Legacy Wiki Mode",
        paper_mode=False,
    )
    text = out.read_text(encoding="utf-8")
    # Legacy un-numbered \section*{} with §-id prefix.
    assert "\\section*{\\S01 Introdução}" in text
    assert "\\section*{\\S02 Métodos}" in text
    assert "\\section*{\\S03 Resultados}" in text
    # No paper-mode \section{} commands when legacy is on.
    assert "\\section{Introdução}" not in text


def test_paper_mode_handles_sections_without_id(tmp_path: Path) -> None:
    """Sections without id render correctly in paper_mode (no leftover space)."""
    content = {
        "sections": [
            {"title": "Conclusão", "paragraphs": [{"text": "Final.", "type": "body"}]},
        ],
        "references": [],
    }
    out = tmp_path / "manuscript.tex"
    render_latex.render_tex(content, out, title="No-id sections")
    text = out.read_text(encoding="utf-8")
    assert "\\section{Conclusão}" in text


def test_legacy_mode_with_no_id_falls_back_to_section_star(tmp_path: Path) -> None:
    """paper_mode=False + section without id emits ``\\section*{Title}`` (no prefix)."""
    content = {
        "sections": [
            {"title": "Conclusão", "paragraphs": [{"text": "Final.", "type": "body"}]},
        ],
        "references": [],
    }
    out = tmp_path / "manuscript.tex"
    render_latex.render_tex(content, out, title="Legacy no-id", paper_mode=False)
    text = out.read_text(encoding="utf-8")
    assert "\\section*{Conclusão}" in text


# ---------------------------------------------------------------------------
# render_docx_abnt paper_mode behaviour
# ---------------------------------------------------------------------------

# python-docx is an optional dep. Skip these tests if not installed.
try:
    import docx as _docx_check  # noqa: F401

    HAS_DOCX = True
except ImportError:  # pragma: no cover
    HAS_DOCX = False


import pytest


@pytest.mark.skipif(not HAS_DOCX, reason="python-docx not installed")
def test_docx_paper_mode_default_uses_numeric_index(tmp_path: Path) -> None:
    """Default paper_mode=True numbers sections as '<N> Title' without §-id."""
    import docx as docx_mod
    import render_docx_abnt

    out = tmp_path / "manuscript.docx"
    render_docx_abnt.render_docx_abnt(
        _content_with_ids(),
        out,
        title="DOCX Paper Mode",
    )
    doc = docx_mod.Document(str(out))
    # Concatenate all paragraph texts into a single string for keyword searches.
    body_text = "\n".join(p.text for p in doc.paragraphs)
    # Numeric headings present.
    assert "1 Introdução" in body_text
    assert "2 Métodos" in body_text
    assert "3 Resultados" in body_text
    # No §-id prefix.
    assert "§01" not in body_text
    assert "§02" not in body_text
    assert "§03" not in body_text


@pytest.mark.skipif(not HAS_DOCX, reason="python-docx not installed")
def test_docx_legacy_wiki_prefix_restores_old_behaviour(tmp_path: Path) -> None:
    """paper_mode=False keeps the legacy '§<id> Title' headings."""
    import docx as docx_mod
    import render_docx_abnt

    out = tmp_path / "manuscript.docx"
    render_docx_abnt.render_docx_abnt(
        _content_with_ids(),
        out,
        title="DOCX Legacy",
        paper_mode=False,
    )
    doc = docx_mod.Document(str(out))
    body_text = "\n".join(p.text for p in doc.paragraphs)
    assert "§01 Introdução" in body_text
    assert "§02 Métodos" in body_text
    assert "§03 Resultados" in body_text


# ---------------------------------------------------------------------------
# Regression: RS-42 manuscript style (the user's actual complaint)
# ---------------------------------------------------------------------------


def test_rs42_style_content_json_no_longer_emits_section_paragraph_prefix(
    tmp_path: Path,
) -> None:
    """A content.json shaped like the RS-42 v1.0.0 manuscript renders cleanly.

    The user complained that PDFs had "§1 Introdução", "§2 Métodos" literal
    in the section titles. With Fix 13 default behaviour, that exact symptom
    is gone.
    """
    content = {
        "title": "Validity of AI-Assisted Reviews",
        "sections": [
            {
                "id": "01",
                "title": "Introdução",
                "paragraphs": [{"text": "Background.", "type": "body"}],
            },
            {
                "id": "02",
                "title": "Métodos",
                "paragraphs": [{"text": "Method description.", "type": "body"}],
            },
        ],
        "references": [],
    }
    out = tmp_path / "manuscript.tex"
    render_latex.render_tex(content, out, title="RS-42 v1.0.1")
    text = out.read_text(encoding="utf-8")
    # The exact symptom the user flagged: §1, §2 literal in PDFs.
    assert "§1 Introdução" not in text
    assert "§2 Métodos" not in text
    assert "\\S01 Introdução" not in text
    assert "\\S02 Métodos" not in text
    # And the corrected output is present.
    assert "\\section{Introdução}" in text
    assert "\\section{Métodos}" in text
