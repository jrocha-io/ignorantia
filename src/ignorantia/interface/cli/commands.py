"""Click subcommands wired to application use cases.

Each subcommand:

1. Builds (or reuses) a use case via the composition root.
2. Translates Click options to a Command DTO from
   :mod:`ignorantia.application.dtos`.
3. Calls ``use_case.execute(command)``.
4. Prints the Result DTO in a stable, machine-readable form.

The pattern is the same across subcommands so subsequent F7 PRs
(``search``, ``render``, ``finalize``) just append a new command
function.

Test seam: each subcommand checks ``ctx.obj`` for a pre-wired use
case before calling the production ``build_*`` factory. This lets
tests inject a deterministic instance (frozen clock, stub services)
without monkey-patching the composition root.
"""

from __future__ import annotations

import json
from typing import Any

import click

from ignorantia.application.dtos import RunAuditCommand
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.interface.cli import main as _main


def register(cli: click.Group) -> None:
    """Attach every subcommand to ``cli``.

    Called once from :mod:`ignorantia.interface.cli.main` after the
    group is defined. Keeps subcommand registration explicit and
    discoverable in one place.
    """
    cli.add_command(audit)


@click.command(
    "audit",
    help="Append a single entry to the reproducibility manifest.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--action",
    required=True,
    help="Stable action identifier (e.g. 'search.run').",
)
@click.option(
    "--actor",
    default="cli",
    show_default=True,
    help="Who is recording the entry.",
)
@click.option(
    "--payload",
    default="{}",
    show_default=True,
    help="JSON object with free-form details about the event.",
)
@click.pass_context
def audit(ctx: click.Context, action: str, actor: str, payload: str) -> None:
    """Record an entry via :class:`RunAuditUseCase`.

    The result is printed as a single-line JSON object on stdout so
    callers can pipe it into other tooling without parsing the human
    text.
    """
    try:
        payload_obj = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(
            f"--payload must be a valid JSON object: {exc.msg}",
            param_hint="--payload",
        ) from exc
    if not isinstance(payload_obj, dict):
        raise click.BadParameter(
            "--payload must be a JSON object (dict), not a scalar or array.",
            param_hint="--payload",
        )

    use_case = _resolve_audit_use_case(ctx)
    command = RunAuditCommand(action=action, actor=actor, payload=payload_obj)
    result = use_case.execute(command)
    click.echo(
        json.dumps(
            {
                "timestamp_iso8601": result.timestamp_iso8601,
                "action": result.action,
                "manifest_size": result.manifest_size,
            },
            ensure_ascii=False,
        )
    )


def _resolve_audit_use_case(ctx: click.Context) -> RunAuditUseCase:
    """Return a pre-injected use case from ``ctx.obj`` or build one.

    Tests stash a use case under ``ctx.obj["audit_use_case"]`` so they
    can pin a frozen clock and inspect the in-process manifest. In
    production the build-from-scratch branch runs.
    """
    obj: dict[str, Any] = ctx.ensure_object(dict)
    cached = obj.get("audit_use_case")
    if isinstance(cached, RunAuditUseCase):
        return cached
    use_case = _main.build_audit_use_case()
    obj["audit_use_case"] = use_case
    return use_case
