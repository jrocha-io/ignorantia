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
from ignorantia.infrastructure.search.http.acm_full import AcmFullAdapter
from ignorantia.infrastructure.search.http.arxiv import ArxivAdapter
from ignorantia.infrastructure.search.http.bdtd import BdtdAdapter
from ignorantia.infrastructure.search.http.biorxiv import BioRxivAdapter, MedRxivAdapter
from ignorantia.infrastructure.search.http.catalogo_teses_capes import (
    CatalogoTesesCapesAdapter,
)
from ignorantia.infrastructure.search.http.cinahl_full import CinahlFullAdapter
from ignorantia.infrastructure.search.http.clacso import ClacsoAdapter
from ignorantia.infrastructure.search.http.clinicaltrials_gov import (
    ClinicalTrialsGovAdapter,
)
from ignorantia.infrastructure.search.http.cochrane_central import CochraneCentralAdapter
from ignorantia.infrastructure.search.http.core import CoreAdapter
from ignorantia.infrastructure.search.http.crossref import CrossrefAdapter
from ignorantia.infrastructure.search.http.dabi import DabiAdapter
from ignorantia.infrastructure.search.http.dblp import DblpAdapter
from ignorantia.infrastructure.search.http.dialnet import DialnetAdapter
from ignorantia.infrastructure.search.http.dimensions import DimensionsAdapter
from ignorantia.infrastructure.search.http.doaj import DoajAdapter
from ignorantia.infrastructure.search.http.e_lis import ELisAdapter
from ignorantia.infrastructure.search.http.edarxiv import EdArxivAdapter
from ignorantia.infrastructure.search.http.embase import EmbaseAdapter
from ignorantia.infrastructure.search.http.engineering_village import (
    EngineeringVillageAdapter,
)
from ignorantia.infrastructure.search.http.eric import EricAdapter
from ignorantia.infrastructure.search.http.europepmc import EuropePmcAdapter
from ignorantia.infrastructure.search.http.hal import HalAdapter
from ignorantia.infrastructure.search.http.hein_online import HeinOnlineAdapter
from ignorantia.infrastructure.search.http.ieee_full import IeeeFullAdapter
from ignorantia.infrastructure.search.http.jstor_full import JstorFullAdapter
from ignorantia.infrastructure.search.http.jstor_oa import JstorOaAdapter
from ignorantia.infrastructure.search.http.la_referencia import LaReferenciaAdapter
from ignorantia.infrastructure.search.http.lilacs import LilacsAdapter
from ignorantia.infrastructure.search.http.oapen import OapenAdapter
from ignorantia.infrastructure.search.http.openalex import OpenAlexAdapter
from ignorantia.infrastructure.search.http.osf_preprints import OsfPreprintsAdapter
from ignorantia.infrastructure.search.http.pepsic import PepsicAdapter
from ignorantia.infrastructure.search.http.periodicos_capes import (
    PeriodicosCapesAdapter,
)
from ignorantia.infrastructure.search.http.philarchive import PhilArchiveAdapter
from ignorantia.infrastructure.search.http.proquest_full import ProquestFullAdapter
from ignorantia.infrastructure.search.http.proquest_oa import ProquestOaAdapter
from ignorantia.infrastructure.search.http.psycinfo_full import PsycInfoFullAdapter
from ignorantia.infrastructure.search.http.pubmed import PubMedAdapter
from ignorantia.infrastructure.search.http.pubmed_central import PubMedCentralAdapter
from ignorantia.infrastructure.search.http.redalyc import RedalycAdapter
from ignorantia.infrastructure.search.http.redib import RedibAdapter
from ignorantia.infrastructure.search.http.sage_full import SageFullAdapter
from ignorantia.infrastructure.search.http.scielo import ScieloAdapter
from ignorantia.infrastructure.search.http.scielo_preprints import (
    ScieloPreprintsAdapter,
)
from ignorantia.infrastructure.search.http.sciencedirect_full import (
    ScienceDirectFullAdapter,
)
from ignorantia.infrastructure.search.http.scioteca import SciotecaAdapter
from ignorantia.infrastructure.search.http.scopus_full import ScopusFullAdapter
from ignorantia.infrastructure.search.http.semantic_scholar import SemanticScholarAdapter
from ignorantia.infrastructure.search.http.spell import SpellAdapter
from ignorantia.infrastructure.search.http.springer_full import SpringerFullAdapter
from ignorantia.infrastructure.search.http.ssrn_full import SsrnFullAdapter
from ignorantia.infrastructure.search.http.wiley_tdm import WileyTdmAdapter
from ignorantia.infrastructure.search.http.wos_full import WosFullAdapter
from ignorantia.infrastructure.search.http.zenodo import ZenodoAdapter


