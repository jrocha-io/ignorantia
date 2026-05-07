"""Unit tests for the ``finalize`` CLI subcommand."""

from __future__ import annotations

import json
from collections.abc import Iterable

import pytest
from click.testing import CliRunner

from ignorantia.application.use_cases.finalize_pipeline import (
    FinalizePipelineUseCase,
)
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)
from ignorantia.interface.cli.main import (
    build_finalize_pipeline_use_case,
    build_pipeline_steps,
    cli,
)


def _clock_sequence(values: Iterable[str]):
    iterator = iter(values)

    def _clock() -> str:
        return next(iterator)

    return _clock


def _step(name: str, status: StepStatus = StepStatus.OK, artifact: str | None = None):
    def _fn() -> StepResult:
        return StepResult(name=name, status=status, artifact=artifact)

    return PipelineStep(name=name, label=name.upper(), fn=_fn)


@pytest.fixture
def use_case() -> FinalizePipelineUseCase:
    return FinalizePipelineUseCase(
        executor=PipelineExecutor(
            clock=_clock_sequence(["2026-05-07T12:00:00Z", "2026-05-07T12:00:05Z"])
        ),
        steps=[
            _step("a", artifact="out/a.html"),
            _step("b", status=StepStatus.SKIPPED),
        ],
    )


@pytest.fixture
def obj(use_case: FinalizePipelineUseCase) -> dict[str, FinalizePipelineUseCase]:
    return {"finalize_use_case": use_case}


class TestFinalizeSubcommandHelp:
    def test_help_is_documented(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize", "--help"])
        assert result.exit_code == 0
        assert "--actor" in result.output


class TestFinalizeSubcommandHappyPath:
    def test_emits_json_with_aggregations(self, obj: dict[str, FinalizePipelineUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize", "--actor", "cli"], obj=obj)
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["started_at_iso8601"] == "2026-05-07T12:00:00Z"
        assert parsed["finished_at_iso8601"] == "2026-05-07T12:00:05Z"
        assert parsed["n_ok"] == 1
        assert parsed["n_skipped"] == 1
        assert parsed["n_errors"] == 0
        assert parsed["is_successful"] is True
        assert parsed["final_artifacts"] == ["out/a.html"]

    def test_steps_appear_in_execution_order(self, obj: dict[str, FinalizePipelineUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize"], obj=obj)
        parsed = json.loads(result.output)
        names = [s["name"] for s in parsed["steps"]]
        assert names == ["a", "b"]

    def test_step_status_is_a_string(self, obj: dict[str, FinalizePipelineUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize"], obj=obj)
        parsed = json.loads(result.output)
        assert all(isinstance(s["status"], str) for s in parsed["steps"])
        assert parsed["steps"][0]["status"] == "ok"
        assert parsed["steps"][1]["status"] == "skipped"


class TestFinalizeCompositionRoot:
    def test_build_pipeline_steps_is_empty_until_infra_lands(self) -> None:
        # Documented contract: until concrete steps are migrated from
        # scripts/pipeline_finalize.py, the registry is intentionally
        # empty. This test fails the day someone forgets to update it.
        assert build_pipeline_steps() == ()

    def test_build_finalize_pipeline_use_case_returns_real_instance(self) -> None:
        use_case = build_finalize_pipeline_use_case()
        assert isinstance(use_case, FinalizePipelineUseCase)

    def test_default_invocation_with_empty_registry_is_successful(self) -> None:
        # Until concrete steps land, the production wiring runs an
        # empty pipeline → 0 errors → is_successful=True.
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["steps"] == []
        assert parsed["n_ok"] == 0
        assert parsed["n_errors"] == 0
        assert parsed["is_successful"] is True
