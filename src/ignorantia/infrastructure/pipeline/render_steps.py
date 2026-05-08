"""``PipelineStep`` factories for the v3 render pipeline.

The v2 ``scripts/pipeline_finalize.py`` orchestrated six concrete
steps (``cross_tab``, ``format_abnt``, ``render_html_chunks``,
``render_docx_abnt``, ``render_latex``, ``screening_pipeline``).
This module migrates the three render steps into the v3
infrastructure layer; the remaining steps (cross_tab, screening)
land in follow-up sprints once their domain code exists. The
``format_abnt`` step is no longer needed as a separate pipeline
step in v3 — citation formatting happens inline inside
:class:`HtmlRenderer` / :class:`LatexRenderer` / :class:`DocxRenderer`
through the injected :class:`CitationFormatterPort`.

Every factory below returns a :class:`PipelineStep` whose
zero-argument ``fn`` closes over the manuscript, the output
directory, and the citation formatter. The
:class:`PipelineExecutor` runs the registry sequentially and
captures any exception as :attr:`StepStatus.ERROR`, so the
factories themselves do not catch — they let the executor's
resilience policy do its job.

DOCX is gated on the optional ``[docx]`` extra. The lazy import in
:func:`build_docx_render_step` mirrors the
:class:`DocxRenderer` constructor's lazy import: the factory is
always callable, but ``fn()`` raises :class:`ImportError` (and the
executor turns it into a clean ERROR result) if ``python-docx`` is
not installed.
"""

from __future__ import annotations

from pathlib import Path

from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)
from ignorantia.domain.render.entities import ManuscriptDoc
from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer
from ignorantia.infrastructure.render.latex_renderer import LatexRenderer

_HTML_FILENAME = "manuscript.html"
_LATEX_FILENAME = "manuscript.tex"
_DOCX_FILENAME = "manuscript.docx"


def build_html_render_step(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    formatter: CitationFormatterPort,
) -> PipelineStep:
    """Build a :class:`PipelineStep` that renders ``manuscript`` as HTML.

    The step writes ``output_dir/manuscript.html`` and returns a
    :class:`StepResult` with the artefact path and the byte size.
    """

    def _fn() -> StepResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        renderer = HtmlRenderer(formatter=formatter)
        artefact = renderer.render(manuscript)
        output_path = output_dir / _HTML_FILENAME
        output_path.write_bytes(artefact)
        return StepResult(
            name="render_html",
            status=StepStatus.OK,
            artifact=str(output_path),
            message=f"Wrote {len(artefact)} bytes",
        )

    return PipelineStep(name="render_html", label="Render HTML", fn=_fn)


def build_latex_render_step(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    formatter: CitationFormatterPort,
) -> PipelineStep:
    """Build a :class:`PipelineStep` that renders ``manuscript`` as LaTeX.

    The step writes ``output_dir/manuscript.tex`` and returns a
    :class:`StepResult` with the artefact path and the byte size.
    """

    def _fn() -> StepResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        renderer = LatexRenderer(formatter=formatter)
        artefact = renderer.render(manuscript)
        output_path = output_dir / _LATEX_FILENAME
        output_path.write_bytes(artefact)
        return StepResult(
            name="render_latex",
            status=StepStatus.OK,
            artifact=str(output_path),
            message=f"Wrote {len(artefact)} bytes",
        )

    return PipelineStep(name="render_latex", label="Render LaTeX", fn=_fn)


def build_docx_render_step(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    formatter: CitationFormatterPort,
) -> PipelineStep:
    """Build a :class:`PipelineStep` that renders ``manuscript`` as DOCX.

    Gated on the optional ``[docx]`` extra: the factory itself is
    always callable, but ``fn()`` instantiates :class:`DocxRenderer`
    which raises :class:`ImportError` (caught by
    :class:`PipelineExecutor` and reported as ERROR) when the extra
    is not installed.
    """

    def _fn() -> StepResult:
        # Lazy import so the module loads cleanly without python-docx.
        from ignorantia.infrastructure.render.docx_renderer import DocxRenderer

        output_dir.mkdir(parents=True, exist_ok=True)
        renderer = DocxRenderer(formatter=formatter)
        artefact = renderer.render(manuscript)
        output_path = output_dir / _DOCX_FILENAME
        output_path.write_bytes(artefact)
        return StepResult(
            name="render_docx",
            status=StepStatus.OK,
            artifact=str(output_path),
            message=f"Wrote {len(artefact)} bytes",
        )

    return PipelineStep(name="render_docx", label="Render DOCX", fn=_fn)
