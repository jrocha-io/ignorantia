"""Property-based contract tests for :class:`AdapterPort` implementations.

Every concrete adapter, regardless of its source, must satisfy these
invariants. As F3 migrates the remaining 61 adapters, each one is added
to the parametrise list below and the same invariants are enforced
without writing new tests.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http.arxiv import ArxivAdapter
from ignorantia.infrastructure.search.http.crossref import CrossrefAdapter
from ignorantia.infrastructure.search.http.doaj import DoajAdapter
from ignorantia.infrastructure.search.http.openalex import OpenAlexAdapter
from ignorantia.infrastructure.search.http.semantic_scholar import SemanticScholarAdapter


class _StaticHttpClient:
    """Test double that always returns the same canned body."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        return self._body


_EMPTY_ATOM = b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
_EMPTY_CROSSREF = b'{"message": {"items": []}}'
_EMPTY_DOAJ = b'{"results": []}'
_EMPTY_OPENALEX = b'{"results": [], "meta": {"count": 0}}'
_EMPTY_S2 = b'{"data": []}'


def _arxiv_factory() -> AdapterPort:
    return ArxivAdapter(_StaticHttpClient(_EMPTY_ATOM), max_per_page=10, max_results=10)


def _crossref_factory() -> AdapterPort:
    return CrossrefAdapter(_StaticHttpClient(_EMPTY_CROSSREF), max_per_page=10, max_results=10)


def _doaj_factory() -> AdapterPort:
    return DoajAdapter(_StaticHttpClient(_EMPTY_DOAJ), max_results=10)


def _openalex_factory() -> AdapterPort:
    return OpenAlexAdapter(_StaticHttpClient(_EMPTY_OPENALEX), max_results=10)


def _semantic_scholar_factory() -> AdapterPort:
    return SemanticScholarAdapter(_StaticHttpClient(_EMPTY_S2), max_per_page=10, max_results=10)


_ADAPTER_FACTORIES: tuple[Callable[[], AdapterPort], ...] = (
    _arxiv_factory,
    _crossref_factory,
    _doaj_factory,
    _openalex_factory,
    _semantic_scholar_factory,
)


_year_range = st.tuples(
    st.integers(min_value=1900, max_value=2100),
    st.integers(min_value=1900, max_value=2100),
).filter(lambda pair: pair[0] <= pair[1])


@st.composite
def _search_queries(draw: st.DrawFn) -> SearchQuery:
    text = draw(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs", "Cc"), min_codepoint=0x20),
            min_size=1,
            max_size=80,
        )
    )
    has_range = draw(st.booleans())
    if has_range:
        start, end = draw(_year_range)
        return SearchQuery(text=text, year_start=start, year_end=end)
    return SearchQuery(text=text)


@pytest.mark.parametrize("factory", _ADAPTER_FACTORIES, ids=lambda f: f.__name__)
class TestAdapterPortContract:
    """Invariants every adapter must hold for any well-formed query."""

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(query=_search_queries())
    def test_fetch_result_source_matches_adapter(
        self, factory: Callable[[], AdapterPort], query: SearchQuery
    ) -> None:
        adapter = factory()
        result = adapter.fetch(query)
        assert result.source == adapter.source_id

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(query=_search_queries())
    def test_fetch_result_tier_matches_adapter(
        self, factory: Callable[[], AdapterPort], query: SearchQuery
    ) -> None:
        adapter = factory()
        result = adapter.fetch(query)
        assert result.source_tier is adapter.source_tier

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(query=_search_queries())
    def test_every_item_has_matching_source_tier(
        self, factory: Callable[[], AdapterPort], query: SearchQuery
    ) -> None:
        adapter = factory()
        result = adapter.fetch(query)
        assert all(item.source_tier is adapter.source_tier for item in result.items)

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(query=_search_queries())
    def test_total_results_is_at_least_items_length(
        self, factory: Callable[[], AdapterPort], query: SearchQuery
    ) -> None:
        adapter = factory()
        result = adapter.fetch(query)
        assert result.total_results is not None
        assert result.total_results >= len(result.items)


class TestAdapterMetadataNonEmpty:
    @pytest.mark.parametrize("factory", _ADAPTER_FACTORIES, ids=lambda f: f.__name__)
    def test_source_id_is_non_empty(self, factory: Callable[[], AdapterPort]) -> None:
        assert factory().source_id

    @pytest.mark.parametrize("factory", _ADAPTER_FACTORIES, ids=lambda f: f.__name__)
    def test_source_tier_is_a_tier_instance(self, factory: Callable[[], AdapterPort]) -> None:
        assert isinstance(factory().source_tier, Tier)
