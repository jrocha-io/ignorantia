"""Tests v2.23.1 (Fix 12 of RS-42 dogfood remediation) — persona voice heuristic.

Decisão 20 prescribes an academic impersonal voice that describes the
*method applied to the problem*, not the *execution of the pipeline*.
The dogfood transcripts (2026-05-08) showed Claude treating Decisão 20
as advisory and writing pipeline-execution narration anyway. The
Decisão 19 vocabulary checker (Fix 10) catches a complementary class —
brand-leakage tokens like ``v1.0.0`` / ``Decisão N``. This module
catches the *phrasing* class: ``Phase 3 invocou search_orchestrator.py``,
``cascata KEY → PROXY → FALLBACK_MD``, ``invoquei`` / ``rodei``, etc.

Voice quality is qualitative, so the checker is **advisory by default**:
exit 0 unless ``--strict`` is passed. The advisory mode is meant for
the Fase 7 writing loop; ``--strict`` is for chained pre-packaging gates.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_persona_voice import (  # noqa: E402  — sys.path injection
    Warning_,
    find_warnings,
)

CLI = ROOT / "scripts" / "check_persona_voice.py"


# ---------------------------------------------------------------------------
# Pure-API: clean prose
# ---------------------------------------------------------------------------


def test_clean_persona_prose_returns_no_warnings() -> None:
    """An academic-impersonal paragraph passes the heuristic."""
    text = (
        "A busca foi conduzida em onze bases de acesso aberto e oito bases "
        "comerciais via cascata de tentativas (credencial institucional, "
        "proxy, repositório aberto). As bases comerciais não puderam ser "
        "plenamente acessadas e foram registradas como lacuna a resolver."
    )
    assert find_warnings(text) == []


# ---------------------------------------------------------------------------
# Each pattern class
# ---------------------------------------------------------------------------


def test_phase_n_pipeline_stage_caught() -> None:
    text = "Phase 3 conduziu a busca em onze bases."
    labels = [w.label for w in find_warnings(text)]
    assert "pipeline-stage-reference" in labels


def test_fase_n_in_portuguese_caught() -> None:
    text = "Fase 4 aplicou os critérios de inclusão e exclusão."
    labels = [w.label for w in find_warnings(text)]
    assert "pipeline-stage-reference" in labels


def test_script_name_in_prose_caught() -> None:
    text = "A síntese foi gerada por cross_tabulation.py após a triagem."
    labels = [w.label for w in find_warnings(text)]
    assert "script-name-in-prose" in labels


def test_cli_flag_in_prose_caught() -> None:
    text = "O orquestrador foi invocado com --skip-tier0 e --area=cs_se."
    labels = [w.label for w in find_warnings(text)]
    assert "cli-flag-in-prose" in labels


def test_path_placeholder_in_prose_caught() -> None:
    text = "O resultado é gravado em <output_dir>/searches.json."
    labels = [w.label for w in find_warnings(text)]
    assert "path-placeholder-in-prose" in labels


def test_cascade_arrow_rhetoric_caught() -> None:
    text = "Cascata KEY → PROXY → FALLBACK_MD para bases comerciais."
    labels = [w.label for w in find_warnings(text)]
    assert "cascade-arrow-rhetoric" in labels


def test_em_dash_between_acronyms_is_not_a_false_positive() -> None:
    """``ICMJE — IA`` is normal punctuation, not cascade rhetoric."""
    text = "Conforme as diretrizes ICMJE — IA generativa não pode ser autora."
    labels = [w.label for w in find_warnings(text)]
    assert "cascade-arrow-rhetoric" not in labels


def test_tier_n_caught() -> None:
    text = "A busca cobriu Tier 1 e Tier 2 com cascata de fallback."
    labels = [w.label for w in find_warnings(text)]
    assert "tier-reference" in labels


def test_dd_n_design_decision_caught() -> None:
    text = "Conforme DD-10, os logs ficam em duas camadas."
    labels = [w.label for w in find_warnings(text)]
    assert "dd-reference" in labels


def test_first_person_execution_caught() -> None:
    text = "Invoquei o orquestrador e rodei o pipeline completo."
    labels = [w.label for w in find_warnings(text)]
    assert "first-person-execution" in labels


def test_orchestrator_vocabulary_caught() -> None:
    text = "O orchestrator processou as queries em subprocess long-running."
    labels = [w.label for w in find_warnings(text)]
    assert "infrastructure-vocabulary" in labels


# ---------------------------------------------------------------------------
# LaTeX preamble exclusion
# ---------------------------------------------------------------------------


def test_latex_preamble_packages_are_not_false_positives() -> None:
    """\\usepackage[utf8]{inputenc} and similar must not trip the checker."""
    text = (
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{hyperref}\n"
        "\\begin{document}\n"
        "A busca foi conduzida em onze bases de acesso aberto.\n"
        "\\end{document}\n"
    )
    assert find_warnings(text, is_latex=True) == []


def test_latex_body_warnings_still_caught_after_preamble() -> None:
    text = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Phase 3 invocou search_orchestrator.py para a busca.\n"
        "\\end{document}\n"
    )
    labels = {w.label for w in find_warnings(text, is_latex=True)}
    assert "pipeline-stage-reference" in labels
    assert "script-name-in-prose" in labels


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def _run_cli(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), str(path), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_advisory_mode_returns_zero_even_with_warnings(tmp_path: Path) -> None:
    """Default mode is advisory — exit 0 even when warnings are present."""
    f = tmp_path / "manuscript.md"
    f.write_text("Phase 3 invocou search_orchestrator.py.", encoding="utf-8")
    result = _run_cli(f)
    assert result.returncode == 0
    # Output goes to stdout in advisory mode.
    assert "warning" in result.stdout.lower() or "warning" in result.stderr.lower()


def test_cli_strict_mode_returns_two_on_warnings(tmp_path: Path) -> None:
    """``--strict`` flips the exit code to 2 when any warning fires."""
    f = tmp_path / "manuscript.md"
    f.write_text("Phase 3 invocou search_orchestrator.py.", encoding="utf-8")
    result = _run_cli(f, "--strict")
    assert result.returncode == 2


def test_cli_strict_mode_returns_zero_on_clean_text(tmp_path: Path) -> None:
    f = tmp_path / "manuscript.md"
    f.write_text(
        "A busca foi conduzida em onze bases de acesso aberto.", encoding="utf-8"
    )
    result = _run_cli(f, "--strict")
    assert result.returncode == 0


def test_cli_exit_one_on_missing_file(tmp_path: Path) -> None:
    result = _run_cli(tmp_path / "does-not-exist.tex")
    assert result.returncode == 1


def test_cli_quiet_flag_suppresses_per_warning_lines(tmp_path: Path) -> None:
    f = tmp_path / "manuscript.md"
    f.write_text("Phase 3 invocou search_orchestrator.py.", encoding="utf-8")
    result = _run_cli(f, "--quiet")
    output = result.stdout + result.stderr
    assert "warning" in output.lower()
    assert "why:" not in output


# ---------------------------------------------------------------------------
# Regression: RS-42 dogfood phrases must fire warnings
# ---------------------------------------------------------------------------


def test_rs42_dogfood_phrases_are_caught() -> None:
    """Phrases the user flagged as voice-leakage all fire warnings."""
    rs42_phrases = [
        "Phase 3 invocou search_orchestrator.py com area=cs_se",
        "11 Tier 1 + 8 Tier 2 paywall em cascata KEY → PROXY → FALLBACK_MD",
        "Conforme DD-10, os logs ficam em logs/logs_*.jsonl",
        "Invoquei pipeline_finalize.py e gerei o pacote final",
        "search_orchestrator processou as queries com --skip-tier0",
        "O resultado fica em <output_dir>/searches.json",
    ]
    for phrase in rs42_phrases:
        warnings = find_warnings(phrase)
        assert warnings, f"Phrase passed unexpectedly: {phrase!r}"


# ---------------------------------------------------------------------------
# Warning_ surface
# ---------------------------------------------------------------------------


def test_warning_record_is_frozen() -> None:
    w = Warning_(label="x", matched_text="y", line_number=1, why="z")
    try:
        w.label = "changed"  # type: ignore[misc]
    except Exception:  # noqa: BLE001
        return
    raise AssertionError("Warning_ should be frozen")