class _StaticHttpClient:
    """Test double that always returns the same canned body for GET or POST."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        return self._body

    def post(
        self,
        url: str,
        *,
        data: bytes,
        headers: object | None = None,
    ) -> bytes:
        del url, data, headers
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
_EMPTY_DBLP = b'{"result": {"hits": {"hit": []}}}'
_EMPTY_PHIL = b'{"results": []}'
_EMPTY_JSTOR_OA = b'{"results": []}'
_EMPTY_OAPEN = b"[]"
_EMPTY_SOLR = b'{"response": {"docs": []}}'
_EMPTY_EMBASE = b'{"results": {"article": []}}'
_EMPTY_SSRN = b'{"results": [], "meta": {"count": 0}}'
_EMPTY_CTGOV = b'{"studies": [], "totalCount": 0}'
_EMPTY_CORE = b'{"results": [], "totalHits": 0}'
_EMPTY_DIMENSIONS = b'{"publications": []}'


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


def _pubmed_central_factory() -> AdapterPort:
    return PubMedCentralAdapter(_StaticHttpClient(_EMPTY_PUBMED), max_results=10)


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
_EMPTY_SPRINGER = b'{"records": []}'
_EMPTY_WOS = b'{"hits": [], "metadata": {"total": 0}}'
_EMPTY_CROSSREF_MEMBER = b'{"message": {"items": [], "total-results": 0}}'
_EMPTY_OSF = b'{"data": []}'


def _scopus_full_factory() -> AdapterPort:
    return ScopusFullAdapter(_StaticHttpClient(_EMPTY_SCOPUS), api_key="K", max_results=10)


def _ieee_full_factory() -> AdapterPort:
    return IeeeFullAdapter(_StaticHttpClient(_EMPTY_IEEE), api_key="K", max_results=10)


def _sciencedirect_full_factory() -> AdapterPort:
    return ScienceDirectFullAdapter(_StaticHttpClient(_EMPTY_SCOPUS), api_key="K", max_results=10)


def _springer_full_factory() -> AdapterPort:
    return SpringerFullAdapter(_StaticHttpClient(_EMPTY_SPRINGER), api_key="K", max_results=10)


def _wos_full_factory() -> AdapterPort:
    return WosFullAdapter(_StaticHttpClient(_EMPTY_WOS), api_key="K", max_results=10)


def _sage_full_factory() -> AdapterPort:
    return SageFullAdapter(_StaticHttpClient(_EMPTY_CROSSREF_MEMBER), api_key="K", max_results=10)


def _acm_full_factory() -> AdapterPort:
    return AcmFullAdapter(_StaticHttpClient(_EMPTY_CROSSREF_MEMBER), api_key="K", max_results=10)


def _wiley_tdm_factory() -> AdapterPort:
    return WileyTdmAdapter(_StaticHttpClient(_EMPTY_CROSSREF_MEMBER), api_key="K", max_results=10)


def _dblp_factory() -> AdapterPort:
    return DblpAdapter(_StaticHttpClient(_EMPTY_DBLP), max_per_page=10, max_results=10)


def _philarchive_factory() -> AdapterPort:
    return PhilArchiveAdapter(_StaticHttpClient(_EMPTY_PHIL), max_results=10)


def _jstor_oa_factory() -> AdapterPort:
    return JstorOaAdapter(_StaticHttpClient(_EMPTY_JSTOR_OA), max_results=10)


def _oapen_factory() -> AdapterPort:
    return OapenAdapter(_StaticHttpClient(_EMPTY_OAPEN), max_results=10)


def _osf_preprints_factory() -> AdapterPort:
    return OsfPreprintsAdapter(_StaticHttpClient(_EMPTY_OSF), max_results=10)


def _edarxiv_factory() -> AdapterPort:
    return EdArxivAdapter(_StaticHttpClient(_EMPTY_OSF), max_results=10)


def _cinahl_full_factory() -> AdapterPort:
    return CinahlFullAdapter(_StaticHttpClient(b""), max_results=10)


def _hein_online_factory() -> AdapterPort:
    return HeinOnlineAdapter(_StaticHttpClient(b""), max_results=10)


def _psycinfo_full_factory() -> AdapterPort:
    return PsycInfoFullAdapter(_StaticHttpClient(b""), max_results=10)


def _embase_factory() -> AdapterPort:
    return EmbaseAdapter(_StaticHttpClient(_EMPTY_EMBASE), api_key="K", max_results=10)


def _engineering_village_factory() -> AdapterPort:
    return EngineeringVillageAdapter(
        OpenAlexAdapter(_StaticHttpClient(_EMPTY_OPENALEX), max_results=10)
    )


def _ssrn_full_factory() -> AdapterPort:
    return SsrnFullAdapter(_StaticHttpClient(_EMPTY_SSRN), max_results=10)


def _clinicaltrials_gov_factory() -> AdapterPort:
    return ClinicalTrialsGovAdapter(_StaticHttpClient(_EMPTY_CTGOV), max_results=10)


def _cochrane_central_factory() -> AdapterPort:
    return CochraneCentralAdapter(_StaticHttpClient(b""))


def _proquest_oa_factory() -> AdapterPort:
    return ProquestOaAdapter(_StaticHttpClient(b""))


def _proquest_full_factory() -> AdapterPort:
    return ProquestFullAdapter(_StaticHttpClient(b""), max_results=10)


def _jstor_full_factory() -> AdapterPort:
    return JstorFullAdapter(_StaticHttpClient(b""), max_results=10)


def _core_factory() -> AdapterPort:
    return CoreAdapter(_StaticHttpClient(_EMPTY_CORE), max_results=10)


def _dimensions_factory() -> AdapterPort:
    return DimensionsAdapter(_StaticHttpClient(_EMPTY_DIMENSIONS), api_key="K", max_results=10)


def _lilacs_factory() -> AdapterPort:
    return LilacsAdapter(_StaticHttpClient(b""))


def _pepsic_factory() -> AdapterPort:
    return PepsicAdapter(_StaticHttpClient(b""))


def _redalyc_factory() -> AdapterPort:
    return RedalycAdapter(_StaticHttpClient(b""))


_EMPTY_REDIB = b'{"results": [], "total": 0}'


def _redib_factory() -> AdapterPort:
    return RedibAdapter(_StaticHttpClient(_EMPTY_REDIB), api_key="K", max_results=10)


def _dialnet_factory() -> AdapterPort:
    return DialnetAdapter(_StaticHttpClient(b""))


def _dabi_factory() -> AdapterPort:
    return DabiAdapter(_StaticHttpClient(b""))


def _spell_factory() -> AdapterPort:
    return SpellAdapter(_StaticHttpClient(b""))


def _periodicos_capes_factory() -> AdapterPort:
    return PeriodicosCapesAdapter(_StaticHttpClient(b""))


def _clacso_factory() -> AdapterPort:
    return ClacsoAdapter(_StaticHttpClient(b""))


def _e_lis_factory() -> AdapterPort:
    return ELisAdapter(_StaticHttpClient(b""))


def _scielo_preprints_factory() -> AdapterPort:
    return ScieloPreprintsAdapter(_StaticHttpClient(b""))


def _catalogo_teses_capes_factory() -> AdapterPort:
    return CatalogoTesesCapesAdapter(_StaticHttpClient(b""))


def _scioteca_factory() -> AdapterPort:
    return SciotecaAdapter(_StaticHttpClient(b""))


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
    _pubmed_central_factory,
    _zenodo_factory,
    _la_referencia_factory,
    _bdtd_factory,
    _scielo_factory,
    _hal_factory,
    _eric_factory,
    _scopus_full_factory,
    _ieee_full_factory,
    _sciencedirect_full_factory,
    _springer_full_factory,
    _wos_full_factory,
    _sage_full_factory,
    _acm_full_factory,
    _wiley_tdm_factory,
    _dblp_factory,
    _philarchive_factory,
    _jstor_oa_factory,
    _oapen_factory,
    _osf_preprints_factory,
    _edarxiv_factory,
    _cinahl_full_factory,
    _hein_online_factory,
    _psycinfo_full_factory,
    _embase_factory,
    _engineering_village_factory,
    _ssrn_full_factory,
    _clinicaltrials_gov_factory,
    _cochrane_central_factory,
    _proquest_oa_factory,
    _proquest_full_factory,
    _jstor_full_factory,
    _core_factory,
    _dimensions_factory,
    _lilacs_factory,
    _pepsic_factory,
    _redalyc_factory,
    _redib_factory,
    _dialnet_factory,
    _dabi_factory,
    _spell_factory,
    _periodicos_capes_factory,
    _clacso_factory,
    _e_lis_factory,
    _scielo_preprints_factory,
    _catalogo_teses_capes_factory,
    _scioteca_factory,
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
