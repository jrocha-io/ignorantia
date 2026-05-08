"""Fix 16 — render_v2.py ↔ manuscript-template.html placeholder sync (RS-42).

The RS-42 dogfood diagnosed that the manuscript template declared ~89
``{{PLACEHOLDER}}`` slots, while the substitutions dict in
``render_v2.main`` provided only ~50 — the remaining ~50 literals leaked
into the rendered HTML, polluting the output silently.

Fix 16 introduces:

1. ``_build_i18n_labels(lang)`` — supplies every label-only placeholder
   (tab labels, section headings, table captions) for pt-BR / en-US.
2. Direct-rename aliases (LANG_TAG ← LANG, RESULTS_HTML ← RESULTS_DESCRIPTIVE_HTML,
   NOT_THIS_VERSION_ITEMS ← NOT_THIS_VERSION_ITEMS_HTML, HASH ← HASH_LINE,
   SKILL_TAG ← SKILL_VERSION).
3. ``STATUS_BANNER_HTML`` composed from ``PHASE_BANNER_HTML`` + ``ZONE_BANNER_HTML``.
4. Audit-panel sub-keys defaulted from existing bundles
   (AUDIT_FINAL_GRADE_HTML ← AUDIT_HTML, etc.).
5. Per-section TLDR slots (TLDR_00..TLDR_08) split from the flat ``tldrs`` list.
6. ``_validate_no_unresolved_placeholders`` — turns the silent failure into
   either a stderr warning (default) or a hard failure (``--strict``).

These tests pin the helpers' contracts and exercise the end-to-end render
to verify no `{{...}}` literal survives substitution.
"""

from __future__ import annotations

import json
import re
import sys
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}")
TEMPLATE = REPO / "assets" / "templates" / "manuscript-template.html"


# ── helpers contract ────────────────────────────────────────────────────


def test_build_i18n_labels_ptbr_supplies_all_section_headings():
    from render_v2 import _build_i18n_labels
    labels = _build_i18n_labels("pt-BR")
    for i in range(11):
        assert f"SEC{i:02d}_HEADING" in labels, f"missing SEC{i:02d}_HEADING in pt-BR labels"
    assert labels["TAB_MANUSCRIPT"] == "Manuscrito"
    assert labels["AUDIT_HEADING"] == "Auditoria"


def test_build_i18n_labels_en_falls_back_for_unknown_lang():
    from render_v2 import _build_i18n_labels
    labels = _build_i18n_labels("en-US")
    assert labels["TAB_MANUSCRIPT"] == "Manuscript"
    # Unknown language uses English defaults (not ptBR).
    fr_labels = _build_i18n_labels("fr-FR")
    assert fr_labels["TAB_MANUSCRIPT"] == "Manuscript"


def test_split_tldrs_per_section_pads_missing_slots_with_empty():
    from render_v2 import _split_tldrs_per_section
    out = _split_tldrs_per_section(["A", "B"], n=9)
    assert out["TLDR_00"] == "A"
    assert out["TLDR_01"] == "B"
    for i in range(2, 9):
        assert out[f"TLDR_{i:02d}"] == "", f"TLDR_{i:02d} should be empty when input runs out"


def test_split_tldrs_per_section_accepts_dict_entries():
    from render_v2 import _split_tldrs_per_section
    out = _split_tldrs_per_section([
        {"html": "<p>One</p>"},
        {"text": "Two"},
        "Three",
    ], n=9)
    assert out["TLDR_00"] == "<p>One</p>"
    assert out["TLDR_01"] == "Two"
    assert out["TLDR_02"] == "Three"


def test_validate_no_unresolved_placeholders_warns_and_returns_list(capsys):
    from render_v2 import _validate_no_unresolved_placeholders
    out = _validate_no_unresolved_placeholders("hello {{FOO}} world {{BAR}}")
    assert out == ["BAR", "FOO"]
    captured = capsys.readouterr()
    assert "FOO" in captured.err and "BAR" in captured.err


