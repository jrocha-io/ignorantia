"""Tests v2.23.1 (Fix 9 of RS-42 dogfood remediation) — assessment gate.

The assessor (`scripts/generate_assessment.py`) used to always exit 0 even
when reporting eliminatórios or scores far below the submission threshold.
RS-42 v1.0.0 was packaged and shipped with a 4.0/10.0 grade and three
eliminatórios because no programmatic gate stood in the way.

Fix 9 turns the assessor into a gate:
  * default `--gate-min-score` of 7.0;
  * exit code 2 on eliminatórios OR sub-threshold score;
  * machine-readable `assessment_gate.json` sidecar in `--package-dir`;
  * `--no-gate` opt-out for triage / partial-package debugging.

These tests drive the assessor as a subprocess against minimal fixtures, so
they exercise the real CLI surface — which is what the SKILL.md flow uses.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSESSOR = ROOT / "scripts" / "generate_assessment.py"


def _write_minimal_package(package_dir: Path) -> tuple[Path, Path, Path]:
    """Write the smallest set of inputs the assessor demands.

    The minimal fixture deliberately fails on multiple dimensions — it has
    no protocol.md, no compliance declaration, no real corpus — so the
    assessor flags eliminatórios and scores well below 7.0. That is what
    the gate-fail tests need.

    Returns a tuple of (content.json, extraction.csv, qa.csv) paths.
    """
    package_dir.mkdir(parents=True, exist_ok=True)
    content = package_dir / "manuscript-content.json"
    content.write_text(
        json.dumps(
            {
                "title": "minimal",
                "abstract": "",
                "sections": {},
            }
        ),
        encoding="utf-8",
    )
    extraction = package_dir / "extraction.csv"
    extraction.write_text("study_id,title\n", encoding="utf-8")
    qa = package_dir / "quality-appraisal.csv"
    qa.write_text("study_id,score\n", encoding="utf-8")
    return content, extraction, qa


def _run_assessor(
    *,
    package_dir: Path,
    out: Path,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the assessor as a subprocess; capture exit code + stderr."""
    content, extraction, qa = (
        package_dir / "manuscript-content.json",
        package_dir / "extraction.csv",
        package_dir / "quality-appraisal.csv",
    )
    cmd = [
        sys.executable,
        str(ASSESSOR),
        "--package-dir",
        str(package_dir),
        "--content",
        str(content),
        "--extraction",
        str(extraction),
        "--qa",
        str(qa),
        "--version",
        "1.0.0",
        "--topic-slug",
        "test-topic",
        "--out",
        str(out),
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


# ----------------------------------------------------------------------
# Gate FAILS by default on eliminatórios + sub-threshold score
# ----------------------------------------------------------------------


def test_gate_fails_with_exit_code_2_on_minimal_package(tmp_path: Path) -> None:
    """Default gate (min 7.0) rejects a minimal-fixture package."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    result = _run_assessor(package_dir=pkg, out=out)
    assert result.returncode == 2, (
        f"Expected gate failure (exit 2); got {result.returncode}.\n"
        f"stderr:\n{result.stderr}"
    )


def test_gate_failure_message_lists_reasons(tmp_path: Path) -> None:
    """Gate-fail stderr names the failure reasons."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    result = _run_assessor(package_dir=pkg, out=out)
    assert "GATE FAILED" in result.stderr
    # Either reason (eliminatório OR score) must appear.
    assert "eliminatório" in result.stderr or "score" in result.stderr


# ----------------------------------------------------------------------
# Sidecar JSON is always written
# ----------------------------------------------------------------------


def test_sidecar_json_written_on_failure(tmp_path: Path) -> None:
    """`assessment_gate.json` lands in --package-dir even when the gate fails."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    _run_assessor(package_dir=pkg, out=out)
    sidecar = pkg / "assessment_gate.json"
    assert sidecar.is_file(), "assessment_gate.json sidecar missing"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert "score" in payload
    assert payload["min_score"] == 7.0
    assert payload["eliminatory_count"] >= 1
    assert payload["version"] == "1.0.0"


def test_sidecar_payload_schema(tmp_path: Path) -> None:
    """Sidecar payload exposes the keys downstream tools need."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    _run_assessor(package_dir=pkg, out=out)
    payload = json.loads((pkg / "assessment_gate.json").read_text(encoding="utf-8"))
    expected_keys = {
        "passed",
        "score",
        "min_score",
        "eliminatory_count",
        "eliminatory_failed",
        "score_failed",
        "report_path",
        "version",
    }
    assert expected_keys.issubset(payload.keys())


# ----------------------------------------------------------------------
# Markdown report is still written even when the gate fails
# ----------------------------------------------------------------------


def test_markdown_report_written_on_failure(tmp_path: Path) -> None:
    """Gate failure does NOT suppress the human-readable report."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    _run_assessor(package_dir=pkg, out=out)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "Avaliação automática" in text or "Final score" in text


# ----------------------------------------------------------------------
# --no-gate keeps the report but exits 0
# ----------------------------------------------------------------------


def test_no_gate_flag_returns_zero_despite_failure(tmp_path: Path) -> None:
    """--no-gate flips the exit code to 0 even when the gate would have failed."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    result = _run_assessor(package_dir=pkg, out=out, extra=["--no-gate"])
    assert result.returncode == 0, (
        f"--no-gate should keep exit 0; got {result.returncode}.\n"
        f"stderr:\n{result.stderr}"
    )
    # Sidecar still records the failure so downstream tools see the truth.
    payload = json.loads((pkg / "assessment_gate.json").read_text(encoding="utf-8"))
    assert payload["passed"] is False


# ----------------------------------------------------------------------
# Custom --gate-min-score
# ----------------------------------------------------------------------


def test_gate_respects_custom_min_score(tmp_path: Path) -> None:
    """A very low --gate-min-score still fails if eliminatórios are present."""
    pkg = tmp_path / "pkg"
    _write_minimal_package(pkg)
    out = tmp_path / "avaliacao.md"

    result = _run_assessor(
        package_dir=pkg, out=out, extra=["--gate-min-score", "0.0"]
    )
    # Score-floor passes (0.0), but eliminatórios still fail the gate.
    assert result.returncode == 2
    payload = json.loads((pkg / "assessment_gate.json").read_text(encoding="utf-8"))
    assert payload["score_failed"] is False
    assert payload["eliminatory_failed"] is True
