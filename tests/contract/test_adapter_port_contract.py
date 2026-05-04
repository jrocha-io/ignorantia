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
from ignorantia.infrastructure.search.http.bdtd import BdtdAdapter
from ignorantia.infrastructure.search.http.biorxiv import BioRxivAdapter, MedRxivAdapter
from ignorantia.infrastructure.search.http.crossref import CrossrefAdapter
from ignorantia.infrastructure.search.http.doaj import DoajAdapter
from ignorantia.infrastructure.search.http.eric import EricAdapter
from ignorantia.infrastructure.search.http.europepmc import EuropePmcAdapter
from ignorantia.infrastructure.search.http.hal import HalAdapter
from ignorantia.infrastructure.search.http.ieee_full import IeeeFullAdapter
from ignorantia.infrastructure.search.http.la_referencia import LaReferenciaAdapter
from ignorantia.infrastructure.search.http.openalex import OpenAlexAdapter
from ignorantia.infrastructure.search.http.pubmed import PubMedAdapter
from ignorantia.infrastructure.search.http.scielo import ScieloAdapter
from ignorantia.infrastructure.search.http.scopus_full import ScopusFullAdapter
from ignorantia.infrastructure.search.http.semantic_scholar import SemanticScholarAdapter
from ignorantia.infrastructure.search.http.zenodo import ZenodoAdapter


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
_EMPTY_BIORXIV = b'{"collection": []}'
_EMPTY_EUROPEPMC = b'{"resultList": {"result": []}, "hitCount": 0}'
_EMPTY_PUBMED = b'{"esearchresult": {"idlist": []}}'
_EMPTY_ZENODO = b'{"hits": {"hits": [], "total": 0}}'
_EMPTY_RSS = b"<rss><channel></channel></rss>"
_EMPTY_SOLR = b'{"response": {"docs": []}}'


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


def _biorxiv_factory() -> AdapterPort:
    return BioRxivAdapter(_StaticHttpClient(_EMPTY_BIORXIV), max_pages=1, max_results=10)


def _medrxiv_factory() -> AdapterPort:
    return MedRxivAdapter(_StaticHttpClient(_EMPTY_BIORXIV), max_pages=1, max_results=10)


def _europepmc_factory() -> AdapterPort:
    return EuropePmcAdapter(_StaticHttpClient(_EMPTY_EUROPEPMC), max_results=10)


def _pubmed_factory() -> AdapterPort:
    return PubMedAdapter(_StaticHttpClient(_EMPTY_PUBMED), max_results=10)


def _zenodo_factory() -> AdapterPort:
    return ZenodoAdapter(_StaticHttpClient(_EMPTY_ZENODO), max_results=10)


def _la_referencia_factory() -> AdapterPort:
    return LaReferenciaAdapter(_StaticHttpClient(_EMPTY_RSS), max_results=10)


def _bdtd_factory() -> AdapterPort:
    return BdtdAdapter(_StaticHttpClient(_EMPTY_RSS), max_results=10)


def _scielo_factory() -> AdapterPort:
    return ScieloAdapter(_StaticHttpClient(_EMPTY_SOLR), max_per_page=10, max_results=10)


def _hal_factory() -> AdapterPort:
    return HalAdapter(_StaticHttpClient(_EMPTY_SOLR), max_results=10)


def _eric_factory() -> AdapterPort:
    return EricAdapter(_StaticHttpClient(_EMPTY_SOLR), max_results=10)


_EMPTY_SCOPUS = b'{"search-results": {"entry": [], "opensearch:totalResults": "0"}}'
_EMPTY_IEEE = b'{"articles": [], "total_records": 0}'


def _scopus_full_factory() -> AdapterPort:
    return ScopusFullAdapter(_StaticHttpClient(_EMPTY_SCOPUS), api_key="K", max_results=10)


def _ieee_full_factory() -> AdapterPort:
    return IeeeFullAdapter(_StaticHttpClient(_EMPTY_IEEE), api_key="K", max_results=10)


_ADAPTER_FACTORIES: tuple[Callable[[], AdapterPort], ...] = (
    _arxiv_factory,
    _crossref_factory,
    _doaj_factory,
    _openalex_factory,
    _semantic_scholar_factory,
    _biorxiv_factory,
    _medrxiv_factory,
    _europepmc_factory,
    _pubmed_factory,
    _zenodo_factory,
    _la_referencia_factory,
    _bdtd_factory,
    _scielo_factory,
    _hal_factory,
    _eric_factory,
    _scopus_full_factory,
    _ieee_full_factory,
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
