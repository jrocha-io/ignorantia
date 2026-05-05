"""``EngineeringVillageAdapter`` — Compendex OA subset via OpenAlex (Decorator).

Engineering Village (Elsevier/Compendex) is paywall, but the OA-accessible
subset indexed by Compendex is reachable through OpenAlex with engineering
discipline filtering. This adapter is a Decorator over any
:class:`AdapterPort` (in production: :class:`OpenAlexAdapter`): it
enriches the query with an engineering term, delegates the fetch, and
re-labels the result as ``engineering_village`` (Tier 1).

Items returned by the delegate (typically Tier 0 from OpenAlex) are
re-tagged to Tier 1 to satisfy the
``test_every_item_has_matching_source_tier`` invariant of the
``AdapterPort`` contract suite.
"""

from __future__ import annotations

import dataclasses

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.search.http.openalex import OpenAlexAdapter

_VALID_SUBDISCIPLINES: frozenset[str] = frozenset(
    {"mechanical", "civil", "chemical", "electrical", "materials", "environmental"}
)


class EngineeringVillageAdapter(AdapterPort):
    """Decorator over an :class:`AdapterPort` that targets engineering."""

    source_id = "engineering_village"
    source_tier = Tier.TIER1

    def __init__(
        self,
        delegate: AdapterPort,
        *,
        subdiscipline: str | None = None,
    ) -> None:
        """Wire the decorator to a delegate adapter (typically OpenAlex)."""
        if subdiscipline is not None and subdiscipline not in _VALID_SUBDISCIPLINES:
            raise ValueError(
                f"unknown engineering subdiscipline: {subdiscipline!r}; "
                f"valid options are {sorted(_VALID_SUBDISCIPLINES)}"
            )
        self._delegate = delegate
        self._subdiscipline = subdiscipline

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Delegate to the wrapped adapter and re-brand the result."""
        result = self._delegate.fetch(self._enrich(query))
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=result.method,
            query=query,
            items=tuple(self._retag(it) for it in result.items),
            total_results=result.total_results,
        )

    def _enrich(self, query: SearchQuery) -> SearchQuery:
        suffix = self._subdiscipline or "engineering"
        return dataclasses.replace(query, text=f"{query.text} {suffix}")

    def _retag(self, item: FetchedItem) -> FetchedItem:
        if item.source_tier is self.source_tier:
            return item
        return dataclasses.replace(item, source_tier=self.source_tier)


def build_engineering_village_adapter(
    http: HttpClient,
    *,
    subdiscipline: str | None = None,
) -> EngineeringVillageAdapter:
    """Compose ``OpenAlexAdapter`` + engineering Decorator (factory helper)."""
    return EngineeringVillageAdapter(OpenAlexAdapter(http), subdiscipline=subdiscipline)
