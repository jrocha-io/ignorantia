"""Unit tests for :func:`build_incremental_html_render_step`."""

from __future__ import annotations

from pathlib import Path

import pytest

from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import StepStatus
from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.infrastructure.pipeline.incremental_render import (
    build_incremental_html_render_step,
)
from ignorantia.infrastructure.render.citation.apa_formatter import (
    ApaCitationFormatter,
)
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer


@pytest.fixture
def manuscript() -> ManuscriptDoc:
    return ManuscriptDoc(
        title="A Tutorial Systematic Review",
        abstract="This study evaluates X.",
        keywords=("evidence", "review"),
        sections=(
            Section(id="intro", title="Introduction", body_md="Body 1."),
            Section(id="methods", title="Methods", body_md="Body 2."),
            Section(id="results", title="Results", body_md="Body 3."),
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


class TestStepMetadata:
    def test_name_and_label(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        assert step.name == "incremental_render_html"
        assert "chunked" in step.label.lower()


class TestStepWritesValidHtml:
    def test_writes_html_artefact(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(tmp_path / "manuscript.html")
        body = (tmp_path / "manuscript.html").read_bytes()
        assert body.startswith(b"<!DOCTYPE html>")
        assert b"</html>" in body[-50:]

    def test_all_sections_present(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        step.fn()
        body = (tmp_path / "manuscript.html").read_text(encoding="utf-8")
        for section in manuscript.sections:
            assert f'<section id="{section.id}">' in body
            assert f"<h2>{section.title}</h2>" in body

    def test_references_section_present_when_refs_exist(
        self, manuscript: ManuscriptDoc, tmp_path: Path
    ) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        step.fn()
        body = (tmp_path / "manuscript.html").read_text(encoding="utf-8")
        assert '<section class="references">' in body
        assert "Silva" in body  # APA author surname

    def test_references_section_omitted_when_empty(self, tmp_path: Path) -> None:
        bare = ManuscriptDoc(
            title="No Refs",
            abstract="x",
            sections=(Section(id="s", title="S", body_md="x"),),
            references=(),
        )
        step = build_incremental_html_render_step(
            manuscript=bare,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        step.fn()
        body = (tmp_path / "manuscript.html").read_text(encoding="utf-8")
        assert '<section class="references">' not in body


class TestParityWithOneShotRender:
    def test_byte_set_matches_one_shot_render(
        self, manuscript: ManuscriptDoc, tmp_path: Path
    ) -> None:
        # The incremental write must contain the same structural
        # elements as HtmlRenderer.render(doc). Compare by checking
        # both produce the same set of tags / IDs / titles, not
        # byte-equal (whitespace differs by a trailing newline).
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        step.fn()
        incremental = (tmp_path / "manuscript.html").read_bytes()

        one_shot = HtmlRenderer(formatter=ApaCitationFormatter()).render(manuscript)

        # All section IDs from the one-shot output appear in the
        # incremental output too.
        for section in manuscript.sections:
            tag = f'<section id="{section.id}">'.encode()
            assert tag in one_shot
            assert tag in incremental

        # Title carrier (h1) and references heading match.
        assert b"<h1>A Tutorial Systematic Review</h1>" in incremental
        assert b"<h2>References</h2>" in incremental


class TestEdgeCases:
    def test_creates_output_dir_if_missing(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested"
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=nested,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert (nested / "manuscript.html").is_file()

    def test_custom_filename(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
            filename="article.html",
        )
        result = step.fn()
        assert result.artifact == str(tmp_path / "article.html")
        assert (tmp_path / "article.html").is_file()

    def test_zero_sections_produces_minimal_html(self, tmp_path: Path) -> None:
        empty = ManuscriptDoc(
            title="Empty",
            abstract="",
            sections=(),
            references=(),
        )
        step = build_incremental_html_render_step(
            manuscript=empty,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        body = (tmp_path / "manuscript.html").read_bytes()
        assert b"<!DOCTYPE html>" in body
        assert b"<h1>Empty</h1>" in body
        assert b"</html>" in body[-50:]


class TestStepReportsSectionCount:
    def test_message_carries_section_and_reference_counts(
        self, manuscript: ManuscriptDoc, tmp_path: Path
    ) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        result = step.fn()
        assert "3 section" in result.message
        assert "1 reference" in result.message


class TestStepUnderExecutor:
    def test_executor_runs_and_collects_artifact(
        self, manuscript: ManuscriptDoc, tmp_path: Path
    ) -> None:
        step = build_incremental_html_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=ApaCitationFormatter(),
        )
        clock_values = iter(["t1", "t2"])
        executor = PipelineExecutor(clock=lambda: next(clock_values))
        result = executor.run([step])
        assert result.is_successful
        assert result.n_ok == 1
        assert result.final_artifacts == (str(tmp_path / "manuscript.html"),)
