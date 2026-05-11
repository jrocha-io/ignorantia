"""Fix 21 / Phase E1 — phase2_init: handoff validation + output dir bootstrap.

phase2_init is the single command Phase 2 (Cowork) runs to start a
biphasic execution. It validates the handoff JSON, recomputes the
integrity hash, and sets up the output directory layout.

These tests pin its contract:

- Valid handoff → exit 0, run dir bootstrapped with expected layout.
- Schema-invalid handoff → exit 2, no run dir touched.
- Hash mismatch → exit 2.
- Missing handoff file → exit 1.
- Cross-reference inconsistencies (DOI in included list but with
  exclude decision) → exit 2.
- Existing run dir without --force → exit 1.
- --force overwrites an existing run dir.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SCRIPT = ROOT / "scripts" / "phase2_init.py"


def _canonical_hash(handoff: dict) -> str:
    copy = {k: v for k, v in handoff.items() if k != "handoff_hash"}
    raw = json.dumps(copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_handoff() -> dict:
    """A minimal valid handoff per schemas/handoff-v1.schema.json."""
    body = {
        "phase": 1,
        "schema_version": "1.0",
        "created_at": "2026-05-11T12:00:00Z",
        "protocol": {
            "title": "Validade de scoping reviews assistidas por IA",
            "authors": [{"name": "Test Author", "orcid": "0009-0000-8359-872X"}],
            "review_type": "scoping_review",
            "review_purpose": "design_foundational",
            "language": "pt-BR",
            "citation_style": "abnt",
            "temporal_window": {"start_date": "2018-01-01", "end_date": "2026-05-09"},
            "pcc": {
                "population": "Estudos sobre uso de LLMs em revisões",
                "concept": "Validade, alucinação, reprodutibilidade",
                "context": "Período 2018-2026",
            },
            "sub_questions": [{"id": "RQ1.1", "text": "Qual a taxa de alucinação?"}],
            "inclusion_criteria": [{"id": "IC1", "text": "Peer-reviewed ou preprint"}],
            "exclusion_criteria": [{"id": "EC1", "text": "Pré-2018"}],
            "bases": [
                {"id": "arxiv", "name": "arXiv",
                 "access_tier": "open_access", "execution_mode": "direct_api"},
                {"id": "openalex", "name": "OpenAlex",
                 "access_tier": "open_access", "execution_mode": "direct_api"},
                {"id": "crossref", "name": "Crossref",
                 "access_tier": "open_access", "execution_mode": "direct_api"},
            ],
            "search_strings": {
                "arxiv": '("LLM" OR "large language model") AND "systematic review"',
                "openalex": '("LLM") AND "literature review"',
                "crossref": '"systematic review" AND "AI"',
            },
            "ai_disclosure": {
                "template": "industrial_secret_cnpq_pt",
                "stages_used": ["screening_title_abstract"],
            },
        },
        "searches": [
            {"base_id": "arxiv", "query": "test",
             "executed_at": "2026-05-09T03:00:00Z",
             "n_hits_raw": 200, "status": "success"},
            {"base_id": "openalex", "query": "test",
             "executed_at": "2026-05-09T03:01:00Z",
             "n_hits_raw": 133, "status": "success"},
            {"base_id": "crossref", "query": "test",
             "executed_at": "2026-05-09T03:02:00Z",
             "n_hits_raw": 200, "status": "success"},
        ],
        "dedup": {"n_in": 533, "n_out": 525,
                  "hierarchy": ["doi", "arxiv_id", "title_author_year_normalized"]},
        "screening": {
            "passes": [{"name": "p1", "n_in": 525, "n_out": 200,
                        "criteria": "IA terms AND review terms"}],
            "trace_per_doi": {
                "10.1590/abc-001": [
                    {"pass_name": "p1", "decision": "include", "reason": "match"}
                ]
            },
        },
        "included_for_fulltext": [
            {"doi": "10.1590/abc-001", "title": "Example", "year": 2024,
             "expected_access_tier": "open_access"}
        ],
        "metadata": {
            "skill_version": "3.0.0",
            "model": "anthropic/claude-opus-4-7",
            "phase1_session_id": "phase1-test-001",
        },
    }
    body["handoff_hash"] = _canonical_hash(body)
    return body


def _write_handoff(tmp_path: Path, handoff: dict) -> Path:
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, check=False,
    )


# ── happy path ─────────────────────────────────────────────────────────


def test_valid_handoff_bootstraps_run_dir(tmp_path: Path):
    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    result = _run(str(handoff_path), "--output-dir", str(out))
    assert result.returncode == 0, result.stderr
    # The run dir is named author-title-vX.Y.Z (no brand)
    run_dirs = list(out.glob("*"))
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert "ignorantia" not in run_dir.name  # brand-free filename
    # Expected layout
    for sub in ("sources", "gates", "logs"):
        assert (run_dir / sub).is_dir()
    for f in ("handoff.json", "extraction.csv", "claim_to_source.json",
              "gap_report.md", "phase2_state.json"):
        assert (run_dir / f).is_file(), f"{f} missing"


def test_handoff_copy_is_byte_identical_modulo_pretty_print(tmp_path: Path):
    """The handoff copied to <run>/handoff.json must preserve the
    semantic content. The canonical hash must match the original."""
    from phase2_init import canonical_hash

    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    _run(str(handoff_path), "--output-dir", str(out))
    run_dir = next(out.glob("*"))
    copied = json.loads((run_dir / "handoff.json").read_text("utf-8"))
    assert canonical_hash(copied) == handoff["handoff_hash"]


def test_phase2_state_records_started_at_and_step(tmp_path: Path):
    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    _run(str(handoff_path), "--output-dir", str(out))
    run_dir = next(out.glob("*"))
    state = json.loads((run_dir / "phase2_state.json").read_text("utf-8"))
    assert state["phase"] == 2
    assert "init" in state["completed_steps"]
    assert state["handoff_hash"] == handoff["handoff_hash"]


def test_extraction_csv_has_header(tmp_path: Path):
    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    _run(str(handoff_path), "--output-dir", str(out))
    run_dir = next(out.glob("*"))
    csv_text = (run_dir / "extraction.csv").read_text("utf-8")
    assert csv_text.startswith("study_id,doi,title,")
    assert "claim_ids" in csv_text.splitlines()[0]


def test_claim_to_source_json_is_initially_empty_list(tmp_path: Path):
    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    _run(str(handoff_path), "--output-dir", str(out))
    run_dir = next(out.glob("*"))
    assert json.loads((run_dir / "claim_to_source.json").read_text()) == []


# ── error paths ────────────────────────────────────────────────────────


def test_missing_handoff_file_exits_1(tmp_path: Path):
    result = _run(str(tmp_path / "nope.json"), "--output-dir", str(tmp_path / "runs"))
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_invalid_json_exits_1(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json {", encoding="utf-8")
    result = _run(str(bad), "--output-dir", str(tmp_path / "runs"))
    assert result.returncode == 1
    assert "not valid JSON" in result.stderr


def test_schema_invalid_handoff_exits_2(tmp_path: Path):
    """A handoff that fails schema validation must trigger exit 2 and
    leave no run dir behind."""
    bad = _valid_handoff()
    bad["protocol"]["review_type"] = "narrative_review"  # not in enum
    bad["handoff_hash"] = _canonical_hash(bad)
    handoff_path = _write_handoff(tmp_path, bad)
    out = tmp_path / "runs"
    result = _run(str(handoff_path), "--output-dir", str(out))
    assert result.returncode == 2
    assert "schema validation" in result.stderr.lower() or "missing required" in result.stderr.lower()
    # No run dir was created
    assert not list(out.glob("*"))


def test_hash_mismatch_exits_2(tmp_path: Path):
    """If the handoff was modified after Phase 1 sealed it, the
    recomputed hash won't match. Phase 2 must abort."""
    handoff = _valid_handoff()
    handoff["protocol"]["title"] = "Tampered title"  # mutate after hash
    # Don't recompute handoff_hash → mismatch
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    result = _run(str(handoff_path), "--output-dir", str(out))
    assert result.returncode == 2
    assert "hash mismatch" in result.stderr.lower() or "modified after" in result.stderr.lower()


