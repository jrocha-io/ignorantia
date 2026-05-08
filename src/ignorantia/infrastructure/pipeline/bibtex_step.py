r"""``build_bibtex_render_step`` — write ``bibliography.bib`` for a manuscript.

Companion step to :func:`build_latex_render_step` (PR #80, render
pipeline migration). Decisão 36 / Fix 6 reclassifies PDF compiled
from LaTeX + BibTeX as the canonical academic artefact, which
requires a ``.bib`` file alongside the ``.tex``. This step handles
the ``.bib`` half.

Registry order matters: the LaTeX render step (when configured
in external-BibTeX mode) emits ``\\bibliography{bibliography}``
referencing this file. To keep the ``pdflatex+bibtex+pdflatex+
pdflatex`` cycle clean, the bib step should run **before** the
LaTeX step in the pipeline registry.

The factory closes over a :class:`ManuscriptDoc`, an output_dir,
and a :class:`BibTexEntryFormatterPort` (one of the four shipped
adapters via :func:`bibtex_formatter_for`).
"""

from __future__ import annotations

from pathlib import Path

from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)
from ignorantia.domain.render.entities import ManuscriptDoc
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
    BibTexEntryFormatterPort,
)
from ignorantia.infrastructure.render.bib_file_renderer import BibFileRenderer

_DEFAULT_FILENAME = "bibliography.bib"


def build_bibtex_render_step(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    formatter: BibTexEntryFormatterPort,
    filename: str = _DEFAULT_FILENAME,
) -> PipelineStep:
    """Build a :class:`PipelineStep` that emits ``bibliography.bib``.

    Args:
        manuscript: Manuscript whose ``references`` get rendered.
            Closure-captured so the step's ``fn`` is zero-argument.
        output_dir: Directory where ``bibliography.bib`` lands.
            Created if missing.
        formatter: Concrete :class:`BibTexEntryFormatterPort`. Use
            :func:`bibtex_formatter_for` to pick one from
            :class:`BibTexStyle`.
        filename: Override the default ``bibliography.bib`` (e.g.
            for tests or for emitting under a custom name).

    Returns:
        A :class:`PipelineStep` named ``render_bibtex``.
    """
    target = output_dir / filename
    renderer = BibFileRenderer(formatter=formatter)

    def _fn() -> StepResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        body = renderer.render(manuscript)
        target.write_bytes(body)
        return StepResult(
            name="render_bibtex",
            status=StepStatus.OK,
            artifact=str(target),
            message=(
                f"Wrote {len(body)} bytes; "
                f"{len(manuscript.references)} entry(s) "
                f"in {formatter.style.value} style"
            ),
        )

    return PipelineStep(
        name="render_bibtex",
        label="Render bibliography.bib (BibTeX)",
        fn=_fn,
    )
