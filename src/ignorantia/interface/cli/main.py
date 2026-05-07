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
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.domain.audit.services import ManifestService


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
