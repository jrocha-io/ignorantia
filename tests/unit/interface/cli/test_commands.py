"""Unit tests for the CLI subcommands."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.domain.audit.services import ManifestService
from ignorantia.interface.cli.main import cli


def _frozen_clock(value: str = "2026-05-07T12:00:00Z"):
    def _clock() -> str:
        return value

    return _clock


@pytest.fixture
def use_case() -> RunAuditUseCase:
    """Pre-wired use case with a frozen clock for deterministic output."""
    return RunAuditUseCase(service=ManifestService(clock=_frozen_clock()))


@pytest.fixture
def obj(use_case: RunAuditUseCase) -> dict[str, RunAuditUseCase]:
    return {"audit_use_case": use_case}


class TestAuditSubcommand:
    def test_help_documents_all_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0
        assert "--action" in result.output
        assert "--actor" in result.output
        assert "--payload" in result.output

    def test_basic_invocation_prints_json_result(self, obj: dict[str, RunAuditUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["audit", "--action", "search.run", "--actor", "cli"],
            obj=obj,
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["action"] == "search.run"
        assert parsed["timestamp_iso8601"] == "2026-05-07T12:00:00Z"
        assert parsed["manifest_size"] == 1

    def test_action_is_required(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "--actor", "cli"])
        assert result.exit_code != 0
        assert "--action" in result.output.lower()

    def test_actor_defaults_to_cli(
        self, obj: dict[str, RunAuditUseCase], use_case: RunAuditUseCase
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "--action", "x"], obj=obj)
        assert result.exit_code == 0
        assert use_case.manifest.entries[0].actor == "cli"

    def test_payload_defaults_to_empty_dict(
        self, obj: dict[str, RunAuditUseCase], use_case: RunAuditUseCase
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "--action", "x"], obj=obj)
        assert result.exit_code == 0
        assert use_case.manifest.entries[0].payload == {}

    def test_payload_propagates_through_to_entry(
        self, obj: dict[str, RunAuditUseCase], use_case: RunAuditUseCase
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "--action",
                "search.run",
                "--payload",
                '{"query_hash": "abc", "n_results": 7}',
            ],
            obj=obj,
        )
        assert result.exit_code == 0
        last = use_case.manifest.entries[-1]
        assert last.payload == {"query_hash": "abc", "n_results": 7}


class TestAuditSubcommandPayloadValidation:
    def test_invalid_json_rejected_with_helpful_message(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["audit", "--action", "x", "--payload", "{not-json"],
        )
        assert result.exit_code != 0
        assert "--payload" in result.output

    def test_non_object_payload_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["audit", "--action", "x", "--payload", "[1, 2, 3]"],
        )
        assert result.exit_code != 0
        assert "JSON object" in result.output


class TestCompositionInjection:
    def test_use_case_from_obj_takes_precedence_over_factory(
        self, obj: dict[str, RunAuditUseCase], use_case: RunAuditUseCase
    ) -> None:
        # Two invocations on the same obj see the same manifest —
        # confirms the injected use case is reused.
        runner = CliRunner()
        runner.invoke(cli, ["audit", "--action", "a"], obj=obj)
        runner.invoke(cli, ["audit", "--action", "b"], obj=obj)
        actions = tuple(e.action for e in use_case.manifest.entries)
        assert actions == ("a", "b")

    def test_default_obj_builds_fresh_use_case(self) -> None:
        # Without injection the CLI builds its own use case via the
        # composition root. Two invocations get different manifests
        # because each Click invocation is a fresh process tree —
        # ``obj`` is initialised by the group on every run.
        runner = CliRunner()
        result_a = runner.invoke(cli, ["audit", "--action", "a"])
        result_b = runner.invoke(cli, ["audit", "--action", "b"])
        assert result_a.exit_code == 0
        assert result_b.exit_code == 0
        a = json.loads(result_a.output)
        b = json.loads(result_b.output)
        assert a["manifest_size"] == 1
        assert b["manifest_size"] == 1
