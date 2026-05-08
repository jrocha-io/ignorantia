"""Click subcommands wired to application use cases.

Each subcommand:

1. Builds (or reuses) a use case via the composition root.
2. Translates Click options to a Command DTO from
   :mod:`ignorantia.application.dtos`.
3. Calls ``use_case.execute(command)``.
4. Prints the Result DTO in a stable, machine-readable form.

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
    ReferenceInputDto,
    RenderManuscriptCommand,
    RunAuditCommand,
    SearchForStudiesCommand,
    SectionInputDto,
)
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
from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat
from ignorantia.infrastructure.persistence.json_writer import JsonWriter
from ignorantia.interface.cli import main as _main
from ignorantia.interface.manifests import validate_manifest


def _emit(manifest_name: str, payload: dict[str, Any]) -> None:
    """Validate ``payload`` against ``manifest_name``'s schema, then echo it.

    Per ``V3_ARCHITECTURE_PLAN.md``: every CLI subcommand validates
    its JSON output before printing it. Drift in the DTO surface
    (or its serialisation) trips the validator and fails the run
    loudly rather than shipping a new wire format silently.
    """
    validate_manifest(manifest_name, payload)
    click.echo(json.dumps(payload, ensure_ascii=False))


def register(cli: click.Group) -> None:
    """Attach every subcommand to ``cli``.

    Called once from :mod:`ignorantia.interface.cli.main` after the
    group is defined. Keeps subcommand registration explicit and
    discoverable in one place.
    """
    cli.add_command(audit)
    cli.add_command(finalize)
    cli.add_command(render)
    cli.add_command(search)


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


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
    _emit(
        "audit_result",
        {
            "timestamp_iso8601": result.timestamp_iso8601,
            "action": result.action,
            "manifest_size": result.manifest_size,
        },
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


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------


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
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help=(
        "Optional manuscript spec (JSON, same shape as `render --input`). "
        "When supplied, the pipeline runs the HTML / LaTeX / DOCX render steps."
    ),
)
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    default=None,
    help="Output directory for render artefacts. Required with --input.",
)
@click.option(
    "--citation-style",
    "citation_style",
    type=click.Choice([s.value for s in CitationStyle], case_sensitive=False),
    default=CitationStyle.APA.value,
    show_default=True,
    help="Citation style used by every render step.",
)
@click.option(
    "--skip-html",
    is_flag=True,
    default=False,
    help="Drop the HTML render step from the registry.",
)
@click.option(
    "--skip-latex",
    is_flag=True,
    default=False,
    help="Drop the LaTeX render step from the registry.",
)
@click.option(
    "--skip-docx",
    is_flag=True,
    default=False,
    help="Drop the DOCX render step (use this when [docx] extra not installed).",
)
@click.pass_context
def finalize(
    ctx: click.Context,
    actor: str,
    input_path: Path | None,
    output_dir: Path | None,
    citation_style: str,
    skip_html: bool,
    skip_latex: bool,
    skip_docx: bool,
) -> None:
    """Run :class:`FinalizePipelineUseCase` and print the result DTO.

    Two modes:

    * Without ``--input``: runs the empty step registry — useful as a
      smoke check that the executor + clock + JSON schema validation
      are wired correctly.
    * With ``--input`` + ``--output-dir``: runs the render pipeline
      (HTML / LaTeX / DOCX, minus the ``--skip-*`` formats) over the
      manuscript at ``--input``, writing artefacts under
      ``--output-dir``.
    """
    if input_path is not None and output_dir is None:
        raise click.BadParameter(
            "--output-dir is required when --input is supplied.",
            param_hint="--output-dir",
        )

    use_case = _resolve_finalize_use_case(
        ctx,
        input_path=input_path,
        output_dir=output_dir,
        citation_style=CitationStyle(citation_style.lower()),
        skip_html=skip_html,
        skip_latex=skip_latex,
        skip_docx=skip_docx,
    )
    command = FinalizePipelineCommand(actor=actor)
    result = use_case.execute(command)
    _emit(
        "finalize_pipeline_result",
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
    )


def _resolve_finalize_use_case(
    ctx: click.Context,
    *,
    input_path: Path | None = None,
    output_dir: Path | None = None,
    citation_style: CitationStyle = CitationStyle.APA,
    skip_html: bool = False,
    skip_latex: bool = False,
    skip_docx: bool = False,
) -> FinalizePipelineUseCase:
    """Resolve the pre-injected use case OR build one for the requested mode.

    Tests inject under ``ctx.obj["finalize_use_case"]``. Production
    chooses between the empty registry (no ``--input``) and the
    render registry pinned to the supplied manuscript.
    """
    obj: dict[str, Any] = ctx.ensure_object(dict)
    cached = obj.get("finalize_use_case")
    if isinstance(cached, FinalizePipelineUseCase):
        return cached
    if input_path is not None and output_dir is not None:
        spec = _read_manuscript_spec(input_path)
        manuscript = _spec_to_manuscript(spec)
        return _main.build_render_pipeline_use_case(
            manuscript=manuscript,
            output_dir=output_dir,
            citation_style=citation_style,
            skip_html=skip_html,
            skip_latex=skip_latex,
            skip_docx=skip_docx,
        )
    use_case = _main.build_finalize_pipeline_use_case()
    obj["finalize_use_case"] = use_case
    return use_case


def _spec_to_manuscript(spec: dict[str, Any]) -> ManuscriptDoc:
    """Translate a wire-format manuscript JSON into a domain :class:`ManuscriptDoc`.

    Reuses :func:`_build_render_command` so the manuscript shape is
    identical to what the ``render`` subcommand consumes — the
    ``finalize`` and ``render`` paths cannot drift.
    """
    command = _build_render_command(spec)
    builder = (
        ManuscriptDoc.builder()
        .title(command.title)
        .abstract(command.abstract)
        .language(command.language)
        .keywords(command.keywords)
    )
    for section in command.sections:
        builder = builder.add_section(_section_dto_to_section(section))
    for reference in command.references:
        builder = builder.add_reference(_reference_dto_to_reference(reference))
    return builder.build()


def _section_dto_to_section(dto: SectionInputDto) -> Section:
    return Section(id=dto.id, title=dto.title, body_md=dto.body_md)


def _reference_dto_to_reference(dto: ReferenceInputDto) -> Reference:
    return Reference(
        type=dto.type,
        title=dto.title,
        authors=dto.authors,
        year=dto.year,
        venue=dto.venue,
        volume=dto.volume,
        issue=dto.issue,
        pages=dto.pages,
        doi=dto.doi,
        url=dto.url,
        accessed=dto.accessed,
        location=dto.location,
        publisher=dto.publisher,
        chapter_title=dto.chapter_title,
        book_editors=dto.book_editors,
        program=dto.program,
        institution=dto.institution,
        language=dto.language,
    )


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


@click.command(
    "render",
    help="Render a manuscript JSON spec to HTML / LaTeX / DOCX.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to a JSON file with the manuscript spec.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Path to write the rendered artefact.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
    default=OutputFormat.HTML.value,
    show_default=True,
    help="Output format.",
)
@click.option(
    "--citation-style",
    "citation_style",
    type=click.Choice([s.value for s in CitationStyle], case_sensitive=False),
    default=CitationStyle.APA.value,
    show_default=True,
    help="Citation style for the references list.",
)
@click.pass_context
def render(
    ctx: click.Context,
    input_path: Path,
    output_path: Path,
    output_format: str,
    citation_style: str,
) -> None:
    """Render the manuscript at ``--input`` to ``--output``.

    The input is the wire form of :class:`RenderManuscriptCommand`:
    a JSON object with ``title`` (required) plus optional
    ``abstract``, ``language``, ``keywords``, ``sections``,
    ``references``. ``sections`` and ``references`` mirror
    :class:`SectionInputDto` and :class:`ReferenceInputDto`.
    """
    spec = _read_manuscript_spec(input_path)
    command = _build_render_command(spec)
    fmt = OutputFormat(output_format.lower())
    style = CitationStyle(citation_style.lower())

    use_case = _resolve_render_use_case(ctx, fmt, style)
    result = use_case.execute(command)
    output_path.write_bytes(result.artifact_bytes)
    _emit(
        "render_result",
        {
            "output_format": result.output_format,
            "byte_size": result.byte_size,
            "output_path": str(output_path),
        },
    )


def _read_manuscript_spec(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise click.BadParameter(f"could not read --input: {exc}", param_hint="--input") from exc
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(
            f"--input is not valid JSON: {exc.msg}", param_hint="--input"
        ) from exc
    if not isinstance(spec, dict):
        raise click.BadParameter("--input must be a JSON object (dict).", param_hint="--input")
    return spec


def _build_render_command(spec: dict[str, Any]) -> RenderManuscriptCommand:
    sections = tuple(_build_section(s) for s in spec.get("sections", ()))
    references = tuple(_build_reference(r) for r in spec.get("references", ()))
    keywords = tuple(spec.get("keywords", ()))
    try:
        return RenderManuscriptCommand(
            title=spec.get("title", ""),
            abstract=spec.get("abstract", ""),
            language=spec.get("language", "en"),
            keywords=keywords,
            sections=sections,
            references=references,
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--input") from exc


def _build_section(payload: dict[str, Any]) -> SectionInputDto:
    return SectionInputDto(
        id=payload.get("id", ""),
        title=payload.get("title", ""),
        body_md=payload.get("body_md", ""),
    )


def _build_reference(payload: dict[str, Any]) -> ReferenceInputDto:
    authors = payload.get("authors", ())
    book_editors = payload.get("book_editors")
    return ReferenceInputDto(
        type=payload.get("type", ""),
        title=payload.get("title", ""),
        authors=tuple(authors),
        year=payload.get("year"),
        venue=payload.get("venue", ""),
        volume=payload.get("volume"),
        issue=payload.get("issue"),
        pages=payload.get("pages"),
        doi=payload.get("doi"),
        url=payload.get("url"),
        accessed=payload.get("accessed"),
        location=payload.get("location"),
        publisher=payload.get("publisher"),
        chapter_title=payload.get("chapter_title"),
        book_editors=tuple(book_editors) if book_editors is not None else None,
        program=payload.get("program"),
        institution=payload.get("institution"),
        language=payload.get("language", "en"),
    )


def _resolve_render_use_case(
    ctx: click.Context,
    output_format: OutputFormat,
    citation_style: CitationStyle,
) -> RenderManuscriptUseCase:
    """Resolve from ``ctx.obj`` or build via the composition root.

    Tests inject a pre-built use case under ``ctx.obj["render_use_case"]``
    to bypass the renderer / formatter wiring. Production builds a
    fresh use case per invocation since the renderer choice depends
    on CLI options.
    """
    obj: dict[str, Any] = ctx.ensure_object(dict)
    cached = obj.get("render_use_case")
    if isinstance(cached, RenderManuscriptUseCase):
        return cached
    return _main.build_render_manuscript_use_case(output_format, citation_style)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


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
    _emit("search_result", summary)

    if output_path is not None:
        # Full payload — per-source + dedup'd items in their DTO
        # shape — goes through JsonWriter so the schema is enforced
        # before bytes hit disk.
        full = {
            "per_source": [asdict(s) for s in result.per_source],
            "deduplicated_items": [asdict(i) for i in result.deduplicated_items],
        }
        JsonWriter().write_json(full, schema_name="search_full_result", path=output_path)


def _resolve_search_use_case(ctx: click.Context) -> SearchForStudiesUseCase:
    """Same injection seam as :func:`_resolve_audit_use_case`."""
    obj: dict[str, Any] = ctx.ensure_object(dict)
    cached = obj.get("search_use_case")
    if isinstance(cached, SearchForStudiesUseCase):
        return cached
    use_case = _main.build_search_for_studies_use_case()
    obj["search_use_case"] = use_case
    return use_case
