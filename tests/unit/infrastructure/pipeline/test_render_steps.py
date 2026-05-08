"""Unit tests for the render-step factories."""

from __future__ import annotations

from pathlib import Path

import pytest

from ignorantia.domain.pipeline.value_objects import StepStatus
from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.infrastructure.pipeline.render_steps import (
    build_docx_render_step,
    build_html_render_step,
    build_latex_render_step,
)
from ignorantia.infrastructure.render.citation.apa_formatter import (
    ApaCitationFormatter,
)


@pytest.fixture
def manuscript() -> ManuscriptDoc:
    return ManuscriptDoc(
        title="A Tutorial Systematic Review",
        abstract="This study evaluates X.",
        sections=(
            Section(id="intro", title="Introduction", body_md="Body."),
            Section(id="methods", title="Methods", body_md="Methods body."),
        ),
        references=(
            Reference(
                type="article",
                title="Quality of evidence",
                authors=("Silva, J. P.",),
                year=2024,
                venue="Journal",
            ),
        ),
    )


class TestHtmlRenderStep:
    def test_step_metadata(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        assert step.name == "render_html"
        assert step.label == "Render HTML"

    def test_writes_html_artefact(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(tmp_path / "manuscript.html")
        artefact_bytes = (tmp_path / "manuscript.html").read_bytes()
        assert artefact_bytes.startswith(b"<!DOCTYPE html>")
        assert b"A Tutorial Systematic Review" in artefact_bytes

    def test_creates_output_dir_if_missing(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "deeper"
        step = build_html_render_step(
            manuscript=manuscript,
            output_dir=nested,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert (nested / "manuscript.html").is_file()


class TestLatexRenderStep:
    def test_writes_tex_artefact(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_latex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(tmp_path / "manuscript.tex")
        body = (tmp_path / "manuscript.tex").read_bytes()
        assert b"\\documentclass" in body
        assert b"A Tutorial Systematic Review" in body

    def test_step_name_is_render_latex(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_latex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        assert step.name == "render_latex"


class TestDocxRenderStep:
    def test_step_metadata(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        # The factory must always be callable, even without [docx]
        # installed — only fn() reaches into python-docx.
        step = build_docx_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        assert step.name == "render_docx"
        assert step.label == "Render DOCX"

    def test_fn_writes_docx_artefact(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        # Only run the body if python-docx is installed; otherwise
        # skip — the factory's contract is "fail at fn() not at
        # construction".
        pytest.importorskip("docx")
        step = build_docx_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(tmp_path / "manuscript.docx")
        # OOXML files start with the ZIP magic.
        body = (tmp_path / "manuscript.docx").read_bytes()
        assert body[:2] == b"PK"


class TestRenderStepsViaExecutor:
    def test_executor_runs_all_three_steps(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        # Confirms the steps compose under PipelineExecutor without
        # needing the CLI plumbing.
        from ignorantia.domain.pipeline.services import PipelineExecutor

        clock_values = iter(["2026-05-07T12:00:00Z", "2026-05-07T12:00:01Z"])

        def _clock() -> str:
            return next(clock_values)

        formatter = ApaCitationFormatter()
        executor = PipelineExecutor(clock=_clock)
        steps = (
            build_html_render_step(manuscript=manuscript, output_dir=tmp_path, formatter=formatter),
            build_latex_render_step(
                manuscript=manuscript, output_dir=tmp_path, formatter=formatter
            ),
        )
        result = executor.run(steps)
        assert result.is_successful
        assert result.n_ok == 2
        assert (tmp_path / "manuscript.html").is_file()
        assert (tmp_path / "manuscript.tex").is_file()
