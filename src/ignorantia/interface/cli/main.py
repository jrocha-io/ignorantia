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
from pathlib import Path

import click

from ignorantia import __version__
from ignorantia.application.use_cases.finalize_pipeline import (
    FinalizePipelineUseCase,
)
from ignorantia.application.use_cases.render_manuscript import (
    RenderManuscriptUseCase,
)
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.domain.audit.services import ManifestService
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import PipelineStep
from ignorantia.domain.render.entities import ManuscriptDoc
from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat
from ignorantia.domain.search.services.search_orchestrator import (
    SearchOrchestrator,
)
from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.pipeline.render_steps import (
    build_docx_render_step,
    build_html_render_step,
    build_latex_render_step,
)
from ignorantia.infrastructure.render.citation.factory import (
    citation_formatter_for,
)
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer
from ignorantia.infrastructure.render.latex_renderer import LatexRenderer
from ignorantia.infrastructure.search.adapter_factory import AdapterFactory


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
    """Return the empty default pipeline-step registry.

    Used when ``ignorantia finalize`` runs without ``--input`` /
    ``--output-dir``. With those flags the CLI calls
    :func:`build_render_pipeline_steps` instead, which produces the
    HTML / LaTeX / DOCX render registry. Future steps (cross-tab,
    screening) append here as they migrate from
    ``scripts/pipeline_finalize.py``.
    """
    return ()


def build_render_pipeline_steps(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    citation_style: CitationStyle,
    skip_html: bool = False,
    skip_latex: bool = False,
    skip_docx: bool = False,
) -> tuple[PipelineStep, ...]:
    """Return the render-pipeline registry for a single manuscript.

    Each requested format becomes one :class:`PipelineStep` that
    closes over the manuscript, the output directory, and the
    formatter so the executor can run them as zero-argument
    callables. Skip flags drop a format from the registry entirely
    (vs running it and returning :attr:`StepStatus.SKIPPED` — the
    Open/Closed contract is "the registry contains exactly the
    work to do").
    """
    formatter = citation_formatter_for(citation_style)
    steps: list[PipelineStep] = []
    if not skip_html:
        steps.append(
            build_html_render_step(
                manuscript=manuscript,
                output_dir=output_dir,
                formatter=formatter,
            )
        )
    if not skip_latex:
        steps.append(
            build_latex_render_step(
                manuscript=manuscript,
                output_dir=output_dir,
                formatter=formatter,
            )
        )
    if not skip_docx:
        steps.append(
            build_docx_render_step(
                manuscript=manuscript,
                output_dir=output_dir,
                formatter=formatter,
            )
        )
    return tuple(steps)


def build_finalize_pipeline_use_case() -> FinalizePipelineUseCase:
    """Construct :class:`FinalizePipelineUseCase` with the empty registry."""
    return FinalizePipelineUseCase(
        executor=PipelineExecutor(clock=_real_clock),
        steps=build_pipeline_steps(),
    )


def build_render_pipeline_use_case(
    *,
    manuscript: ManuscriptDoc,
    output_dir: Path,
    citation_style: CitationStyle,
    skip_html: bool = False,
    skip_latex: bool = False,
    skip_docx: bool = False,
) -> FinalizePipelineUseCase:
    """Construct :class:`FinalizePipelineUseCase` configured for render output.

    Production wiring used by ``ignorantia finalize`` when ``--input``
    is supplied: builds the render-step registry pinned to the given
    manuscript + output directory + citation style, then wraps it in
    a :class:`PipelineExecutor` with the real clock.
    """
    return FinalizePipelineUseCase(
        executor=PipelineExecutor(clock=_real_clock),
        steps=build_render_pipeline_steps(
            manuscript=manuscript,
            output_dir=output_dir,
            citation_style=citation_style,
            skip_html=skip_html,
            skip_latex=skip_latex,
            skip_docx=skip_docx,
        ),
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


def _user_agent() -> str:
    """Return the User-Agent string the production HTTP client uses."""
    return f"ignorantia/{__version__} (+https://github.com/jrocha-io/ignorantia)"


def build_http_client() -> HttpClient:
    """Construct a production :class:`HttpClient`.

    Defaults are conservative: 30s timeout, 1s minimum throttle
    between requests, 3 retries. CLI / pipeline knobs to override
    these can be added when the use case demands.
    """
    return HttpClient(
        user_agent=_user_agent(),
        timeout_s=30.0,
        throttle_s=1.0,
        max_retries=3,
    )


def build_search_for_studies_use_case() -> SearchForStudiesUseCase:
    """Construct :class:`SearchForStudiesUseCase` with production wiring.

    Wires the real :class:`AdapterFactory` (which exposes every
    registered search adapter) behind a :class:`SearchOrchestrator`.
    """
    factory = AdapterFactory(http=build_http_client())
    return SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))


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
