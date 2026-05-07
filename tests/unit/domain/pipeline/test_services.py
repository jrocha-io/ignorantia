"""Unit tests for :class:`PipelineExecutor`.

The executor iterates a registry of :class:`PipelineStep` instances
in order, calls each step's ``fn``, and aggregates the per-step
results into a :class:`PipelineResult`. Failures in one step do not
stop the executor — the next step still runs.

Time injection (issue #13): the constructor takes a ``clock``
callable and the executor stamps both ``started_at_iso8601`` and
``finished_at_iso8601`` from it. Tests pin a sequence of frozen
values to exercise both timestamps deterministically.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from ignorantia.domain.pipeline.entities import PipelineResult
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)


def _step(
    name: str,
    *,
    status: StepStatus = StepStatus.OK,
    artifact: str | None = None,
    raises: BaseException | None = None,
) -> PipelineStep:
    def _fn() -> StepResult:
        if raises is not None:
            raise raises
        return StepResult(name=name, status=status, artifact=artifact)

    return PipelineStep(name=name, label=name.upper(), fn=_fn)


def _clock_sequence(values: Iterable[str]):
    iterator = iter(values)

    def _clock() -> str:
        return next(iterator)

    return _clock


@pytest.fixture
def executor() -> PipelineExecutor:
    return PipelineExecutor(clock=_clock_sequence(["2026-05-07T12:00:00Z", "2026-05-07T12:00:05Z"]))


class TestExecutorReturnsResult:
    def test_returns_pipeline_result(self, executor: PipelineExecutor) -> None:
        result = executor.run([_step("a"), _step("b")])
        assert isinstance(result, PipelineResult)

    def test_steps_appear_in_execution_order(self, executor: PipelineExecutor) -> None:
        result = executor.run([_step("a"), _step("b"), _step("c")])
        assert tuple(s.name for s in result.steps) == ("a", "b", "c")

    def test_clock_provides_started_and_finished(self, executor: PipelineExecutor) -> None:
        result = executor.run([_step("a")])
        assert result.started_at_iso8601 == "2026-05-07T12:00:00Z"
        assert result.finished_at_iso8601 == "2026-05-07T12:00:05Z"


class TestExecutorAggregations:
    def test_counts_each_status(self, executor: PipelineExecutor) -> None:
        result = executor.run(
            [
                _step("a", status=StepStatus.OK),
                _step("b", status=StepStatus.SKIPPED),
                _step("c", status=StepStatus.ERROR),
            ]
        )
        assert result.n_ok == 1
        assert result.n_skipped == 1
        assert result.n_errors == 1

    def test_final_artifacts_are_collected(self, executor: PipelineExecutor) -> None:
        result = executor.run(
            [
                _step("a", artifact="out/a.html"),
                _step("b", artifact="out/b.docx"),
            ]
        )
        assert result.final_artifacts == ("out/a.html", "out/b.docx")


class TestExecutorErrorHandling:
    def test_failing_step_does_not_stop_pipeline(self) -> None:
        executor = PipelineExecutor(clock=_clock_sequence(["t1", "t2"]))
        result = executor.run(
            [
                _step("a"),
                _step("b", raises=RuntimeError("boom")),
                _step("c"),
            ]
        )
        # All three steps appear in the result.
        assert tuple(s.name for s in result.steps) == ("a", "b", "c")
        # The failing step has ERROR status.
        b_result = next(s for s in result.steps if s.name == "b")
        assert b_result.status is StepStatus.ERROR
        # Subsequent step still ran.
        c_result = next(s for s in result.steps if s.name == "c")
        assert c_result.status is StepStatus.OK

    def test_failing_step_carries_exception_message(self) -> None:
        executor = PipelineExecutor(clock=_clock_sequence(["t1", "t2"]))
        result = executor.run([_step("b", raises=RuntimeError("boom"))])
        b_result = result.steps[0]
        assert "boom" in b_result.message

    def test_step_returning_non_step_result_marks_error(self) -> None:
        # Defensive: if a step's fn returns the wrong type, the
        # executor reports it as ERROR rather than crashing the run.
        def _bad_fn() -> StepResult:
            return "not a result"  # type: ignore[return-value]

        bad_step = PipelineStep(name="bad", label="BAD", fn=_bad_fn)
        executor = PipelineExecutor(clock=_clock_sequence(["t1", "t2"]))
        result = executor.run([bad_step])
        assert result.steps[0].status is StepStatus.ERROR
