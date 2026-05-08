"""Value objects for the pipeline bounded context.

The pipeline domain is the v3 form of v2's ``PIPELINE_STEPS`` registry
(E10, ``scripts/pipeline_finalize.py``). The executor iterates a tuple
of :class:`PipelineStep` instances; each step's callable returns a
:class:`StepResult` with one of the three :class:`StepStatus` outcomes.

Pinned wire formats are load-bearing: ``pipeline_summary.json`` round-
trips these values, so renaming an enum member or its ``.value`` is a
breaking change for downstream tooling.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class StepStatus(str, Enum):
    """Outcome of a single pipeline step."""

    OK = "ok"
    """Step ran successfully and (optionally) produced an artefact."""

    SKIPPED = "skipped"
    """Step was deliberately skipped (e.g. ``--skip-pdf`` flag)."""

    ERROR = "error"
    """Step raised an exception or returned an error indicator."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"ok"``)."""
        return self.value


@dataclass(frozen=True, slots=True)
class StepResult:
    """Outcome of running a single :class:`PipelineStep`.

    Attributes:
        name: The step's stable identifier (matches
            :attr:`PipelineStep.name`).
        status: One of the three :class:`StepStatus` outcomes.
        message: Free-text explanation, especially useful for
            ``ERROR`` and ``SKIPPED`` outcomes.
        artifact: Filesystem path of the artefact the step produced,
            when applicable. ``None`` for steps that do not produce
            artefacts (analysis-only steps).
    """

    name: str
    status: StepStatus
    message: str = ""
    artifact: str | None = None

    def __post_init__(self) -> None:
        """Empty step names break aggregation in :class:`PipelineResult`."""
        if not self.name:
            raise ValueError("StepResult.name must be a non-empty string")


@dataclass(frozen=True, slots=True)
class PipelineStep:
    """One entry in the pipeline executor's registry.

    The registry pattern (Open/Closed) is preserved verbatim from
    v2.23.0 / E10: adding a new step means appending one
    :class:`PipelineStep` to the registry tuple — no edits to the
    executor body.

    Attributes:
        name: Stable step identifier used in result output.
        label: Human-readable label shown in console progress lines.
        fn: Zero-argument callable that runs the step. Step inputs
            (paths, config) are bound by the caller via
            :func:`functools.partial` or closures, keeping this
            domain object free of infrastructure concerns.
    """

    name: str
    label: str
    fn: Callable[[], StepResult]

    def __post_init__(self) -> None:
        """Empty identifiers break registry lookup and progress output."""
        if not self.name:
            raise ValueError("PipelineStep.name must be a non-empty string")
        if not self.label:
            raise ValueError("PipelineStep.label must be a non-empty string")
