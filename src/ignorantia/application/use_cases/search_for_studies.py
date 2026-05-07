"""``SearchForStudiesUseCase`` — orchestrate a multi-adapter search run.

Wraps the F3 :class:`SearchOrchestrator` behind the F6 use-case
pattern. The use case takes a flat :class:`SearchForStudiesCommand`
DTO from the interface layer, translates it to a domain
:class:`SearchQuery`, runs the orchestrator over the requested
adapter ids, and returns a flat :class:`SearchForStudiesResult` DTO
with per-source results plus a deduplicated cross-source item list.

The orchestrator is injected at construction (DIP). Production
wiring binds it to a ``SearchOrchestrator`` constructed with a real
``AdapterFactory``; tests pass an orchestrator built over a stub
factory.
"""

from __future__ import annotations

from ignorantia.application.dtos import (
    FetchedItemDto,
    SearchForStudiesCommand,
    SearchForStudiesResult,
    SearchSourceResultDto,
)
from ignorantia.domain.search.entities import (
    FetchedItem,
    SearchQuery,
    SearchResult,
)
from ignorantia.domain.search.services.search_orchestrator import (
    SearchOrchestrator,
)
from ignorantia.domain.search.value_objects import Method


class SearchForStudiesUseCase:
    """Run a search across the requested adapters and return a result DTO."""

    def __init__(self, *, orchestrator: SearchOrchestrator) -> None:
        """Wire the use case to a :class:`SearchOrchestrator`."""
        self._orchestrator = orchestrator

    def execute(self, command: SearchForStudiesCommand) -> SearchForStudiesResult:
        """Run the orchestrator and convert the domain results to DTOs."""
        query = SearchQuery(
            text=command.text,
            year_start=command.year_start,
            year_end=command.year_end,
            languages=command.languages,
        )
        per_source = self._orchestrator.run(query, command.source_ids)
        deduped = self._orchestrator.deduplicated_items(per_source)

        per_source_dtos = tuple(_to_source_dto(per_source[sid]) for sid in command.source_ids)
        n_errored = sum(1 for r in per_source.values() if r.method is Method.REAL_ERROR)
        n_total = sum(len(r.items) for r in per_source.values())
        return SearchForStudiesResult(
            per_source=per_source_dtos,
            deduplicated_items=tuple(_to_item_dto(i) for i in deduped),
            n_sources_ok=len(per_source) - n_errored,
            n_sources_errored=n_errored,
            n_items_total=n_total,
            n_items_deduplicated=len(deduped),
        )


def _to_source_dto(result: SearchResult) -> SearchSourceResultDto:
    return SearchSourceResultDto(
        source=result.source,
        source_tier=str(result.source_tier),
        method=str(result.method),
        items=tuple(_to_item_dto(i) for i in result.items),
        total_results=result.total_results or 0,
    )


def _to_item_dto(item: FetchedItem) -> FetchedItemDto:
    return FetchedItemDto(
        title=item.title,
        source_tier=str(item.source_tier),
        authors=item.authors,
        year=item.year,
        doi=item.doi,
        issn=item.issn,
        isbn=item.isbn,
        venue=item.venue,
        language=item.language,
        is_oa=item.is_oa,
        url=item.url,
        url_for_pdf=item.url_for_pdf,
        abstract=item.abstract,
        publication_type=item.publication_type,
    )
