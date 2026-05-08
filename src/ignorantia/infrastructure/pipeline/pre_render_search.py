"""``pre_render_search`` — PipelineStep that runs Phase-3 search and persists results.

Per Decisão 34 (chunked-write protocol for large SLRs), the corpus
of search results must leave the conversation context as soon as
possible: written to disk before any synthesis prose is generated
in the same response. This step performs the search via
:class:`SearchOrchestrator` and writes
``<output_dir>/searches.json`` validated against the
``search_full_result`` schema (already published in
:mod:`ignorantia.interface.manifests`).

Downstream steps (extraction, screening, render) read the file from
disk; they never receive the in-memory result tuple. That gives
Claude the freedom to drop the corpus from its context window after
this step returns.

The step contract is the standard v3 :class:`PipelineStep`: a
zero-argument ``fn`` that returns a :class:`StepResult`. Inputs
(orchestrator, queries, output path) are captured in a closure by
the factory.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from ignorantia.application.dtos import (
    SearchForStudiesCommand,
    SearchForStudiesResult,
)
from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.domain.pipeline.value_objects import (
    PipelineStep,
    StepResult,
    StepStatus,
)
from ignorantia.infrastructure.persistence.json_writer import JsonWriter

_DEFAULT_FILENAME = "searches.json"


def build_pre_render_search_step(
    *,
    use_case: SearchForStudiesUseCase,
    commands: Sequence[SearchForStudiesCommand],
    output_dir: Path,
    filename: str = _DEFAULT_FILENAME,
) -> PipelineStep:
    """Build the search-and-persist step for the render pipeline.

    Args:
        use_case: Pre-wired :class:`SearchForStudiesUseCase`. Tests
            inject a stub-orchestrator-backed instance; production
            uses ``build_search_for_studies_use_case()``.
        commands: One :class:`SearchForStudiesCommand` per query. The
            step runs them sequentially and merges per-source results
            so the final ``searches.json`` carries the full union.
        output_dir: Directory where ``searches.json`` is written.
            Created if missing.
        filename: Override the default ``searches.json`` filename
            (useful for tests or for emitting under a custom name).

    Returns:
        A :class:`PipelineStep` named ``pre_render_search`` whose
        ``fn`` runs the searches and writes the JSON.
    """
    if not commands:
        raise ValueError(
            "build_pre_render_search_step: at least one SearchForStudiesCommand "
            "is required (got empty sequence)"
        )

    target = output_dir / filename

    def _fn() -> StepResult:
        merged_per_source = []
        merged_dedup: list[dict[str, object]] = []
        seen_titles: set[str] = set()
        n_total_pre_dedup = 0
        n_errored = 0

        for command in commands:
            result: SearchForStudiesResult = use_case.execute(command)
            for src in result.per_source:
                merged_per_source.append(asdict(src))
            for item in result.deduplicated_items:
                # Cross-query dedup by title — preserves the first
                # encountered entry. Per-query orchestrator dedup
                # already collapsed within-query duplicates.
                if item.title in seen_titles:
                    continue
                seen_titles.add(item.title)
                merged_dedup.append(asdict(item))
            n_total_pre_dedup += result.n_items_total
            n_errored += result.n_sources_errored

        payload = {
            "per_source": merged_per_source,
            "deduplicated_items": merged_dedup,
        }
        bytes_written = JsonWriter().write_json(
            payload, schema_name="search_full_result", path=target
        )
        n_unique = len(merged_dedup)
        n_sources_ok = len(merged_per_source) - n_errored
        return StepResult(
            name="pre_render_search",
            status=StepStatus.OK,
            artifact=str(target),
            message=(
                f"Wrote {bytes_written} bytes; "
                f"{len(commands)} queries, {n_sources_ok} sources ok, "
                f"{n_errored} errored, "
                f"{n_total_pre_dedup} items pre-dedup, "
                f"{n_unique} after cross-query dedup"
            ),
        )

    return PipelineStep(
        name="pre_render_search",
        label="Pre-render search (Phase 3 corpus persist)",
        fn=_fn,
    )