def test_included_doi_with_exclude_decision_exits_2(tmp_path: Path):
    """A DOI in included_for_fulltext[] must have a positive final
    screening decision. Schema doesn't enforce; phase2_init does."""
    handoff = _valid_handoff()
    handoff["screening"]["trace_per_doi"]["10.1590/abc-001"] = [
        {"pass_name": "p1", "decision": "exclude", "reason": "out of scope"}
    ]
    handoff["handoff_hash"] = _canonical_hash(handoff)
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    result = _run(str(handoff_path), "--output-dir", str(out))
    assert result.returncode == 2
    assert "cross-reference" in result.stderr.lower() or "final screening" in result.stderr.lower()


def test_included_doi_with_no_screening_trace_exits_2(tmp_path: Path):
    handoff = _valid_handoff()
    handoff["screening"]["trace_per_doi"] = {}
    handoff["handoff_hash"] = _canonical_hash(handoff)
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"
    result = _run(str(handoff_path), "--output-dir", str(out))
    assert result.returncode == 2


# ── --force semantics ──────────────────────────────────────────────────


def test_existing_run_dir_without_force_exits_1(tmp_path: Path):
    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"

    # First run succeeds
    result_a = _run(str(handoff_path), "--output-dir", str(out))
    assert result_a.returncode == 0

    # Second run on the same handoff (same derived run_id) must fail
    result_b = _run(str(handoff_path), "--output-dir", str(out))
    assert result_b.returncode == 1
    assert "already exists" in result_b.stderr


