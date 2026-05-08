"""Unit tests for the JSON-schema runtime validator.

Pins:

* every registered manifest name resolves to a valid schema document;
* a fully-populated payload that matches the schema validates;
* missing required fields, type errors, and ``additionalProperties``
  violations are caught;
* unknown manifest names raise :class:`KeyError`;
* the ``method`` enum on ``search_result`` rejects unknown values
  (guards against drift in :class:`Method` without a schema bump);
* the ``status`` enum on ``finalize_pipeline_result`` rejects unknown
  values (guards against drift in :class:`StepStatus`).
"""

from __future__ import annotations

import pytest
from jsonschema.exceptions import ValidationError

from ignorantia.interface.manifests import (
    known_manifests,
    load_schema,
    validate_manifest,
)


class TestKnownManifests:
    def test_all_subcommand_manifests_registered(self) -> None:
        names = set(known_manifests())
        assert names == {
            "audit_result",
            "finalize_pipeline_result",
            "render_result",
            "search_result",
            "search_full_result",
        }


class TestLoadSchema:
    @pytest.mark.parametrize("name", list(known_manifests()))
    def test_each_schema_loads_and_is_a_dict(self, name: str) -> None:
        schema = load_schema(name)
        assert isinstance(schema, dict)
        assert schema["$schema"].startswith("https://json-schema.org/")
        assert schema["type"] == "object"

    def test_unknown_name_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="unknown manifest schema"):
            load_schema("not_a_manifest")

    def test_load_schema_is_cached(self) -> None:
        first = load_schema("audit_result")
        second = load_schema("audit_result")
        # Cached: same dict instance returned.
        assert first is second


# ----------------------------------------------------------------------
# audit_result
# ----------------------------------------------------------------------


class TestAuditResultSchema:
    def test_minimal_valid_payload_passes(self) -> None:
        validate_manifest(
            "audit_result",
            {
                "timestamp_iso8601": "2026-05-07T12:00:00Z",
                "action": "search.run",
                "manifest_size": 1,
            },
        )

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "audit_result",
                {"action": "x", "manifest_size": 1},  # missing timestamp
            )

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "audit_result",
                {
                    "timestamp_iso8601": "t",
                    "action": "x",
                    "manifest_size": 1,
                    "stowaway": "should fail",
                },
            )

    def test_zero_manifest_size_rejected(self) -> None:
        # A manifest_size of 0 means no entry was appended — the
        # CLI never emits this. The schema enforces it for safety.
        with pytest.raises(ValidationError):
            validate_manifest(
                "audit_result",
                {
                    "timestamp_iso8601": "t",
                    "action": "x",
                    "manifest_size": 0,
                },
            )


# ----------------------------------------------------------------------
# finalize_pipeline_result
# ----------------------------------------------------------------------


class TestFinalizePipelineResultSchema:
    def test_valid_payload_with_steps_passes(self) -> None:
        validate_manifest(
            "finalize_pipeline_result",
            {
                "started_at_iso8601": "2026-05-07T12:00:00Z",
                "finished_at_iso8601": "2026-05-07T12:00:05Z",
                "n_ok": 1,
                "n_skipped": 1,
                "n_errors": 0,
                "final_artifacts": ["out/a.html"],
                "is_successful": True,
                "steps": [
                    {
                        "name": "a",
                        "status": "ok",
                        "message": "",
                        "artifact": "out/a.html",
                    },
                    {
                        "name": "b",
                        "status": "skipped",
                        "message": "by user",
                        "artifact": None,
                    },
                ],
            },
        )

    def test_step_status_rejects_unknown_enum_value(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "finalize_pipeline_result",
                {
                    "started_at_iso8601": "t",
                    "finished_at_iso8601": "t",
                    "n_ok": 0,
                    "n_skipped": 0,
                    "n_errors": 0,
                    "final_artifacts": [],
                    "is_successful": True,
                    "steps": [
                        {
                            "name": "a",
                            "status": "weird",
                            "message": "",
                            "artifact": None,
                        }
                    ],
                },
            )


# ----------------------------------------------------------------------
# render_result
# ----------------------------------------------------------------------


class TestRenderResultSchema:
    def test_valid_payload_passes(self) -> None:
        validate_manifest(
            "render_result",
            {
                "output_format": "html",
                "byte_size": 1024,
                "output_path": "out/manuscript.html",
            },
        )

    def test_unknown_output_format_rejected(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "render_result",
                {
                    "output_format": "epub",
                    "byte_size": 1,
                    "output_path": "x",
                },
            )

    def test_negative_byte_size_rejected(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "render_result",
                {
                    "output_format": "html",
                    "byte_size": -1,
                    "output_path": "x",
                },
            )


# ----------------------------------------------------------------------
# search_result
# ----------------------------------------------------------------------


class TestSearchResultSchema:
    def test_valid_payload_passes(self) -> None:
        validate_manifest(
            "search_result",
            {
                "n_sources_ok": 2,
                "n_sources_errored": 1,
                "n_items_total": 7,
                "n_items_deduplicated": 5,
                "per_source_status": [
                    {
                        "source": "arxiv",
                        "method": "real",
                        "n_items": 3,
                        "total_results": 10,
                    },
                    {
                        "source": "broken",
                        "method": "real_error",
                        "n_items": 0,
                        "total_results": 0,
                    },
                ],
            },
        )

    def test_unknown_method_rejected(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "search_result",
                {
                    "n_sources_ok": 1,
                    "n_sources_errored": 0,
                    "n_items_total": 0,
                    "n_items_deduplicated": 0,
                    "per_source_status": [
                        {
                            "source": "x",
                            "method": "fake",
                            "n_items": 0,
                            "total_results": 0,
                        }
                    ],
                },
            )


# ----------------------------------------------------------------------
# unknown manifest
# ----------------------------------------------------------------------


class TestValidateManifestUnknownName:
    def test_raises_key_error_for_unknown(self) -> None:
        with pytest.raises(KeyError):
            validate_manifest("does_not_exist", {})
