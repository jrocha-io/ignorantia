"""Unit tests for :class:`JsonWriter`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from ignorantia.infrastructure.persistence.json_writer import JsonWriter


def _valid_audit_result() -> dict[str, object]:
    return {
        "timestamp_iso8601": "2026-05-07T12:00:00Z",
        "action": "search.run",
        "manifest_size": 1,
    }


class TestWriteJson:
    def test_writes_valid_payload_and_returns_byte_count(self, tmp_path: Path) -> None:
        target = tmp_path / "audit.json"
        n_bytes = JsonWriter().write_json(
            _valid_audit_result(), schema_name="audit_result", path=target
        )
        assert target.is_file()
        assert n_bytes == target.stat().st_size
        body = json.loads(target.read_text(encoding="utf-8"))
        assert body["action"] == "search.run"

    def test_creates_parent_dir_if_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "audit.json"
        JsonWriter().write_json(_valid_audit_result(), schema_name="audit_result", path=target)
        assert target.is_file()

    def test_pretty_indent_is_supported(self, tmp_path: Path) -> None:
        target = tmp_path / "audit.json"
        JsonWriter().write_json(
            _valid_audit_result(), schema_name="audit_result", path=target, indent=2
        )
        text = target.read_text(encoding="utf-8")
        assert "\n  " in text  # indented lines


class TestWriteJsonValidation:
    def test_invalid_payload_raises_validation_error(self, tmp_path: Path) -> None:
        bad = {"timestamp_iso8601": "t", "action": "x"}  # missing manifest_size
        with pytest.raises(ValidationError):
            JsonWriter().write_json(bad, schema_name="audit_result", path=tmp_path / "x.json")

    def test_invalid_payload_does_not_create_file(self, tmp_path: Path) -> None:
        target = tmp_path / "x.json"
        with pytest.raises(ValidationError):
            JsonWriter().write_json({"action": "x"}, schema_name="audit_result", path=target)
        assert not target.exists()

    def test_unknown_schema_name_raises_key_error(self, tmp_path: Path) -> None:
        with pytest.raises(KeyError):
            JsonWriter().write_json({}, schema_name="not_a_schema", path=tmp_path / "x.json")


class TestAtomicReplace:
    def test_existing_target_is_replaced_atomically(self, tmp_path: Path) -> None:
        target = tmp_path / "audit.json"
        target.write_text("PREVIOUS", encoding="utf-8")
        JsonWriter().write_json(_valid_audit_result(), schema_name="audit_result", path=target)
        body = json.loads(target.read_text(encoding="utf-8"))
        assert body["action"] == "search.run"

    def test_no_temp_files_left_behind_on_success(self, tmp_path: Path) -> None:
        target = tmp_path / "audit.json"
        JsonWriter().write_json(_valid_audit_result(), schema_name="audit_result", path=target)
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".audit")]
        assert leftovers == []

    def test_validation_error_does_not_leave_temp_file(self, tmp_path: Path) -> None:
        # Validation runs before the temp file is opened, so nothing
        # should land on disk.
        bad = {"action": "x"}  # missing required fields
        with pytest.raises(ValidationError):
            JsonWriter().write_json(bad, schema_name="audit_result", path=tmp_path / "x.json")
        leftovers = list(tmp_path.iterdir())
        assert leftovers == []
