"""``incremental_render`` — chunked HTML write step (Fix 3, Decisão 34).

The v2 ``scripts/render_chunks.py`` (Decisão 18, v2.10.0)
implemented incremental rendering by writing the HTML head, then
appending one section at a time, then closing — so a transient
failure in section *N* did not invalidate sections 0..N-1, and the
full HTML never had to live in a single string.

This module ports that pattern into v3 as a :class:`PipelineStep`.
The factory closes over a :class:`ManuscriptDoc` and an output
path; the step's ``fn`` opens the file, writes the head bytes via
:meth:`HtmlRenderer.render_opening`, iterates the sections writing
each fragment via :meth:`HtmlRenderer.render_section`, optionally
writes the references block, and closes with
:meth:`HtmlRenderer.render_closing`. The per-section writes are
flushed individually so a crash mid-stream leaves a partial-but-
parsable file (for debugging); on success the file matches what
:meth:`HtmlRenderer.render` would emit byte-for-byte (modulo the
trailing newline).

When to prefer this step over the one-shot
:func:`build_html_render_step`:

* The manuscript has many sections (>5 per Decisão 34) — the step
  surface is the same but memory pressure is lower because we
  never hold the full HTML in memory.
* The render is being driven from a chat context where holding
  the full HTML in conversation tokens would exhaust the budget
  (the SKILL.md operational protocol).

When to prefer the one-shot path: tiny manuscripts (<5 sections)
where the difference is unmeasurable.
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

_DEFAULT_FILENAME = "manuscript.html"


def build_incremental_html_render_step(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    formatter: CitationFormatterPort,
    filename: str = _DEFAULT_FILENAME,
) -> PipelineStep:
    """Build a :class:`PipelineStep` that writes the HTML in chunks.

    Args:
        manuscript: The document to render. Captured at factory
            time; the closure means the step's ``fn`` is
            zero-argument (the v3 :class:`PipelineStep` contract).
        output_dir: Directory where the artefact lands. Created if
            missing.
        formatter: The :class:`CitationFormatterPort` used for the
            references list (mirrors the one-shot step's
            ``formatter`` keyword).
        filename: Override the default ``manuscript.html`` (useful
            for tests and for emitting under a custom name).

    Returns:
        A :class:`PipelineStep` named ``incremental_render_html``.
    """
    target = output_dir / filename
    renderer = HtmlRenderer(formatter=formatter)

    def _fn() -> StepResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        bytes_written = 0
        sections_appended = 0

        with target.open("wb") as f:
            head_bytes = renderer.render_opening(manuscript)
            f.write(head_bytes)
            f.flush()
            bytes_written += len(head_bytes)

            for section in manuscript.sections:
                # render_section returns just the <section> fragment;
                # append a trailing newline so the on-disk shape
                # matches the joined output of HtmlRenderer.render.
                fragment = renderer.render_section(section) + b"\n"
                f.write(fragment)
                f.flush()
                bytes_written += len(fragment)
                sections_appended += 1

            references_bytes = renderer.render_references_section(manuscript.references)
            if references_bytes:
                f.write(references_bytes)
                f.flush()
                bytes_written += len(references_bytes)

            closing_bytes = renderer.render_closing()
            f.write(closing_bytes)
            bytes_written += len(closing_bytes)

        return StepResult(
            name="incremental_render_html",
            status=StepStatus.OK,
            artifact=str(target),
            message=(
                f"Wrote {bytes_written} bytes; "
                f"{sections_appended} section(s), "
                f"{len(manuscript.references)} reference(s)"
            ),
        )

    return PipelineStep(
        name="incremental_render_html",
        label="Incremental HTML render (chunked write)",
        fn=_fn,
    )
