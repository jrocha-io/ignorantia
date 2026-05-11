"""Fix 21 / Phase A — biphasic handoff schema validation.

The handoff JSON is the sole interface between Phase 1 (chat) and
Phase 2 (Cowork). If the schema lets bad handoffs through, Phase 2
either crashes mid-retrieval or silently does the wrong thing — both
are worse than rejecting the handoff at the boundary.

These tests pin:

- The schema file is valid JSON Schema (loads + has the expected
  top-level structure).
- A minimal valid handoff round-trips through ``jsonschema.validate``.
- Each forbidden mistake (missing field, wrong enum, malformed DOI,
  wrong phase number, hash mismatch) is rejected.

``jsonschema`` is a soft dependency: tests skip cleanly if the
package is not installed in the local environment (CI installs it via
``[dev]`` extra).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "schemas" / "handoff-v1.schema.json"


# ── helpers ─────────────────────────────────────────────────────────────


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _canonical_hash(handoff: dict) -> str:
    """Compute the canonical SHA-256 of a handoff, excluding handoff_hash."""
    copy = {k: v for k, v in handoff.items() if k != "handoff_hash"}
    raw = json.dumps(copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _minimal_valid_handoff() -> dict:
    """A handoff just big enough to satisfy every minItems/required."""
    body = {
        "phase": 1,
        "schema_version": "1.0",
        "created_at": "2026-05-11T12:00:00Z",
        "protocol": {
            "title": "Validade de scoping reviews assistidas por IA",
            "authors": [
                {
                    "name": "José Cândido Pereira da Rocha",
                    "orcid": "0009-0000-8359-872X",
                }
            ],
            "review_type": "scoping_review",
            "review_purpose": "design_foundational",
            "language": "pt-BR",
            "citation_style": "abnt",
            "temporal_window": {"start_date": "2018-01-01", "end_date": "2026-05-09"},
            "pcc": {
                "population": "Estudos sobre uso de LLMs em revisões da literatura",
                "concept": "Validade, acurácia, alucinação, viés, reprodutibilidade",
                "context": "Período 2018-2026; guidelines emergentes EQUATOR",
            },
            "sub_questions": [
                {"id": "RQ1.1", "text": "Qual é a taxa documentada de alucinação?"}
            ],
            "inclusion_criteria": [{"id": "IC1", "text": "Peer-reviewed ou preprint"}],
            "exclusion_criteria": [{"id": "EC1", "text": "Pré-2018"}],
            "bases": [
                {
                    "id": "arxiv",
                    "name": "arXiv",
                    "access_tier": "open_access",
                    "execution_mode": "direct_api",
                },
                {
                    "id": "openalex",
                    "name": "OpenAlex",
                    "access_tier": "open_access",
                    "execution_mode": "direct_api",
                },
                {
                    "id": "crossref",
                    "name": "Crossref",
                    "access_tier": "open_access",
                    "execution_mode": "direct_api",
                },
            ],
            "search_strings": {
                "arxiv": '("large language model" OR LLM) AND "systematic review"',
                "openalex": '("LLM" OR "large language model") AND "literature review"',
                "crossref": '"systematic review" AND "artificial intelligence"',
            },
            "ai_disclosure": {
                "template": "industrial_secret_cnpq_pt",
                "stages_used": ["search_string_design", "screening_title_abstract"],
            },
        },
        "searches": [
            {
                "base_id": "arxiv",
                "query": "test",
                "executed_at": "2026-05-09T03:00:00Z",
                "n_hits_raw": 200,
                "status": "success",
            },
            {
                "base_id": "openalex",
                "query": "test",
                "executed_at": "2026-05-09T03:01:00Z",
                "n_hits_raw": 133,
                "status": "success",
            },
            {
                "base_id": "crossref",
                "query": "test",
                "executed_at": "2026-05-09T03:02:00Z",
                "n_hits_raw": 200,
                "status": "success",
            },
        ],
        "dedup": {
            "n_in": 533,
            "n_out": 525,
            "hierarchy": ["doi", "arxiv_id", "title_author_year_normalized"],
        },
        "screening": {
            "passes": [
                {
                    "name": "p1_keyword_match",
                    "n_in": 525,
                    "n_out": 200,
                    "criteria": "IA terms AND review terms",
                }
            ],
            "trace_per_doi": {
                "10.1590/abc-001": [
                    {
                        "pass_name": "p1_keyword_match",
                        "decision": "include",
                        "reason": "matches both",
                    }
                ]
            },
        },
        "included_for_fulltext": [
            {
                "doi": "10.1590/abc-001",
                "title": "Example study",
                "year": 2024,
                "expected_access_tier": "open_access",
            }
        ],
        "metadata": {
            "skill_version": "3.0.0",
            "model": "anthropic/claude-opus-4-7",
            "phase1_session_id": "phase1-2026-05-09-001",
        },
    }
    body["handoff_hash"] = _canonical_hash(body)
    return body


# ── core schema ─────────────────────────────────────────────────────────


def test_schema_file_is_valid_json():
    """The schema must parse as JSON before any validation runs."""
    schema = _load_schema()
    assert schema["$schema"].startswith("https://json-schema.org/")
    assert schema["type"] == "object"
    assert "handoff_hash" in schema["required"]


def test_minimal_valid_handoff_validates():
    """A handoff that satisfies every required field passes validation."""
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    jsonschema.validate(handoff, schema)


# ── rejection: missing required fields ─────────────────────────────────


@pytest.mark.parametrize(
    "missing_field",
    [
        "phase",
        "schema_version",
        "created_at",
        "protocol",
        "searches",
        "dedup",
        "screening",
        "included_for_fulltext",
        "metadata",
        "handoff_hash",
    ],
)
def test_missing_top_level_field_is_rejected(missing_field):
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    del handoff[missing_field]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


# ── rejection: wrong types / enums ─────────────────────────────────────


def test_wrong_phase_number_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["phase"] = 2  # Phase 2 doesn't emit a phase-1 handoff.
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_invalid_review_type_enum_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["protocol"]["review_type"] = "narrative_review"  # not in enum
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_invalid_review_purpose_enum_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["protocol"]["review_purpose"] = "exploration"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_malformed_doi_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["included_for_fulltext"][0]["doi"] = "not-a-doi"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_short_doi_with_only_one_digit_prefix_is_rejected():
    """Crossref pattern requires 4-9 digits after '10.'; 10.1/x is invalid."""
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["included_for_fulltext"][0]["doi"] = "10.1/x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_malformed_orcid_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["protocol"]["authors"][0]["orcid"] = "0000-0000"  # incomplete
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_fewer_than_three_bases_is_rejected():
    """PRISMA-2020 requires multiple bases; the schema enforces minItems=3."""
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["protocol"]["bases"] = handoff["protocol"]["bases"][:2]
    handoff["searches"] = handoff["searches"][:2]  # keep consistent
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_empty_included_list_is_rejected():
    """If T/A screening excludes everything, Phase 2 has nothing to do.
    The handoff must declare at least one DOI to retrieve."""
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["included_for_fulltext"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_invalid_handoff_hash_format_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["handoff_hash"] = "short"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_invalid_schema_version_is_rejected():
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["schema_version"] = "2.0"  # major must be 1.x for this schema
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


def test_additional_top_level_property_is_rejected():
    """``additionalProperties: false`` blocks rogue fields."""
    schema = _load_schema()
    handoff = _minimal_valid_handoff()
    handoff["extra_field_phase1_decided_to_add"] = "oops"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(handoff, schema)


# ── hash semantics ──────────────────────────────────────────────────────


def test_canonical_hash_excludes_handoff_hash_field():
    """The hash must not depend on itself; otherwise no value can satisfy it."""
    handoff = _minimal_valid_handoff()
    h1 = _canonical_hash(handoff)
    handoff["handoff_hash"] = "0" * 64
    h2 = _canonical_hash(handoff)
    assert h1 == h2


def test_canonical_hash_is_stable_under_key_reordering():
    """JSON serialisation must canonicalise — same content, same hash."""
    handoff = _minimal_valid_handoff()
    h1 = _canonical_hash(handoff)
    # Rebuild with reversed top-level key order
    rebuilt = {k: handoff[k] for k in reversed(list(handoff.keys()))}
    h2 = _canonical_hash(rebuilt)
    assert h1 == h2


def test_canonical_hash_changes_when_substantive_content_changes():
    handoff = _minimal_valid_handoff()
    h1 = _canonical_hash(handoff)
    handoff["protocol"]["title"] = "A different title"
    h2 = _canonical_hash(handoff)
    assert h1 != h2
