"""Composition root for the v3 CLI.

This module wires concrete domain services + use cases together at the
process boundary. Per ``V3_ARCHITECTURE_PLAN.md`` the *interface*
layer (CLI / HTTP / future entry points) only ever sees DTOs from
``application.dtos`` — never raw domain entities. The CLI translates
``argv`` to a Command DTO, calls the use case, and prints the
Result DTO.

The Click group declared here is registered as the ``ignorantia``
console script in ``pyproject.toml``. Subcommands live in
``commands.py`` and import the use cases they wrap.
"""

from __future__ import annotations

from datetime import datetime, timezone

import click

from ignorantia import __version__
from ignorantia.application.use_cases.finalize_pipeline import (
    FinalizePipelineUseCase,
)
from ignorantia.application.use_cases.render_manuscript import (
    RenderManuscriptUseCase,
)
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.domain.audit.services import ManifestService
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import PipelineStep
from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat
from ignorantia.infrastructure.render.citation.factory import (
    citation_formatter_for,
)
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer
from ignorantia.infrastructure.render.latex_renderer import LatexRenderer


def _real_clock() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Centralised here so the CLI's wiring is the single place that
    calls :func:`datetime.now` (issue #13). Domain code stays clock-
    free; production wiring binds the clock here, tests inject a
    frozen value.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_audit_use_case() -> RunAuditUseCase:
    """Construct :class:`RunAuditUseCase` with production wiring.

    Factored out so tests can wire the same use case with a frozen
    clock, and so future composition-root logic (e.g. loading a
    persisted manifest from disk) lives in one obvious place.
    """
    return RunAuditUseCase(service=ManifestService(clock=_real_clock))


def build_pipeline_steps() -> tuple[PipelineStep, ...]:
    """Return the concrete pipeline-step registry the CLI runs.

    Empty for now: the v3 step library (cross-tab, render, screening,
    ...) is being migrated from ``scripts/pipeline_finalize.py`` into
    ``infrastructure/pipeline/`` incrementally. As each step lands as
    a :class:`PipelineStep` factory, append it here. Keeping the
    registry centralised in the composition root preserves the
    Open/Closed property.
    """
    return ()


def build_finalize_pipeline_use_case() -> FinalizePipelineUseCase:
    """Construct :class:`FinalizePipelineUseCase` with production wiring."""
    return FinalizePipelineUseCase(
        executor=PipelineExecutor(clock=_real_clock),
        steps=build_pipeline_steps(),
    )


def build_renderer(
    output_format: OutputFormat,
    formatter: CitationFormatterPort,
) -> RendererPort:
    """Map :class:`OutputFormat` to a concrete :class:`RendererPort`.

    DOCX is behind the optional ``[docx]`` extra; importing the
    DOCX renderer here is deferred until the user actually asks for
    it so the CLI works end-to-end without ``python-docx`` installed
    as long as the user does not pass ``--format docx``.
    """
    if output_format is OutputFormat.HTML:
        return HtmlRenderer(formatter=formatter)
    if output_format is OutputFormat.LATEX:
        return LatexRenderer(formatter=formatter)
    if output_format is OutputFormat.DOCX:
        # Imported lazily so a deployment without python-docx still
        # enjoys the HTML / LaTeX paths.
        from ignorantia.infrastructure.render.docx_renderer import DocxRenderer

        return DocxRenderer(formatter=formatter)
    raise ValueError(f"unsupported output format: {output_format!r}")


def build_render_manuscript_use_case(
    output_format: OutputFormat,
    citation_style: CitationStyle,
) -> RenderManuscriptUseCase:
    """Construct :class:`RenderManuscriptUseCase` with production wiring.

    The format and citation style come from CLI options; the factory
    threads them through the renderer / formatter ports without the
    interface layer touching domain entities directly.
    """
    formatter = citation_formatter_for(citation_style)
    renderer = build_renderer(output_format, formatter)
    return RenderManuscriptUseCase(renderer=renderer, formatter=formatter)


@click.group(
    help="Ignorantia — PRISMA-2020 systematic literature review skill.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__, message="%(prog)s %(version)s")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Top-level Click group; subcommands are registered below."""
    # ``ctx.ensure_object(dict)`` lets subcommands stash use cases
    # on the context for tests to swap. Production callers go through
    # ``build_*_use_case`` directly.
    ctx.ensure_object(dict)


# Subcommand registration is done in ``commands`` so this module stays
# focused on composition.
from ignorantia.interface.cli import commands  # noqa: E402

commands.register(cli)
