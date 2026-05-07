"""Pipeline domain services.

:class:`PipelineExecutor` is the v3 form of v2's ``run_pipeline``
function (``scripts/pipeline_finalize.py``). It iterates a registry
of :class:`PipelineStep` instances in order, calls each step's ``fn``,
and aggregates the per-step results into a :class:`PipelineResult`.

Behavioural contract preserved from v2.23.0 / E10:

* **Failure does not abort the run.** A step that raises an exception
  is reported with :attr:`StepStatus.ERROR` and the executor moves
  on to the next step. The v2 rationale was that downstream artefacts
  (PDF, .docx) are independent of each other — a missing PDF does
  not invalidate the .docx.
* **Defensive return-type check.** If a step's ``fn`` returns
  something other than a :class:`StepResult`, the executor reports
  it as ``ERROR`` rather than letting the wrong type propagate into
  the result aggregate.

Time injection (issue #13): the constructor takes a ``clock``
callable and stamps both ``started_at_iso8601`` (before the first
step) and ``finished_at_iso8601`` (after the last step). Tests pin
a deterministic sequence; production wiring binds the clock to a
real timestamp source in ``infrastructure/``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast

from ignorantia.domain.pipeline.entities import PipelineResult
from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)


class PipelineExecutor:
    """Run a registry of :class:`PipelineStep` instances and aggregate the results."""

    def __init__(self, *, clock: Callable[[], str]) -> None:
        """Wire the executor to a deterministic clock (issue #13)."""
        self._clock = clock

    def run(self, steps: Sequence[PipelineStep]) -> PipelineResult:
        """Execute ``steps`` in order and return the aggregated :class:`PipelineResult`."""
        started_at = self._clock()
        results: list[StepResult] = []
        for step in steps:
            results.append(_run_one(step))
        finished_at = self._clock()
        return PipelineResult(
            started_at_iso8601=started_at,
            finished_at_iso8601=finished_at,
            steps=tuple(results),
        )


def _run_one(step: PipelineStep) -> StepResult:
    """Run a single step, catching exceptions and wrong return types."""
    try:
        outcome = cast(object, step.fn())
    except BaseException as exc:
        return StepResult(
            name=step.name,
            status=StepStatus.ERROR,
            message=f"{type(exc).__name__}: {exc}",
        )
    if not isinstance(outcome, StepResult):
        # Defensive: step.fn is typed as () -> StepResult, but a
        # caller can still construct a PipelineStep over a callable
        # that lies about its return type. Treat the violation as
        # ERROR rather than letting the wrong object propagate. The
        # cast() above keeps the static type system honest while
        # still letting this runtime check run.
        return StepResult(
            name=step.name,
            status=StepStatus.ERROR,
            message=(f"step {step.name!r} returned {type(outcome).__name__}; expected StepResult"),
        )
    return outcome