def test_force_overwrites_existing_run_dir(tmp_path: Path):
    handoff = _valid_handoff()
    handoff_path = _write_handoff(tmp_path, handoff)
    out = tmp_path / "runs"

    _run(str(handoff_path), "--output-dir", str(out))
    run_dir = next(out.glob("*"))
    sentinel = run_dir / "sources" / "stale.txt"
    sentinel.write_text("stale", encoding="utf-8")
    assert sentinel.is_file()

    result = _run(str(handoff_path), "--output-dir", str(out), "--force")
    assert result.returncode == 0
    assert not sentinel.exists()  # sentinel got nuked by --force


# ── pure-function tests ────────────────────────────────────────────────


def test_canonical_hash_excludes_handoff_hash_field():
    from phase2_init import canonical_hash

    handoff = _valid_handoff()
    h1 = canonical_hash(handoff)
    handoff["handoff_hash"] = "0" * 64
    h2 = canonical_hash(handoff)
    assert h1 == h2


def test_canonical_hash_is_stable_under_key_reordering():
    from phase2_init import canonical_hash

    handoff = _valid_handoff()
    h1 = canonical_hash(handoff)
    rebuilt = {k: handoff[k] for k in reversed(list(handoff.keys()))}
    h2 = canonical_hash(rebuilt)
    assert h1 == h2


def test_slugify_handles_portuguese_diacritics():
    from phase2_init import slugify

    assert slugify("Validade de Scoping Reviews") == "validade-de-scoping-reviews"
    assert slugify("Métodos Críticos de Análise") == "metodos-criticos-de-analise"
    assert slugify("São Paulo + Educação") == "sao-paulo-educacao"


def test_derive_run_id_contains_no_brand():
    from phase2_init import derive_run_id

    handoff = _valid_handoff()
    run_id = derive_run_id(handoff)
    assert "ignorantia" not in run_id.lower()
    assert run_id.endswith("-v3.0.0")
    # Author slug + title slug
    assert "author" in run_id  # from "Test Author"


def test_cross_check_accepts_borderline_as_final_decision():
    """Borderline DOIs that survived to the included list are OK —
    Phase 2 can attempt retrieval and let the operator decide later."""
    from phase2_init import cross_check_included_against_screening

    handoff = _valid_handoff()
    handoff["screening"]["trace_per_doi"]["10.1590/abc-001"] = [
        {"pass_name": "p1", "decision": "include", "reason": "..."},
        {"pass_name": "p2", "decision": "borderline", "reason": "edge case"},
    ]
    errors = cross_check_included_against_screening(handoff)
    assert errors == []
