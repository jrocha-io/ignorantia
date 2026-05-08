"""Tests v2.23.1 (Fix 10 of RS-42 dogfood remediation) — Decisão 19 vocabulary.

Decisão 19 forbids skill-internal meta-discourse from leaking into the
manuscript voice. The pre-existing test (``test_v28_eliminations.py``)
covers only the literal brand string ``ignorantia``. RS-42 v1.0.0
slipped through that test while still producing a manuscript that read
as engineering documentation, because the leakage was in a *family* of
terms — not the single brand string.

Fix 10 introduces ``scripts/check_decision_19_vocabulary.py`` with a
forbidden-vocabulary regex set covering:

* SemVer rhetoric (``v1.0.0``, ``v1.1.0``)
* Internal procedural references (``Decisão 8 do protocolo``)
* Skill-internal classifications (``Categoria A``, ``Categoria B``)
* Literal JSON / metadata field names (``review_purpose``,
  ``purpose_per_stage``, etc.)
* Skill brand (consolidated from the v2.8.0 test for one-stop checking)

These tests drive both the pure-Python ``find_violations`` API and the
CLI surface (subprocess + exit code), since both are downstream contracts.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_decision_19_vocabulary import (  # noqa: E402  — sys.path injection
    Violation,
    find_violations,
)

CLI = ROOT / "scripts" / "check_decision_19_vocabulary.py"


# ---------------------------------------------------------------------------
# Pure-API: find_violations
# ---------------------------------------------------------------------------


def test_clean_text_returns_no_violations() -> None:
    """A manuscript-style paragraph with no leakage scores zero."""
    text = (
        "This scoping review consolidates the empirical literature on "
        "AI-assisted screening. Future work will replicate the analysis "
        "in a Cochrane-style systematic review with two reviewers."
    )
    assert find_violations(text) == []


def test_semver_version_tag_is_caught() -> None:
    """``v1.0.0`` and ``v1.1.0`` count as SemVer rhetoric."""
    text = "Esta meta-revisão (v1.0.0) será atualizada em v1.1.0 com novo corpus."
    violations = find_violations(text)
    labels = [v.label for v in violations]
    assert labels.count("semver-version-tag") >= 2


def test_decision_number_reference_is_caught() -> None:
    """``Decisão N`` references leak the protocol-as-checklist mode."""
    text = (
        "As mitigações Categoria A (Decisão 8 do protocolo) foram cumpridas; "
        "snowballing está pendente conforme Decisão 23."
    )
    labels = [v.label for v in find_violations(text)]
    assert "decision-number-reference" in labels
    # ``Categoria A`` should also fire.
    assert "category-classification" in labels


def test_metadata_field_names_are_caught() -> None:
    """JSON / metadata field names belong in metadata, not prose."""
    text = (
        "review_purpose=design_validation declarado explicitamente no "
        "metadado do pacote, com purpose_per_stage e human_oversight."
    )
    labels = [v.label for v in find_violations(text)]
    assert labels.count("metadata-field-name") >= 3


def test_skill_brand_is_caught() -> None:
    """The literal ``ignorantia`` is also surfaced by this checker."""
    text = "Esta revisão foi conduzida com a skill ignorantia v2.23.0."
    labels = [v.label for v in find_violations(text)]
    assert "skill-brand" in labels


def test_violation_records_carry_line_numbers() -> None:
    """Each violation reports a 1-based line number useful for triage."""
    text = "Linha 1 limpa.\nLinha 2 com Decisão 8 problemático.\nLinha 3 limpa."
    violations = find_violations(text)
    assert len(violations) == 1
    assert violations[0].line_number == 2


def test_violations_sorted_by_position() -> None:
    """Multiple violations are returned in document order."""
    text = "Decisão 1 aqui.\nv2.0.0 ali.\nCategoria A acolá."
    violations = find_violations(text)
    line_numbers = [v.line_number for v in violations]
    assert line_numbers == sorted(line_numbers)


# ---------------------------------------------------------------------------
# Pure-API: LaTeX preamble exclusion
# ---------------------------------------------------------------------------


def test_latex_preamble_packages_are_not_false_positives() -> None:
    """``\\usepackage[utf8]{inputenc}`` lines must not trip the version regex."""
    text = (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{hyperref}\n"
        "\\begin{document}\n"
        "This is the body. Future work will extend the analysis.\n"
        "\\end{document}\n"
    )
    violations = find_violations(text, is_latex=True)
    assert violations == []


def test_latex_body_violations_still_caught_after_preamble_strip() -> None:
    """Violations *after* ``\\begin{document}`` are still flagged."""
    text = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Esta v1.0.0 cumpre a Decisão 8 do protocolo.\n"
        "\\end{document}\n"
    )
    violations = find_violations(text, is_latex=True)
    labels = {v.label for v in violations}
    assert "semver-version-tag" in labels
    assert "decision-number-reference" in labels


def test_latex_line_numbers_offset_by_preamble() -> None:
    """Line numbers reported are absolute (count includes preamble lines)."""
    text = (
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\begin{document}\n"
        "Decisão 5 está aqui.\n"
        "\\end{document}\n"
    )
    violations = find_violations(text, is_latex=True)
    assert len(violations) == 1
    # The violating line is the 4th line of the file.
    assert violations[0].line_number == 4


# ---------------------------------------------------------------------------
# CLI surface (exit code, stderr, file-not-found)
# ---------------------------------------------------------------------------


def _run_cli(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), str(path), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exit_zero_on_clean_text(tmp_path: Path) -> None:
    f = tmp_path / "manuscript.md"
    f.write_text("This is a clean academic abstract.", encoding="utf-8")
    result = _run_cli(f)
    assert result.returncode == 0


def test_cli_exit_two_on_violations(tmp_path: Path) -> None:
    f = tmp_path / "manuscript.md"
    f.write_text("Esta v1.0.0 valida o método (Decisão 8).", encoding="utf-8")
    result = _run_cli(f)
    assert result.returncode == 2
    assert "FAILED" in result.stderr
    assert "semver-version-tag" in result.stderr or "decision-number-reference" in result.stderr


def test_cli_exit_one_on_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.tex"
    result = _run_cli(missing)
    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_cli_quiet_flag_suppresses_per_violation_lines(tmp_path: Path) -> None:
    f = tmp_path / "manuscript.md"
    f.write_text("Decisão 5 aqui.", encoding="utf-8")
    result = _run_cli(f, "--quiet")
    assert result.returncode == 2
    # Quiet mode should still emit a one-line summary.
    assert "FAILED" in result.stderr
    # But it should NOT enumerate per-violation `why:` lines.
    assert "why:" not in result.stderr


def test_cli_handles_latex_preamble_via_extension(tmp_path: Path) -> None:
    """A clean .tex file with version-bearing \\usepackage lines passes."""
    f = tmp_path / "manuscript.tex"
    f.write_text(
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\begin{document}\n"
        "Clean academic prose. Future work follows.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    result = _run_cli(f)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Regression: RS-42 v1.0.0 transcript phrases must FAIL the gate
# ---------------------------------------------------------------------------


def test_rs42_v1_phrases_are_caught() -> None:
    """Phrases lifted verbatim from the RS-42 v1.0.0 manuscript fail the check.

    These are the specific leakages the user flagged when calling RS-42
    v1.0.0 'péssimo'. If any of these regress past the checker in a
    future change, this test goes red.
    """
    rs42_phrases = [
        "Esta v1.0.0 é uma execução única; v1.1.0 fará re-execução",
        "Decisão 22 do protocolo",
        "Decisão 23 do protocolo",
        "as cinco mitigações Categoria A",
        "Mitigações Categoria B (recomendadas, parcialmente cumpridas)",
        "review_purpose=design_validation declarado explicitamente",
    ]
    for phrase in rs42_phrases:
        violations = find_violations(phrase)
        assert violations, f"Phrase passed unexpectedly: {phrase!r}"


# ---------------------------------------------------------------------------
# Violation dataclass surface
# ---------------------------------------------------------------------------


def test_violation_is_frozen_and_slotted() -> None:
    """Violation records are immutable value objects."""
    v = Violation(label="x", matched_text="y", line_number=1, why="z")
    try:
        v.label = "changed"  # type: ignore[misc]
    except Exception:  # noqa: BLE001  — frozen raises AttributeError or FrozenInstanceError
        return
    raise AssertionError("Violation should be frozen")
