"""Unit tests for :func:`build_docx_from_latex_step`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ignorantia.domain.pipeline.value_objects import StepStatus
from ignorantia.infrastructure.pipeline import docx_from_latex_step as module
from ignorantia.infrastructure.pipeline.docx_from_latex_step import (
    build_docx_from_latex_step,
)


@pytest.fixture
def tex_present(tmp_path: Path) -> Path:
    p = tmp_path / "manuscript.tex"
    p.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")
    return p


@pytest.fixture
def bib_present(tmp_path: Path) -> Path:
    p = tmp_path / "bibliography.bib"
    p.write_text("@article{x, title={X}, year={2024}}", encoding="utf-8")
    return p


class TestSkippedWhenPandocMissing:
    def test_pandoc_missing_returns_skipped(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: None)
        step = build_docx_from_latex_step(output_dir=tex_present.parent)
        result = step.fn()
        assert result.status is StepStatus.SKIPPED
        assert "pandoc" in result.message


class TestErrorPaths:
    def test_missing_tex_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/pandoc")
        step = build_docx_from_latex_step(output_dir=tmp_path)
        result = step.fn()
        assert result.status is StepStatus.ERROR
        assert "manuscript.tex" in result.message

    def test_missing_bib_returns_error_when_use_bibtex_true(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/pandoc")
        step = build_docx_from_latex_step(output_dir=tex_present.parent, use_bibtex=True)
        result = step.fn()
        assert result.status is StepStatus.ERROR
        assert "bibliography.bib" in result.message

    def test_pandoc_nonzero_exit_returns_error(
        self,
        tex_present: Path,
        bib_present: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/pandoc")

        def _fake_run(*args, **kwargs):
            return MagicMock(returncode=2, stdout="", stderr="bad input")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_docx_from_latex_step(output_dir=tex_present.parent)
        result = step.fn()
        assert result.status is StepStatus.ERROR
        assert "exit code 2" in result.message


class TestHappyPath:
    def test_runs_pandoc_with_bibliography_when_bibtex_true(
        self,
        tex_present: Path,
        bib_present: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/pandoc")
        docx_path = tex_present.parent / "manuscript.docx"
        captured_cmd: list[str] = []

        def _fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            docx_path.write_bytes(b"PK\x03\x04stub-docx")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_docx_from_latex_step(output_dir=tex_present.parent)
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(docx_path)
        assert "--bibliography" in captured_cmd
        assert "bibliography.bib" in captured_cmd

    def test_runs_pandoc_without_bibliography_when_use_bibtex_false(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/pandoc")
        docx_path = tex_present.parent / "manuscript.docx"
        captured_cmd: list[str] = []

        def _fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            docx_path.write_bytes(b"PK\x03\x04stub-docx")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_docx_from_latex_step(output_dir=tex_present.parent, use_bibtex=False)
        result = step.fn()
        assert result.status is StepStatus.OK
        assert "--bibliography" not in captured_cmd

    def test_log_is_written(
        self,
        tex_present: Path,
        bib_present: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/pandoc")
        (tex_present.parent / "manuscript.docx").write_bytes(b"PK")

        def _fake_run(*args, **kwargs):
            return MagicMock(returncode=0, stdout="pandoc converted ok", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_docx_from_latex_step(output_dir=tex_present.parent)
        step.fn()
        log = (tex_present.parent / "manuscript.docx-pandoc.log").read_text()
        assert "pandoc converted ok" in log


class TestStepMetadata:
    def test_step_name_and_label(self, tmp_path: Path) -> None:
        step = build_docx_from_latex_step(output_dir=tmp_path)
        assert step.name == "docx_from_latex"
        assert "pandoc" in step.label.lower()
