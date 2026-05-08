"""Unit tests for :func:`build_bibtex_render_step`."""

from __future__ import annotations

from pathlib import Path

import pytest

from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import StepStatus
from ignorantia.domain.render.entities import ManuscriptDoc, Reference
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import BibTexStyle
from ignorantia.infrastructure.pipeline.bibtex_step import (
    build_bibtex_render_step,
)
from ignorantia.infrastructure.render.citation.bibtex_factory import (
    bibtex_formatter_for,
)


@pytest.fixture
def manuscript() -> ManuscriptDoc:
    return ManuscriptDoc(
        title="Test",
        abstract="x",
        sections=(),
        references=(
            Reference(
                type="article",
                title="Quality of evidence",
                authors=("Silva, J. P.",),
                year=2024,
                venue="J",
            ),
            Reference(
                type="book",
                title="Systematic Reviews",
                authors=("Pereira, A.",),
                year=2023,
                publisher="Press",
            ),
        ),
    )


class TestBuildStep:
    def test_step_metadata(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=bibtex_formatter_for(BibTexStyle.PLAIN),
        )
        assert step.name == "render_bibtex"
        assert "BibTeX" in step.label


class TestStepExecution:
    def test_writes_bibliography_bib(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=bibtex_formatter_for(BibTexStyle.PLAIN),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(tmp_path / "bibliography.bib")
        body = (tmp_path / "bibliography.bib").read_text(encoding="utf-8")
        assert "@article{silva2024quality" in body
        assert "@book{pereira2023" in body

    def test_creates_output_dir(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested"
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=nested,
            formatter=bibtex_formatter_for(BibTexStyle.PLAIN),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        assert (nested / "bibliography.bib").is_file()

    def test_custom_filename(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=bibtex_formatter_for(BibTexStyle.PLAIN),
            filename="refs.bib",
        )
        result = step.fn()
        assert result.artifact == str(tmp_path / "refs.bib")

    def test_message_carries_count_and_style(
        self, manuscript: ManuscriptDoc, tmp_path: Path
    ) -> None:
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=bibtex_formatter_for(BibTexStyle.IEEETRAN),
        )
        result = step.fn()
        assert "2 entry" in result.message
        assert "IEEEtran" in result.message


class TestStepUnderExecutor:
    def test_executor_collects_artifact(self, manuscript: ManuscriptDoc, tmp_path: Path) -> None:
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=bibtex_formatter_for(BibTexStyle.PLAIN),
        )
        clock_values = iter(["t1", "t2"])
        executor = PipelineExecutor(clock=lambda: next(clock_values))
        result = executor.run([step])
        assert result.is_successful
        assert result.final_artifacts == (str(tmp_path / "bibliography.bib"),)


class TestStyleVariants:
    @pytest.mark.parametrize("style", list(BibTexStyle))
    def test_each_style_produces_valid_file(
        self, manuscript: ManuscriptDoc, tmp_path: Path, style: BibTexStyle
    ) -> None:
        step = build_bibtex_render_step(
            manuscript=manuscript,
            output_dir=tmp_path,
            formatter=bibtex_formatter_for(style),
        )
        result = step.fn()
        assert result.status is StepStatus.OK
        body = (tmp_path / "bibliography.bib").read_text(encoding="utf-8")
        assert f"% style: {style.value}" in body
        # Every style emits the article entry — content varies but
        # the @article opener is universal.
        assert body.count("@article{") + body.count("@book{") >= 2
