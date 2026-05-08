"""Entities for the pipeline bounded context.

:class:`PipelineResult` aggregates the per-step outcomes of a
pipeline run with the timestamps that bracket execution. Computed
properties expose the rollup signals callers care about
(``n_ok``, ``n_skipped``, ``n_errors``, ``final_artifacts``,
``is_successful``) so consumers do not re-derive them from the
``steps`` tuple.
"""

from __future__ import annotations

from dataclasses import dataclass

from ignorantia.domain.pipeline.value_objects import StepResult, StepStatus


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Snapshot of a complete pipeline run.

    Attributes:
        started_at_iso8601: When the executor started running steps.
        finished_at_iso8601: When the executor finished the last step.
        steps: Step results in execution order.
    """

    started_at_iso8601: str
    finished_at_iso8601: str
    steps: tuple[StepResult, ...]

    def __post_init__(self) -> None:
        """Pin both timestamps — replay tooling depends on them."""
        if not self.started_at_iso8601:
            raise ValueError("PipelineResult.started_at_iso8601 must be a non-empty string")
        if not self.finished_at_iso8601:
            raise ValueError("PipelineResult.finished_at_iso8601 must be a non-empty string")

    @property
    def n_ok(self) -> int:
        """Number of steps that completed with :attr:`StepStatus.OK`."""
        return sum(1 for s in self.steps if s.status is StepStatus.OK)

    @property
    def n_skipped(self) -> int:
        """Number of steps that returned :attr:`StepStatus.SKIPPED`."""
        return sum(1 for s in self.steps if s.status is StepStatus.SKIPPED)

    @property
    def n_errors(self) -> int:
        """Number of steps that returned :attr:`StepStatus.ERROR`."""
        return sum(1 for s in self.steps if s.status is StepStatus.ERROR)

    @property
    def final_artifacts(self) -> tuple[str, ...]:
        """Artefact paths produced by ``OK`` steps, in execution order.

        Skipped and errored steps are excluded — even when they
        nominally carry an ``artifact`` value, that artefact may be
        partial or absent on disk and downstream packagers should
        not see it.
        """
        return tuple(s.artifact for s in self.steps if s.status is StepStatus.OK and s.artifact)

    @property
    def is_successful(self) -> bool:
        """``True`` when no step errored. Skipped steps are still successful."""
        return self.n_errors == 0