def test_validate_no_unresolved_placeholders_strict_raises():
    from render_v2 import _validate_no_unresolved_placeholders
    with pytest.raises(RuntimeError) as exc:
        _validate_no_unresolved_placeholders("oops {{MISSING}}", strict=True)
    assert "MISSING" in str(exc.value)


def test_validate_no_unresolved_placeholders_clean_input_returns_empty():
    from render_v2 import _validate_no_unresolved_placeholders
    assert _validate_no_unresolved_placeholders("nothing here") == []


# ── end-to-end render ───────────────────────────────────────────────────


def _minimal_fixture(tmp: Path) -> dict:
    """Build the minimal set of CLI inputs render_v2.main expects."""
    content_path = tmp / "content.json"
    content_path.write_text(json.dumps({
        "title": "Fix 16 sync test",
        "subtitle": "",
        "lang": "pt-BR",
        "abstract_html": "<p>Resumo de teste.</p>",
        "introduction_html": "<p>Intro.</p>",
        "background_html": "<p>BG.</p>",
        "methodology_html": "<p>Métodos.</p>",
        "results_descriptive_html": "<p>Resultados.</p>",
        "synthesis_html": "<p>Síntese.</p>",
        "discussion_html": "<p>Discussão.</p>",
        "threats_html": "<p>Ameaças.</p>",
        "conclusion_html": "<p>Conclusão.</p>",
        "references": [{"citation": "FERREIRA, A. Título. 2024.", "doi": "10.1590/abc-123"}],
        "venues": [],
        "rqs": [],
        "not_this_version_items": [],
    }), encoding="utf-8")

    extraction = tmp / "extraction.csv"
    extraction.write_text("id,year,author,title,venue,qa\nE1,2024,X,Título,V,8\n", encoding="utf-8")

    qa = tmp / "qa.csv"
    qa.write_text("id,score\nE1,8\n", encoding="utf-8")

    prisma = tmp / "prisma.svg"
    prisma.write_text("<svg></svg>", encoding="utf-8")

    return {"content": content_path, "extraction": extraction, "qa": qa, "prisma": prisma}


def test_end_to_end_render_resolves_every_placeholder(tmp_path):
    """Render with a minimal fixture and assert no `{{...}}` literal remains."""
    f = _minimal_fixture(tmp_path)
    out = tmp_path / "manuscript.html"
    cmd = [
        sys.executable, str(REPO / "scripts" / "render_v2.py"),
        "--content", str(f["content"]),
        "--extraction", str(f["extraction"]),
        "--qa", str(f["qa"]),
        "--prisma", str(f["prisma"]),
        "--version", "0.1.0",
        "--topic-slug", "fix16-test",
        "--out", str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"render_v2 failed: {result.stderr}"
    assert out.exists()

    rendered = out.read_text(encoding="utf-8")
    leftovers = sorted(set(PLACEHOLDER_RE.findall(rendered)))
    assert not leftovers, (
        f"Unresolved template placeholders survived substitution: {leftovers}"
    )


def test_end_to_end_render_strict_mode_errors_when_template_extended(tmp_path, monkeypatch):
    """Inject an extra unknown placeholder into the template copy and verify
    that --strict causes render_v2 to exit non-zero with the placeholder name
    in the error stream.
    """
    template_text = TEMPLATE.read_text(encoding="utf-8")
    rigged_template = tmp_path / "rigged-template.html"
    # Inject a placeholder render_v2 will never resolve.
    rigged_template.write_text(
        template_text.replace("</body>", "<!-- {{UNKNOWN_FIX16_TOKEN}} --></body>"),
        encoding="utf-8",
    )

    f = _minimal_fixture(tmp_path)
    out = tmp_path / "manuscript.html"
    cmd = [
        sys.executable, str(REPO / "scripts" / "render_v2.py"),
        "--content", str(f["content"]),
        "--extraction", str(f["extraction"]),
        "--qa", str(f["qa"]),
        "--prisma", str(f["prisma"]),
        "--template", str(rigged_template),
        "--version", "0.1.0",
        "--topic-slug", "fix16-strict",
        "--out", str(out),
        "--strict",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode != 0, "expected non-zero exit under --strict"
    assert "UNKNOWN_FIX16_TOKEN" in result.stderr
