"""Unit tests for the ``render`` CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from ignorantia.application.use_cases.render_manuscript import (
    RenderManuscriptUseCase,
)
from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat
from ignorantia.infrastructure.render.citation.apa_formatter import (
    ApaCitationFormatter,
)
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer
from ignorantia.interface.cli.main import (
    build_render_manuscript_use_case,
    build_renderer,
    cli,
)


def _spec() -> dict[str, object]:
    return {
        "title": "A Systematic Review",
        "abstract": "This study evaluates X.",
        "language": "en",
        "keywords": ["evidence", "review"],
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
def input_file(tmp_path: Path) -> Path:
    p = tmp_path / "manuscript.json"
    p.write_text(json.dumps(_spec()), encoding="utf-8")
    return p


@pytest.fixture
def output_file(tmp_path: Path) -> Path:
    return tmp_path / "manuscript.html"


@pytest.fixture
def use_case() -> RenderManuscriptUseCase:
    formatter = ApaCitationFormatter()
    return RenderManuscriptUseCase(
        renderer=HtmlRenderer(formatter=formatter),
        formatter=formatter,
    )


@pytest.fixture
def obj(use_case: RenderManuscriptUseCase) -> dict[str, RenderManuscriptUseCase]:
    return {"render_use_case": use_case}


class TestRenderSubcommandHelp:
    def test_help_documents_all_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.output
        assert "--output" in result.output
        assert "--format" in result.output
        assert "--citation-style" in result.output


class TestRenderSubcommandHappyPath:
    def test_writes_artifact_bytes_to_output_path(
        self,
        input_file: Path,
        output_file: Path,
        obj: dict[str, RenderManuscriptUseCase],
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "render",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ],
            obj=obj,
        )
        assert result.exit_code == 0, result.output
        assert output_file.exists()
        body = output_file.read_bytes()
        assert b"<!DOCTYPE html>" in body
        assert b"A Systematic Review" in body

    def test_emits_summary_json(
        self,
        input_file: Path,
        output_file: Path,
        obj: dict[str, RenderManuscriptUseCase],
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "render",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ],
            obj=obj,
        )
        parsed = json.loads(result.output)
        assert parsed["output_format"] == "html"
        assert parsed["byte_size"] == output_file.stat().st_size
        assert parsed["output_path"].endswith("manuscript.html")


class TestRenderSubcommandFormatRouting:
    def test_format_choice_includes_all_output_formats(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--help"])
        for fmt in OutputFormat:
            assert fmt.value in result.output

    def test_citation_style_choice_includes_all_styles(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--help"])
        for style in CitationStyle:
            assert style.value in result.output

    def test_unknown_format_rejected(self, input_file: Path, output_file: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "render",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
                "--format",
                "epub",
            ],
        )
        assert result.exit_code != 0


class TestRenderSubcommandInputValidation:
    def test_missing_input_path_rejected(self, output_file: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["render", "--input", "/no/such/file.json", "--output", str(output_file)],
        )
        assert result.exit_code != 0

    def test_non_json_input_rejected(self, tmp_path: Path, output_file: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--input", str(bad), "--output", str(output_file)])
        assert result.exit_code != 0
        assert "--input" in result.output

    def test_non_object_json_rejected(self, tmp_path: Path, output_file: Path) -> None:
        scalar = tmp_path / "scalar.json"
        scalar.write_text('"just a string"', encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["render", "--input", str(scalar), "--output", str(output_file)],
        )
        assert result.exit_code != 0

    def test_missing_title_in_spec_rejected(self, tmp_path: Path, output_file: Path) -> None:
        bad_spec = tmp_path / "no-title.json"
        bad_spec.write_text(json.dumps({"abstract": "x"}), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["render", "--input", str(bad_spec), "--output", str(output_file)],
        )
        assert result.exit_code != 0
        assert "title" in result.output.lower()


class TestRenderCompositionRoot:
    def test_build_renderer_routes_html(self) -> None:
        formatter = ApaCitationFormatter()
        renderer = build_renderer(OutputFormat.HTML, formatter)
        assert renderer.output_format is OutputFormat.HTML

    def test_build_renderer_routes_latex(self) -> None:
        formatter = ApaCitationFormatter()
        renderer = build_renderer(OutputFormat.LATEX, formatter)
        assert renderer.output_format is OutputFormat.LATEX

    def test_build_render_manuscript_use_case_returns_real_instance(self) -> None:
        use_case = build_render_manuscript_use_case(OutputFormat.HTML, CitationStyle.APA)
        assert isinstance(use_case, RenderManuscriptUseCase)


class TestRenderEndToEndWithDefaultWiring:
    def test_default_wiring_renders_to_html(self, input_file: Path, output_file: Path) -> None:
        # No injected use case — exercises build_render_manuscript_use_case
        # end-to-end with the real renderer + formatter pair.
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "render",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert output_file.read_bytes().startswith(b"<!DOCTYPE html>")
