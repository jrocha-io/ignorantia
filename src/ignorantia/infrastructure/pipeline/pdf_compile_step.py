r"""``build_pdf_compile_step`` — compile ``manuscript.tex`` to ``.pdf``.

Runs the canonical academic compile cycle::

    pdflatex -interaction=nonstopmode manuscript.tex
    bibtex manuscript
    pdflatex -interaction=nonstopmode manuscript.tex
    pdflatex -interaction=nonstopmode manuscript.tex

The four-pass cycle resolves both ``\\cite{}`` keys (BibTeX needs
the ``.aux`` from pass 1) and forward references / ToC entries
(pass 2 picks up new aux entries; pass 3 settles cross-refs).

The step is **degradable**: if ``pdflatex`` (or, when the LaTeX
file uses ``\\bibliography{}``, ``bibtex``) is not on ``$PATH``,
the step returns :attr:`StepStatus.SKIPPED` with a message naming
the missing binary — it does *not* error. Pipelines without
LaTeX installed still succeed end-to-end; they just don't produce
the PDF.

Stdout/stderr from each pass is captured to ``<tex>.compile.log``
in ``output_dir`` so post-mortem debugging works without re-running.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)

_ArgsBuilder = Callable[[str, str], list[str]]

_DEFAULT_TEX_FILENAME = "manuscript.tex"
_PDFLATEX_TIMEOUT_S = 60
_BIBTEX_TIMEOUT_S = 30


def build_pdf_compile_step(
    *,
    output_dir: Path,
    tex_filename: str = _DEFAULT_TEX_FILENAME,
    use_bibtex: bool = True,
) -> PipelineStep:
    """Build a step that compiles ``output_dir/<tex_filename>`` to PDF.

    Args:
        output_dir: Directory containing the ``.tex`` (and ``.bib``,
            when ``use_bibtex=True``). Compile runs there so all
            generated artefacts (``.aux``, ``.bbl``, ``.log``, ``.pdf``)
            land alongside the source.
        tex_filename: Name of the ``.tex`` file. Default
            ``manuscript.tex``.
        use_bibtex: Whether to run the BibTeX pass. Set ``False``
            for legacy inline-bibliography ``.tex`` files (pre-Fix 6
            mode); the four-pass cycle becomes ``pdflatex x 2``.

    Returns:
        A :class:`PipelineStep` named ``compile_pdf``.
    """
    tex_path = output_dir / tex_filename
    base = tex_path.stem  # "manuscript" — used for bibtex auxname
    pdf_path = output_dir / f"{base}.pdf"
    log_path = output_dir / f"{base}.compile.log"

    def _fn() -> StepResult:
        pdflatex = shutil.which("pdflatex")
        if pdflatex is None:
            return StepResult(
                name="compile_pdf",
                status=StepStatus.SKIPPED,
                message="pdflatex not on PATH; install TeX Live to enable PDF compile",
            )
        if not tex_path.is_file():
            return StepResult(
                name="compile_pdf",
                status=StepStatus.ERROR,
                message=f"{tex_path} does not exist; run the LaTeX render step first",
            )

        bibtex: str | None = None
        if use_bibtex:
            bibtex = shutil.which("bibtex")
            if bibtex is None:
                return StepResult(
                    name="compile_pdf",
                    status=StepStatus.SKIPPED,
                    message=(
                        "bibtex not on PATH; install TeX Live (or pass "
                        "use_bibtex=False for inline-bibliography .tex)"
                    ),
                )

        log_lines: list[str] = []
        sequence = _compile_sequence(use_bibtex=use_bibtex)
        for label, args_template in sequence:
            binary = pdflatex if label.startswith("pdflatex") else bibtex
            assert binary is not None  # noqa: S101 — narrowed by SKIPPED guards above
            cmd: list[str] = [binary, *args_template(tex_filename, base)]
            log_lines.append(f"=== {label} ===\n$ {' '.join(str(a) for a in cmd)}")
            timeout = _BIBTEX_TIMEOUT_S if label == "bibtex" else _PDFLATEX_TIMEOUT_S
            completed = subprocess.run(  # noqa: S603 — args list, no shell
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            log_lines.append(completed.stdout or "")
            log_lines.append(completed.stderr or "")
            if completed.returncode != 0:
                log_path.write_text("\n".join(log_lines), encoding="utf-8")
                return StepResult(
                    name="compile_pdf",
                    status=StepStatus.ERROR,
                    message=(
                        f"{label} failed with exit code {completed.returncode}; "
                        f"see {log_path} for full output"
                    ),
                )

        log_path.write_text("\n".join(log_lines), encoding="utf-8")

        if not pdf_path.is_file():
            return StepResult(
                name="compile_pdf",
                status=StepStatus.ERROR,
                message=(f"compile cycle finished without producing {pdf_path}; see {log_path}"),
            )
        return StepResult(
            name="compile_pdf",
            status=StepStatus.OK,
            artifact=str(pdf_path),
            message=(
                f"Compiled {tex_path.name} -> {pdf_path.name} "
                f"({pdf_path.stat().st_size} bytes); log at {log_path.name}"
            ),
        )

    return PipelineStep(
        name="compile_pdf",
        label="Compile LaTeX to PDF (pdflatex+bibtex+pdflatex+pdflatex)",
        fn=_fn,
    )


def _pdflatex_args(tex: str, _base: str) -> list[str]:
    return ["-interaction=nonstopmode", tex]


def _bibtex_args(_tex: str, base: str) -> list[str]:
    return [base]


def _compile_sequence(*, use_bibtex: bool) -> list[tuple[str, _ArgsBuilder]]:
    """Return the (label, args-template) sequence for the compile cycle."""
    pdflatex_args: _ArgsBuilder = _pdflatex_args
    bibtex_args: _ArgsBuilder = _bibtex_args

    if use_bibtex:
        return [
            ("pdflatex (1/3)", pdflatex_args),
            ("bibtex", bibtex_args),
            ("pdflatex (2/3)", pdflatex_args),
            ("pdflatex (3/3)", pdflatex_args),
        ]
    return [
        ("pdflatex (1/2)", pdflatex_args),
        ("pdflatex (2/2)", pdflatex_args),
    ]
