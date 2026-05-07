"""Unit tests for pipeline value objects.

Two enums + two frozen dataclasses pinned by these tests:

* :class:`StepStatus` — outcome of a single pipeline step
  (``OK / SKIPPED / ERROR``).
* :class:`StepResult` — the artefact + message a step produces.
* :class:`PipelineStep` — one entry in the executor's registry
  (``name``, ``label``, the callable that runs it).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)


class TestStepStatus:
    def test_canonical_wire_values(self) -> None:
        assert StepStatus.OK.value == "ok"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.ERROR.value == "error"

    def test_str_returns_wire_value(self) -> None:
        assert str(StepStatus.OK) == "ok"


class TestStepResultConstruction:
    def test_minimum_fields(self) -> None:
        r = StepResult(name="cross_tab", status=StepStatus.OK)
        assert r.name == "cross_tab"
        assert r.status is StepStatus.OK
        assert r.message == ""
        assert r.artifact is None

    def test_with_artifact_and_message(self) -> None:
        r = StepResult(
            name="render_html",
            status=StepStatus.OK,
            message="Rendered 12 sections",
            artifact="output/manuscript.html",
        )
        assert r.message.startswith("Rendered")
        assert r.artifact == "output/manuscript.html"


class TestStepResultInvariants:
    def test_name_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="name"):
            StepResult(name="", status=StepStatus.OK)


class TestStepResultImmutability:
    def test_is_frozen(self) -> None:
        r = StepResult(name="x", status=StepStatus.OK)
        with pytest.raises(FrozenInstanceError):
            r.name = "y"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        assert StepResult.__slots__
        r = StepResult(name="x", status=StepStatus.OK)
        assert not hasattr(r, "__dict__")


class TestPipelineStepConstruction:
    def test_minimum_fields(self) -> None:
        def _noop() -> StepResult:
            return StepResult(name="x", status=StepStatus.OK)

        step = PipelineStep(name="x", label="X", fn=_noop)
        assert step.name == "x"
        assert step.label == "X"
        assert step.fn is _noop


class TestPipelineStepInvariants:
    def test_name_must_be_non_empty(self) -> None:
        def _noop() -> StepResult:
            return StepResult(name="x", status=StepStatus.OK)

        with pytest.raises(ValueError, match="name"):
            PipelineStep(name="", label="X", fn=_noop)

    def test_label_must_be_non_empty(self) -> None:
        def _noop() -> StepResult:
            return StepResult(name="x", status=StepStatus.OK)

        with pytest.raises(ValueError, match="label"):
            PipelineStep(name="x", label="", fn=_noop)
