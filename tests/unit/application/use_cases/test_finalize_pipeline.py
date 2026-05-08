"""Unit tests for :class:`FinalizePipelineUseCase`.

The use case is exercised against a real :class:`PipelineExecutor`
wired with a frozen-sequence clock. Step callables are stubs — the
test pins how the use case *composes* the executor and converts its
output to a DTO, not the executor's internals (those are covered in
``tests/unit/domain/pipeline/``).
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from ignorantia.application.dtos import (
    FinalizePipelineCommand,
    FinalizePipelineResult,
    StepResultDto,
)
from ignorantia.application.use_cases.finalize_pipeline import FinalizePipelineUseCase
from ignorantia.domain.pipeline.entities import PipelineResult
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)


def _clock_sequence(values: Iterable[str]):
    iterator = iter(values)

    def _clock() -> str:
        return next(iterator)

    return _clock


def _step(
    name: str,
    *,
    status: StepStatus = StepStatus.OK,
    artifact: str | None = None,
) -> PipelineStep:
    def _fn() -> StepResult:
        return StepResult(name=name, status=status, artifact=artifact)

    return PipelineStep(name=name, label=name.upper(), fn=_fn)


@pytest.fixture
def executor() -> PipelineExecutor:
    return PipelineExecutor(clock=_clock_sequence(["2026-05-07T12:00:00Z", "2026-05-07T12:00:05Z"]))


class TestFinalizePipelineUseCaseHappyPath:
    def test_execute_returns_finalize_pipeline_result(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(
            executor=executor,
            steps=[_step("a"), _step("b")],
        )
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert isinstance(result, FinalizePipelineResult)

    def test_step_dtos_appear_in_execution_order(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(
            executor=executor,
            steps=[_step("a"), _step("b"), _step("c")],
        )
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert tuple(s.name for s in result.steps) == ("a", "b", "c")

    def test_step_status_is_serialised_as_string(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(
            executor=executor,
            steps=[
                _step("a", status=StepStatus.OK),
                _step("b", status=StepStatus.SKIPPED),
                _step("c", status=StepStatus.ERROR),
            ],
        )
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert all(isinstance(s.status, str) for s in result.steps)
        assert {s.status for s in result.steps} == {"ok", "skipped", "error"}

    def test_aggregations_carry_through(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(
            executor=executor,
            steps=[
                _step("a", status=StepStatus.OK, artifact="out/a.html"),
                _step("b", status=StepStatus.SKIPPED),
                _step("c", status=StepStatus.ERROR),
                _step("d", status=StepStatus.OK, artifact="out/d.docx"),
            ],
        )
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert result.n_ok == 2
        assert result.n_skipped == 1
        assert result.n_errors == 1
        assert result.final_artifacts == ("out/a.html", "out/d.docx")
        assert result.is_successful is False

    def test_clock_timestamps_propagate(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(executor=executor, steps=[_step("a")])
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert result.started_at_iso8601 == "2026-05-07T12:00:00Z"
        assert result.finished_at_iso8601 == "2026-05-07T12:00:05Z"

    def test_is_successful_when_all_ok_or_skipped(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(
            executor=executor,
            steps=[
                _step("a", status=StepStatus.OK),
                _step("b", status=StepStatus.SKIPPED),
            ],
        )
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert result.is_successful is True


class TestFinalizePipelineUseCaseEmpty:
    def test_empty_step_registry_returns_empty_result(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(executor=executor, steps=[])
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert result.steps == ()
        assert result.n_ok == 0
        assert result.n_skipped == 0
        assert result.n_errors == 0
        assert result.is_successful is True


class TestFinalizePipelineUseCaseDoesNotLeakDomain:
    def test_execute_returns_dto_not_pipeline_result(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(executor=executor, steps=[_step("a")])
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        assert not isinstance(result, PipelineResult)
        assert isinstance(result, FinalizePipelineResult)

    def test_step_dtos_are_dto_type_not_domain(self, executor: PipelineExecutor) -> None:
        use_case = FinalizePipelineUseCase(executor=executor, steps=[_step("a")])
        result = use_case.execute(FinalizePipelineCommand(actor="cli"))
        for s in result.steps:
            assert isinstance(s, StepResultDto)
            assert not isinstance(s, StepResult)
