"""Tests v2.23.1 (Fix 11 of RS-42 dogfood remediation) — pipeline invariants.

The dogfood RS-42 v1.0.0 (2026-05-08) shipped a package with::

    "execution_method": "single_session_ad_hoc_web_search"

— meaning Claude executed five Google-SERP queries inside the chat
session instead of invoking the orchestrator with the prescribed 14+
databases. The package was finalised anyway because nothing programmatic
enforced that the pipeline actually ran.

Fix 11 introduces ``scripts/check_pipeline_invariants.py`` enforcing
three invariants:

* I1 — ad-hoc execution_method is rejected unless ``--accept-ad-hoc-search``.
* I2 — ≥3 databases referenced in searches.json (per PRISMA-2020 minima).
* I3 — no ERROR steps in pipeline_summary.json (when present).

These tests drive both the pure-Python ``check`` API and the CLI surface.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_pipeline_invariants import (  # noqa: E402  — sys.path injection
    InvariantViolation,
    check,
)

CLI = ROOT / "scripts" / "check_pipeline_invariants.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_searches(
    out_dir: Path,
    *,
    execution_method: str | None = "orchestrator_full",
    databases: list[str] | None = None,
) -> Path:
    """Write a minimal searches.json for the invariant checker."""
    metadata: dict[str, object] = {}
    if execution_method is not None:
        metadata["execution_method"] = execution_method
    if databases is not None:
        metadata["tier1_databases_actually_queried"] = databases
    payload: dict[str, object] = {"metadata": metadata, "queries": []}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "searches.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_pipeline_summary(out_dir: Path, steps: list[dict[str, str]]) -> Path:
    """Write a pipeline_summary.json with the given step records."""
    payload = {"steps": steps}
    path = out_dir / "pipeline_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Pure-API: clean fixtures pass
# ---------------------------------------------------------------------------


def test_clean_fixture_returns_no_violations(tmp_path: Path) -> None:
    """Orchestrator method + 5 databases + no ERROR steps = clean."""
    _write_searches(
        tmp_path,
        execution_method="orchestrator_full",
        databases=["pubmed", "scopus", "wos", "openalex", "scielo"],
    )
    _write_pipeline_summary(
        tmp_path,
        steps=[
            {"name": "search", "status": "OK"},
            {"name": "screening", "status": "OK"},
            {"name": "render", "status": "OK"},
        ],
    )
    assert check(tmp_path) == []


# ---------------------------------------------------------------------------
# I1 — ad-hoc execution_method
# ---------------------------------------------------------------------------


def test_i1_ad_hoc_method_is_rejected_by_default(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="single_session_ad_hoc_web_search",
        databases=["a", "b", "c"],
    )
    violations = check(tmp_path)
    assert any(v.invariant_id == "I1" for v in violations)


def test_i1_ad_hoc_method_accepted_with_explicit_flag(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="single_session_ad_hoc_web_search",
        databases=["a", "b", "c"],
    )
    violations = check(tmp_path, accept_ad_hoc=True)
    assert all(v.invariant_id != "I1" for v in violations)


# ---------------------------------------------------------------------------
# I2 — ≥3 databases
# ---------------------------------------------------------------------------


def test_i2_fails_with_fewer_than_three_databases(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="orchestrator_full",
        databases=["pubmed", "scopus"],
    )
    violations = check(tmp_path)
    assert any(v.invariant_id == "I2" for v in violations)


def test_i2_passes_with_three_databases(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="orchestrator_full",
        databases=["a", "b", "c"],
    )
    violations = check(tmp_path)
    assert all(v.invariant_id != "I2" for v in violations)


def test_i2_recognises_legacy_per_database_layout(tmp_path: Path) -> None:
    """The v2 layout uses ``per_database`` instead of metadata list."""
    payload = {
        "metadata": {"execution_method": "orchestrator_full"},
        "per_database": [
            {"database": "pubmed", "queries": []},
            {"database": "scopus", "queries": []},
            {"database": "wos", "queries": []},
        ],
    }
    (tmp_path / "searches.json").write_text(json.dumps(payload), encoding="utf-8")
    violations = check(tmp_path)
    assert all(v.invariant_id != "I2" for v in violations)


# ---------------------------------------------------------------------------
# I3 — pipeline_summary.json error steps
# ---------------------------------------------------------------------------


def test_i3_fails_when_any_step_has_error_status(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="orchestrator_full",
        databases=["a", "b", "c"],
    )
    _write_pipeline_summary(
        tmp_path,
        steps=[
            {"name": "search", "status": "OK"},
            {"name": "compile_pdf", "status": "ERROR"},
        ],
    )
    violations = check(tmp_path)
    assert any(v.invariant_id == "I3" for v in violations)


def test_i3_passes_when_summary_absent(tmp_path: Path) -> None:
    """Missing pipeline_summary.json is not a violation by itself."""
    _write_searches(
        tmp_path,
        execution_method="orchestrator_full",
        databases=["a", "b", "c"],
    )
    violations = check(tmp_path)
    assert all(v.invariant_id != "I3" for v in violations)


# ---------------------------------------------------------------------------
# I0 — input errors
# ---------------------------------------------------------------------------


def test_i0_fails_when_searches_missing(tmp_path: Path) -> None:
    violations = check(tmp_path)
    assert violations and violations[0].invariant_id == "I0"


def test_i0_fails_when_searches_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "searches.json").write_text("{not json", encoding="utf-8")
    violations = check(tmp_path)
    assert violations and violations[0].invariant_id == "I0"


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def _run_cli(output_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), str(output_dir), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exit_zero_on_clean_fixture(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="orchestrator_full",
        databases=["a", "b", "c"],
    )
    result = _run_cli(tmp_path)
    assert result.returncode == 0


def test_cli_exit_two_on_invariant_violation(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="single_session_ad_hoc_web_search",
        databases=["a", "b", "c"],
    )
    result = _run_cli(tmp_path)
    assert result.returncode == 2
    assert "FAILED" in result.stderr
    assert "I1" in result.stderr


def test_cli_exit_one_on_missing_searches(tmp_path: Path) -> None:
    result = _run_cli(tmp_path)
    assert result.returncode == 1


def test_cli_exit_one_on_invalid_directory(tmp_path: Path) -> None:
    result = _run_cli(tmp_path / "does-not-exist")
    assert result.returncode == 1


def test_cli_accepts_ad_hoc_with_flag(tmp_path: Path) -> None:
    _write_searches(
        tmp_path,
        execution_method="single_session_ad_hoc_web_search",
        databases=["a", "b", "c"],
    )
    result = _run_cli(tmp_path, "--accept-ad-hoc-search")
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Regression: RS-42 v1.0.0 fixture must FAIL
# ---------------------------------------------------------------------------


def test_rs42_v1_searches_payload_is_caught(tmp_path: Path) -> None:
    """A searches.json shaped like RS-42 v1.0.0 is rejected on I1.

    The actual RS-42 file declares execution_method ad-hoc plus 5
    databases, so I2 passes. I1 must fire (ad-hoc rejected).
    """
    payload = {
        "metadata": {
            "review_id": "RS-42",
            "version": "1.0.0",
            "execution_method": "single_session_ad_hoc_web_search",
            "tier1_databases_actually_queried": [
                "google_scholar_proxy",
                "pubmed_central_proxy",
                "arxiv_proxy",
                "medrxiv_proxy",
                "crossref_verification",
            ],
        }
    }
    (tmp_path / "searches.json").write_text(json.dumps(payload), encoding="utf-8")
    violations = check(tmp_path)
    ids = {v.invariant_id for v in violations}
    assert "I1" in ids
    assert "I2" not in ids  # 5 databases > 3 minimum


# ---------------------------------------------------------------------------
# InvariantViolation surface
# ---------------------------------------------------------------------------


def test_invariant_violation_is_frozen() -> None:
    v = InvariantViolation(invariant_id="I1", message="x")
    try:
        v.invariant_id = "I9"  # type: ignore[misc]
    except Exception:  # noqa: BLE001
        return
    raise AssertionError("InvariantViolation should be frozen")
