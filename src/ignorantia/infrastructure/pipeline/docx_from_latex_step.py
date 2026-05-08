"""``build_docx_from_latex_step`` — convert ``manuscript.tex`` to ``.docx``.

Runs ``pandoc -s manuscript.tex -o manuscript.docx
--bibliography=bibliography.bib`` (the ``--bibliography`` flag is
omitted when ``use_bibtex=False``). Same degradation pattern as
:func:`build_pdf_compile_step`: missing ``pandoc`` returns
:attr:`StepStatus.SKIPPED` rather than ``ERROR`` so deployments
without pandoc still succeed end-to-end.

This step **replaces** :func:`build_docx_render_step` for the
academic-canonical path: the DOCX rendered from the same ``.tex``
that produces the PDF stays structurally identical to the PDF
(citation order, section numbering, table layout). The direct
:class:`DocxRenderer` path (which builds DOCX from
:class:`ManuscriptDoc` independently) remains available as a
fallback for users without pandoc — its output diverges
structurally from the PDF but compiles without external tools.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)

_DEFAULT_TEX_FILENAME = "manuscript.tex"
_DEFAULT_BIB_FILENAME = "bibliography.bib"
_DEFAULT_DOCX_FILENAME = "manuscript.docx"
_PANDOC_TIMEOUT_S = 60


def build_docx_from_latex_step(
    *,
    output_dir: Path,
    tex_filename: str = _DEFAULT_TEX_FILENAME,
    bib_filename: str | None = _DEFAULT_BIB_FILENAME,
    docx_filename: str = _DEFAULT_DOCX_FILENAME,
    use_bibtex: bool = True,
) -> PipelineStep:
    """Build a step that converts ``output_dir/<tex>`` to ``.docx`` via pandoc.

    Args:
        output_dir: Directory containing the ``.tex`` (and optionally
            the ``.bib``).
        tex_filename: Source LaTeX filename.
        bib_filename: BibTeX filename. Used only when
            ``use_bibtex=True``. Default ``bibliography.bib``.
        docx_filename: Target ``.docx`` filename.
        use_bibtex: Pass ``--bibliography`` to pandoc. Set ``False``
            for inline-bibliography ``.tex`` files (legacy path).

    Returns:
        A :class:`PipelineStep` named ``docx_from_latex``.
    """
    tex_path = output_dir / tex_filename
    docx_path = output_dir / docx_filename
    log_path = output_dir / f"{tex_path.stem}.docx-pandoc.log"
    bib_path = output_dir / bib_filename if (use_bibtex and bib_filename) else None

    def _fn() -> StepResult:
        pandoc = shutil.which("pandoc")
        if pandoc is None:
            return StepResult(
                name="docx_from_latex",
                status=StepStatus.SKIPPED,
                message=(
                    "pandoc not on PATH; install pandoc to enable .tex -> .docx, "
                    "or use the direct DocxRenderer step as a fallback"
                ),
            )
        if not tex_path.is_file():
            return StepResult(
                name="docx_from_latex",
                status=StepStatus.ERROR,
                message=f"{tex_path} does not exist; run the LaTeX render step first",
            )

        cmd: list[str] = [
            pandoc,
            "-s",
            tex_filename,
            "-o",
            docx_filename,
        ]
        if bib_path is not None:
            if not bib_path.is_file():
                return StepResult(
                    name="docx_from_latex",
                    status=StepStatus.ERROR,
                    message=(
                        f"{bib_path} does not exist; run the BibTeX render step "
                        f"before docx_from_latex (or pass use_bibtex=False)"
                    ),
                )
            cmd.extend(["--bibliography", bib_path.name])

        completed = subprocess.run(  # noqa: S603 — args list, no shell
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=_PANDOC_TIMEOUT_S,
            check=False,
        )
        log_path.write_text(
            f"$ {' '.join(cmd)}\n\n"
            f"=== stdout ===\n{completed.stdout or ''}\n\n"
            f"=== stderr ===\n{completed.stderr or ''}\n",
            encoding="utf-8",
        )
        if completed.returncode != 0:
            return StepResult(
                name="docx_from_latex",
                status=StepStatus.ERROR,
                message=(f"pandoc failed with exit code {completed.returncode}; see {log_path}"),
            )
        if not docx_path.is_file():
            return StepResult(
                name="docx_from_latex",
                status=StepStatus.ERROR,
                message=f"pandoc returned 0 but {docx_path} not found",
            )
        return StepResult(
            name="docx_from_latex",
            status=StepStatus.OK,
            artifact=str(docx_path),
            message=(
                f"Converted {tex_path.name} -> {docx_path.name} via pandoc "
                f"({docx_path.stat().st_size} bytes)"
            ),
        )

    return PipelineStep(
        name="docx_from_latex",
        label="Convert LaTeX to DOCX (pandoc)",
        fn=_fn,
    )
