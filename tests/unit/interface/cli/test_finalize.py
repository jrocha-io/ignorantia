"""Unit tests for the ``finalize`` CLI subcommand."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pytest
from click.testing import CliRunner

from ignorantia.application.use_cases.finalize_pipeline import (
    FinalizePipelineUseCase,
)
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)
from ignorantia.domain.render.entities import ManuscriptDoc
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.interface.cli.main import (
    build_finalize_pipeline_use_case,
    build_pipeline_steps,
    build_render_pipeline_steps,
    build_render_pipeline_use_case,
    cli,
)


def _clock_sequence(values: Iterable[str]):
    iterator = iter(values)

    def _clock() -> str:
        return next(iterator)

    return _clock


def _step(name: str, status: StepStatus = StepStatus.OK, artifact: str | None = None):
    def _fn() -> StepResult:
        return StepResult(name=name, status=status, artifact=artifact)

    return PipelineStep(name=name, label=name.upper(), fn=_fn)


@pytest.fixture
def use_case() -> FinalizePipelineUseCase:
    return FinalizePipelineUseCase(
        executor=PipelineExecutor(
            clock=_clock_sequence(["2026-05-07T12:00:00Z", "2026-05-07T12:00:05Z"])
        ),
        steps=[
            _step("a", artifact="out/a.html"),
            _step("b", status=StepStatus.SKIPPED),
        ],
    )


@pytest.fixture
def obj(use_case: FinalizePipelineUseCase) -> dict[str, FinalizePipelineUseCase]:
    return {"finalize_use_case": use_case}


class TestFinalizeSubcommandHelp:
    def test_help_is_documented(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize", "--help"])
        assert result.exit_code == 0
        assert "--actor" in result.output


class TestFinalizeSubcommandHappyPath:
    def test_emits_json_with_aggregations(self, obj: dict[str, FinalizePipelineUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize", "--actor", "cli"], obj=obj)
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["started_at_iso8601"] == "2026-05-07T12:00:00Z"
        assert parsed["finished_at_iso8601"] == "2026-05-07T12:00:05Z"
        assert parsed["n_ok"] == 1
        assert parsed["n_skipped"] == 1
        assert parsed["n_errors"] == 0
        assert parsed["is_successful"] is True
        assert parsed["final_artifacts"] == ["out/a.html"]

    def test_steps_appear_in_execution_order(self, obj: dict[str, FinalizePipelineUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize"], obj=obj)
        parsed = json.loads(result.output)
        names = [s["name"] for s in parsed["steps"]]
        assert names == ["a", "b"]

    def test_step_status_is_a_string(self, obj: dict[str, FinalizePipelineUseCase]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize"], obj=obj)
        parsed = json.loads(result.output)
        assert all(isinstance(s["status"], str) for s in parsed["steps"])
        assert parsed["steps"][0]["status"] == "ok"
        assert parsed["steps"][1]["status"] == "skipped"


class TestFinalizeCompositionRoot:
    def test_build_pipeline_steps_is_empty_for_no_arg_path(self) -> None:
        # Documented contract: the no-arg overload returns the empty
        # registry. Render mode goes through build_render_pipeline_steps.
        assert build_pipeline_steps() == ()

    def test_build_finalize_pipeline_use_case_returns_real_instance(self) -> None:
        use_case = build_finalize_pipeline_use_case()
        assert isinstance(use_case, FinalizePipelineUseCase)

    def test_default_invocation_with_empty_registry_is_successful(self) -> None:
        # Without --input the production wiring runs an empty pipeline
        # → 0 errors → is_successful=True. This is the smoke-check path.
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["steps"] == []
        assert parsed["n_ok"] == 0
        assert parsed["n_errors"] == 0
        assert parsed["is_successful"] is True


def _spec() -> dict[str, object]:
    return {
        "title": "A Tutorial Systematic Review",
        "abstract": "This study evaluates X.",
        "sections": [
            {"id": "intro", "title": "Introduction", "body_md": "Body."},
        ],
        "references": [
            {
                "type": "article",
                "title": "Quality of evidence",
                "authors": ["Silva, J. P."],
                "year": 2024,
                "venue": "Journal",
            }
        ],
    }


@pytest.fixture
def manuscript_input(tmp_path: Path) -> Path:
    p = tmp_path / "manuscript.json"
    p.write_text(json.dumps(_spec()), encoding="utf-8")
    return p


class TestFinalizeRenderModeCompositionRoot:
    def test_build_render_pipeline_steps_default_includes_html_and_latex(
        self, tmp_path: Path
    ) -> None:
        # DOCX path is gated on the [docx] extra; the registry still
        # registers the step (factory is always callable), so the
        # tuple length is 3.
        manuscript = ManuscriptDoc(title="x", abstract="", sections=(), references=())
        steps = build_render_pipeline_steps(
            manuscript=manuscript,
            output_dir=tmp_path,
            citation_style=CitationStyle.APA,
        )
        names = tuple(s.name for s in steps)
        assert names == ("render_html", "render_latex", "render_docx")

    def test_skip_flags_drop_steps_from_registry(self, tmp_path: Path) -> None:
        manuscript = ManuscriptDoc(title="x", abstract="", sections=(), references=())
        steps = build_render_pipeline_steps(
            manuscript=manuscript,
            output_dir=tmp_path,
            citation_style=CitationStyle.APA,
            skip_latex=True,
            skip_docx=True,
        )
        assert tuple(s.name for s in steps) == ("render_html",)

    def test_build_render_pipeline_use_case_returns_real_instance(self, tmp_path: Path) -> None:
        manuscript = ManuscriptDoc(title="x", abstract="", sections=(), references=())
        use_case = build_render_pipeline_use_case(
            manuscript=manuscript,
            output_dir=tmp_path,
            citation_style=CitationStyle.APA,
        )
        assert isinstance(use_case, FinalizePipelineUseCase)


class TestFinalizeRenderModeCli:
    def test_input_without_output_dir_rejected(self, manuscript_input: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["finalize", "--input", str(manuscript_input)])
        assert result.exit_code != 0
        assert "--output-dir" in result.output

    def test_input_runs_render_pipeline(self, manuscript_input: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "finalize",
                "--input",
                str(manuscript_input),
                "--output-dir",
                str(tmp_path),
                "--skip-docx",  # skip DOCX so test doesn't depend on [docx]
            ],
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        # 2 steps: HTML + LaTeX
        assert parsed["n_ok"] == 2
        assert parsed["n_errors"] == 0
        assert parsed["is_successful"] is True
        assert (tmp_path / "manuscript.html").is_file()
        assert (tmp_path / "manuscript.tex").is_file()

    def test_skip_html_drops_html_step(self, manuscript_input: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "finalize",
                "--input",
                str(manuscript_input),
                "--output-dir",
                str(tmp_path),
                "--skip-html",
                "--skip-docx",
            ],
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        names = [s["name"] for s in parsed["steps"]]
        assert names == ["render_latex"]
        assert not (tmp_path / "manuscript.html").exists()
        assert (tmp_path / "manuscript.tex").is_file()

    def test_citation_style_propagates_to_render_steps(
        self, manuscript_input: Path, tmp_path: Path
    ) -> None:
        # ABNT formatter uses uppercase author surnames in the
        # references list — assert that surfaces in the artefact.
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "finalize",
                "--input",
                str(manuscript_input),
                "--output-dir",
                str(tmp_path),
                "--citation-style",
                "abnt",
                "--skip-latex",
                "--skip-docx",
            ],
        )
        assert result.exit_code == 0, result.output
        body = (tmp_path / "manuscript.html").read_bytes()
        assert b"SILVA" in body  # ABNT uppercases surnames
