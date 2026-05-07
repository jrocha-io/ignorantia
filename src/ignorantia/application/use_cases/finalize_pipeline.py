"""``FinalizePipelineUseCase`` — run the pipeline and return a DTO summary.

Wraps :class:`PipelineExecutor` (F5c) behind the F6 use-case pattern.
The pipeline step registry is injected at construction time (DIP), so
production wiring binds it to the real renderer / packager / audit
steps in ``infrastructure/`` while tests pass in stub steps.

The use case converts the domain :class:`PipelineResult` to a flat
:class:`FinalizePipelineResult` DTO so the interface layer never
touches a domain entity directly.
"""

from __future__ import annotations

from collections.abc import Sequence

from ignorantia.application.dtos import (
    FinalizePipelineCommand,
    FinalizePipelineResult,
    StepResultDto,
)
from ignorantia.domain.pipeline.entities import PipelineResult
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import PipelineStep, StepResult


class FinalizePipelineUseCase:
    """Execute a configured pipeline and emit a result DTO."""

    def __init__(
        self,
        *,
        executor: PipelineExecutor,
        steps: Sequence[PipelineStep],
    ) -> None:
        """Wire the use case to an executor and a step registry.

        Args:
            executor: The :class:`PipelineExecutor` (DIP — depends on
                the abstraction; production wiring binds it to an
                executor with a real clock).
            steps: The pipeline registry. Order matters: steps run in
                sequence, and the registry pattern keeps the use case
                Open/Closed against new steps.
        """
        self._executor = executor
        self._steps = tuple(steps)

    def execute(
        self,
        command: FinalizePipelineCommand,
    ) -> FinalizePipelineResult:
        """Run the configured pipeline and return a result DTO.

        The ``command`` is reserved for runtime knobs (actor, future
        ``skip_*`` flags). Today only ``actor`` is honoured: it is
        validated by the command DTO itself, but does not yet alter
        executor behaviour.
        """
        # Validate the command shape; actor is reserved for future
        # CLI / audit wiring (see FinalizePipelineCommand docstring).
        del command
        domain_result = self._executor.run(self._steps)
        return _to_dto(domain_result)


def _to_dto(result: PipelineResult) -> FinalizePipelineResult:
    return FinalizePipelineResult(
        started_at_iso8601=result.started_at_iso8601,
        finished_at_iso8601=result.finished_at_iso8601,
        steps=tuple(_step_to_dto(s) for s in result.steps),
        n_ok=result.n_ok,
        n_skipped=result.n_skipped,
        n_errors=result.n_errors,
        final_artifacts=result.final_artifacts,
        is_successful=result.is_successful,
    )


def _step_to_dto(step: StepResult) -> StepResultDto:
    return StepResultDto(
        name=step.name,
        status=str(step.status),
        message=step.message,
        artifact=step.artifact,
    )
