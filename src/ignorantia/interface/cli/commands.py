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
from dataclasses import asdict
from pathlib import Path
from typing import Any

import click

from ignorantia.application.dtos import (
    FinalizePipelineCommand,
    RunAuditCommand,
    SearchForStudiesCommand,
)
from ignorantia.application.use_cases.finalize_pipeline import (
    FinalizePipelineUseCase,
)
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.interface.cli import main as _main


def register(cli: click.Group) -> None:
    """Attach every subcommand to ``cli``.

    Called once from :mod:`ignorantia.interface.cli.main` after the
    group is defined. Keeps subcommand registration explicit and
    discoverable in one place.
    """
    cli.add_command(audit)
    cli.add_command(finalize)
    cli.add_command(search)


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


@click.command(
    "finalize",
    help="Run the pipeline finalisation steps and emit a JSON summary.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--actor",
    default="cli",
    show_default=True,
    help="Who is running the pipeline.",
)
@click.pass_context
def finalize(ctx: click.Context, actor: str) -> None:
    """Run :class:`FinalizePipelineUseCase` and print the result DTO."""
    use_case = _resolve_finalize_use_case(ctx)
    command = FinalizePipelineCommand(actor=actor)
    result = use_case.execute(command)
    click.echo(
        json.dumps(
            {
                "started_at_iso8601": result.started_at_iso8601,
                "finished_at_iso8601": result.finished_at_iso8601,
                "n_ok": result.n_ok,
                "n_skipped": result.n_skipped,
                "n_errors": result.n_errors,
                "final_artifacts": list(result.final_artifacts),
                "is_successful": result.is_successful,
                "steps": [
                    {
                        "name": s.name,
                        "status": s.status,
                        "message": s.message,
                        "artifact": s.artifact,
                    }
                    for s in result.steps
                ],
            },
            ensure_ascii=False,
        )
    )


def _resolve_finalize_use_case(ctx: click.Context) -> FinalizePipelineUseCase:
    """Same injection seam as :func:`_resolve_audit_use_case`."""
    obj: dict[str, Any] = ctx.ensure_object(dict)
    cached = obj.get("finalize_use_case")
    if isinstance(cached, FinalizePipelineUseCase):
        return cached
    use_case = _main.build_finalize_pipeline_use_case()
    obj["finalize_use_case"] = use_case
    return use_case


@click.command(
    "search",
    help="Run a multi-source search and emit a JSON summary.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--text", required=True, help="Free-text query string.")
@click.option(
    "--source",
    "source_ids",
    multiple=True,
    required=True,
    help="Adapter id (repeat to query multiple sources, e.g. --source arxiv --source openalex).",
)
@click.option(
    "--year-start",
    type=int,
    default=None,
    help="Inclusive lower bound on publication year.",
)
@click.option(
    "--year-end",
    type=int,
    default=None,
    help="Inclusive upper bound on publication year.",
)
@click.option(
    "--language",
    "languages",
    multiple=True,
    help="ISO 639-1 code (repeat for multiple). Empty means any language.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Optional path to write the full per-source + dedup'd item list as JSON.",
)
@click.pass_context
def search(
    ctx: click.Context,
    text: str,
    source_ids: tuple[str, ...],
    year_start: int | None,
    year_end: int | None,
    languages: tuple[str, ...],
    output_path: Path | None,
) -> None:
    """Run :class:`SearchForStudiesUseCase` and print the result DTO."""
    use_case = _resolve_search_use_case(ctx)
    command = SearchForStudiesCommand(
        text=text,
        source_ids=tuple(source_ids),
        year_start=year_start,
        year_end=year_end,
        languages=tuple(languages),
    )
    result = use_case.execute(command)

    summary = {
        "n_sources_ok": result.n_sources_ok,
        "n_sources_errored": result.n_sources_errored,
        "n_items_total": result.n_items_total,
        "n_items_deduplicated": result.n_items_deduplicated,
        "per_source_status": [
            {
                "source": s.source,
                "method": s.method,
                "n_items": len(s.items),
                "total_results": s.total_results,
            }
            for s in result.per_source
        ],
    }
    click.echo(json.dumps(summary, ensure_ascii=False))

    if output_path is not None:
        full = {
            "per_source": [asdict(s) for s in result.per_source],
            "deduplicated_items": [asdict(i) for i in result.deduplicated_items],
        }
        output_path.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")


def _resolve_search_use_case(ctx: click.Context) -> SearchForStudiesUseCase:
    """Same injection seam as :func:`_resolve_audit_use_case`."""
    obj: dict[str, Any] = ctx.ensure_object(dict)
    cached = obj.get("search_use_case")
    if isinstance(cached, SearchForStudiesUseCase):
        return cached
    use_case = _main.build_search_for_studies_use_case()
    obj["search_use_case"] = use_case
    return use_case
