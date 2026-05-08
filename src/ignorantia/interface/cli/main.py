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
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.domain.audit.services import ManifestService
from ignorantia.domain.pipeline.services import PipelineExecutor
from ignorantia.domain.pipeline.value_objects import PipelineStep
from ignorantia.domain.search.services.search_orchestrator import (
    SearchOrchestrator,
)
from ignorantia.infrastructure.http_client import HttpClient
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
