"""Unit tests for :func:`build_pdf_compile_step`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ignorantia.domain.pipeline.value_objects import StepStatus
from ignorantia.infrastructure.pipeline import pdf_compile_step as module
from ignorantia.infrastructure.pipeline.pdf_compile_step import (
    build_pdf_compile_step,
)


@pytest.fixture
def tex_present(tmp_path: Path) -> Path:
    p = tmp_path / "manuscript.tex"
    p.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Degradable: skip when binaries missing
# ---------------------------------------------------------------------------


class TestSkippedWhenBinariesMissing:
    def test_pdflatex_missing_returns_skipped(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda _: None)
        step = build_pdf_compile_step(output_dir=tex_present.parent)
        result = step.fn()
        assert result.status is StepStatus.SKIPPED
        assert "pdflatex" in result.message

    def test_bibtex_missing_returns_skipped(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # pdflatex present, bibtex absent.
        def _which(binary: str) -> str | None:
            return "/usr/bin/pdflatex" if binary == "pdflatex" else None

        monkeypatch.setattr(module.shutil, "which", _which)
        step = build_pdf_compile_step(output_dir=tex_present.parent)
        result = step.fn()
        assert result.status is StepStatus.SKIPPED
        assert "bibtex" in result.message

    def test_use_bibtex_false_skips_bibtex_check(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # pdflatex present, bibtex absent — but use_bibtex=False
        # so absence of bibtex does NOT cause skip.
        def _which(binary: str) -> str | None:
            return "/usr/bin/pdflatex" if binary == "pdflatex" else None

        monkeypatch.setattr(module.shutil, "which", _which)
        # Stub subprocess.run to succeed and produce a PDF.
        pdf_path = tex_present.parent / "manuscript.pdf"

        def _fake_run(*args, **kwargs):
            pdf_path.write_bytes(b"%PDF-stub")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_pdf_compile_step(output_dir=tex_present.parent, use_bibtex=False)
        result = step.fn()
        assert result.status is StepStatus.OK


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    def test_missing_tex_file_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda b: f"/usr/bin/{b}")
        step = build_pdf_compile_step(output_dir=tmp_path)
        result = step.fn()
        assert result.status is StepStatus.ERROR
        assert "manuscript.tex" in result.message

    def test_pdflatex_nonzero_exit_returns_error(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda b: f"/usr/bin/{b}")

        def _fake_run(*args, **kwargs):
            return MagicMock(returncode=1, stdout="error in line 5", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_pdf_compile_step(output_dir=tex_present.parent)
        result = step.fn()
        assert result.status is StepStatus.ERROR
        assert "exit code 1" in result.message
        # Log file was written.
        assert (tex_present.parent / "manuscript.compile.log").is_file()


# ---------------------------------------------------------------------------
# Happy path with stubbed subprocess
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_runs_4_pass_cycle_when_use_bibtex_true(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda b: f"/usr/bin/{b}")
        pdf_path = tex_present.parent / "manuscript.pdf"
        calls: list[list[str]] = []

        def _fake_run(cmd, **kwargs):
            calls.append([str(c) for c in cmd])
            pdf_path.write_bytes(b"%PDF-1.5\nstub")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_pdf_compile_step(output_dir=tex_present.parent, use_bibtex=True)
        result = step.fn()
        assert result.status is StepStatus.OK
        assert result.artifact == str(pdf_path)
        # 4-pass: pdflatex, bibtex, pdflatex, pdflatex
        assert len(calls) == 4
        binaries = [Path(c[0]).name for c in calls]
        assert binaries == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]

    def test_runs_2_pass_cycle_when_use_bibtex_false(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda b: f"/usr/bin/{b}")
        pdf_path = tex_present.parent / "manuscript.pdf"
        calls: list[list[str]] = []

        def _fake_run(cmd, **kwargs):
            calls.append([str(c) for c in cmd])
            pdf_path.write_bytes(b"%PDF-1.5\nstub")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_pdf_compile_step(output_dir=tex_present.parent, use_bibtex=False)
        result = step.fn()
        assert result.status is StepStatus.OK
        # 2-pass: pdflatex, pdflatex (no bibtex)
        assert len(calls) == 2
        assert all(Path(c[0]).name == "pdflatex" for c in calls)

    def test_compile_log_is_written(
        self, tex_present: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.shutil, "which", lambda b: f"/usr/bin/{b}")
        (tex_present.parent / "manuscript.pdf").write_bytes(b"%PDF-stub")

        def _fake_run(*args, **kwargs):
            return MagicMock(returncode=0, stdout="some pdflatex output", stderr="")

        monkeypatch.setattr(module.subprocess, "run", _fake_run)
        step = build_pdf_compile_step(output_dir=tex_present.parent, use_bibtex=False)
        step.fn()
        log = (tex_present.parent / "manuscript.compile.log").read_text()
        assert "pdflatex" in log
        assert "some pdflatex output" in log


# ---------------------------------------------------------------------------
# Step metadata
# ---------------------------------------------------------------------------


class TestStepMetadata:
    def test_step_name_and_label(self, tmp_path: Path) -> None:
        step = build_pdf_compile_step(output_dir=tmp_path)
        assert step.name == "compile_pdf"
        assert "pdflatex" in step.label
