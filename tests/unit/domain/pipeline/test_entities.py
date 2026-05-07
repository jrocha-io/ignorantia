"""Unit tests for :class:`PipelineResult`.

The aggregate captures a complete pipeline run: when it started, when
it finished, every step's :class:`StepResult` in execution order, and
computed signals (``n_ok``, ``n_skipped``, ``n_errors``,
``final_artifacts``) so downstream tooling does not re-derive them.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.pipeline.entities import PipelineResult
from ignorantia.domain.pipeline.value_objects import StepResult, StepStatus


def _r(name: str, status: StepStatus, artifact: str | None = None) -> StepResult:
    return StepResult(name=name, status=status, artifact=artifact)


class TestPipelineResultConstruction:
    def test_empty_pipeline(self) -> None:
        result = PipelineResult(
            started_at_iso8601="2026-05-07T12:00:00Z",
            finished_at_iso8601="2026-05-07T12:00:01Z",
            steps=(),
        )
        assert result.steps == ()
        assert result.n_ok == 0
        assert result.n_skipped == 0
        assert result.n_errors == 0
        assert result.final_artifacts == ()


class TestPipelineResultInvariants:
    def test_started_at_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="started_at"):
            PipelineResult(
                started_at_iso8601="",
                finished_at_iso8601="2026-05-07T12:00:01Z",
                steps=(),
            )

    def test_finished_at_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="finished_at"):
            PipelineResult(
                started_at_iso8601="2026-05-07T12:00:00Z",
                finished_at_iso8601="",
                steps=(),
            )


class TestPipelineResultAggregations:
    def test_counts_each_status(self) -> None:
        result = PipelineResult(
            started_at_iso8601="t",
            finished_at_iso8601="t",
            steps=(
                _r("a", StepStatus.OK),
                _r("b", StepStatus.OK),
                _r("c", StepStatus.SKIPPED),
                _r("d", StepStatus.ERROR),
            ),
        )
        assert result.n_ok == 2
        assert result.n_skipped == 1
        assert result.n_errors == 1

    def test_final_artifacts_only_from_ok_steps(self) -> None:
        result = PipelineResult(
            started_at_iso8601="t",
            finished_at_iso8601="t",
            steps=(
                _r("a", StepStatus.OK, artifact="out/a.html"),
                _r("b", StepStatus.OK, artifact=None),  # OK but no artefact
                _r("c", StepStatus.SKIPPED, artifact="out/c.html"),  # ignored
                _r("d", StepStatus.ERROR, artifact="out/d.html"),  # ignored
                _r("e", StepStatus.OK, artifact="out/e.html"),
            ),
        )
        assert result.final_artifacts == ("out/a.html", "out/e.html")

    def test_is_successful_when_no_errors(self) -> None:
        result = PipelineResult(
            started_at_iso8601="t",
            finished_at_iso8601="t",
            steps=(
                _r("a", StepStatus.OK),
                _r("b", StepStatus.SKIPPED),
            ),
        )
        assert result.is_successful is True

    def test_is_not_successful_when_any_step_errored(self) -> None:
        result = PipelineResult(
            started_at_iso8601="t",
            finished_at_iso8601="t",
            steps=(
                _r("a", StepStatus.OK),
                _r("b", StepStatus.ERROR),
            ),
        )
        assert result.is_successful is False
