"""Unit tests for the CLI composition root."""

from __future__ import annotations

import re

from click.testing import CliRunner

from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.interface.cli.main import build_audit_use_case, cli


class TestCliGroup:
    def test_help_lists_subcommands(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # Help output names every registered subcommand.
        assert "audit" in result.output

    def test_short_help_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["-h"])
        assert result.exit_code == 0
        assert "audit" in result.output

    def test_version_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Click prints "<prog> <version>" — version is sourced from
        # the installed package, so we just assert it parses.
        assert re.match(r"^cli \S+", result.output)


class TestCompositionRoot:
    def test_build_audit_use_case_returns_real_instance(self) -> None:
        use_case = build_audit_use_case()
        assert isinstance(use_case, RunAuditUseCase)

    def test_build_audit_use_case_starts_with_empty_manifest(self) -> None:
        use_case = build_audit_use_case()
        assert len(use_case.manifest) == 0

    def test_build_audit_use_case_is_a_factory_not_a_singleton(self) -> None:
        # Two calls produce two independent use cases — composition
        # root is intentionally a factory so each invocation gets a
        # fresh manifest.
        first = build_audit_use_case()
        second = build_audit_use_case()
        assert first is not second
