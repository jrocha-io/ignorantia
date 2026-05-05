"""``AdapterFactory`` — concrete :class:`AdapterFactoryPort` implementation.

This is the *composition root* for the search bounded context. Every
adapter the system can use is registered exactly once in
:attr:`_REGISTRY`; adding a new database in F3 means adding a new entry
here and nothing else (Open/Closed).
"""

from __future__ import annotations

from collections.abc import Callable

from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.infrastructure.http_client import HttpClient
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
from ignorantia.infrastructure.search.http.eric import EricAdapter
from ignorantia.infrastructure.search.http.europepmc import EuropePmcAdapter
from ignorantia.infrastructure.search.http.google_scholar_serpapi import (
    GoogleScholarSerpApiAdapter,
)
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
from ignorantia.infrastructure.search.http.semantic_scholar import (
    SemanticScholarAdapter,
)
from ignorantia.infrastructure.search.http.spell import SpellAdapter
from ignorantia.infrastructure.search.http.springer_full import SpringerFullAdapter
from ignorantia.infrastructure.search.http.ssrn_full import SsrnFullAdapter
from ignorantia.infrastructure.search.http.wiley_tdm import WileyTdmAdapter
from ignorantia.infrastructure.search.http.wos_full import WosFullAdapter
from ignorantia.infrastructure.search.http.zenodo import ZenodoAdapter

_AdapterBuilder = Callable[[HttpClient], AdapterPort]


_REGISTRY: dict[str, _AdapterBuilder] = {
    "acm_full": AcmFullAdapter,
    "arxiv": ArxivAdapter,
    "bdtd": BdtdAdapter,
    "biorxiv": BioRxivAdapter,
    "catalogo_teses_capes": CatalogoTesesCapesAdapter,
    "cinahl_full": CinahlFullAdapter,
    "clacso": ClacsoAdapter,
    "clinicaltrials_gov": ClinicalTrialsGovAdapter,
    "cochrane_central": CochraneCentralAdapter,
    "core": CoreAdapter,
    "crossref": CrossrefAdapter,
    "dabi": DabiAdapter,
    "dblp": DblpAdapter,
    "dialnet": DialnetAdapter,
    "dimensions": DimensionsAdapter,
    "doaj": DoajAdapter,
    "e_lis": ELisAdapter,
    "edarxiv": EdArxivAdapter,
    "embase": EmbaseAdapter,
    "eric": EricAdapter,
    "europepmc": EuropePmcAdapter,
    "google_scholar_serpapi": GoogleScholarSerpApiAdapter,
    "hal": HalAdapter,
    "hein_online": HeinOnlineAdapter,
    "ieee_full": IeeeFullAdapter,
    "jstor_full": JstorFullAdapter,
    "jstor_oa": JstorOaAdapter,
    "la_referencia": LaReferenciaAdapter,
    "lilacs": LilacsAdapter,
    "medrxiv": MedRxivAdapter,
    "oapen": OapenAdapter,
    "openalex": OpenAlexAdapter,
    "osf_preprints": OsfPreprintsAdapter,
    "pepsic": PepsicAdapter,
    "periodicos_capes": PeriodicosCapesAdapter,
    "philarchive": PhilArchiveAdapter,
    "proquest_full": ProquestFullAdapter,
    "proquest_oa": ProquestOaAdapter,
    "psycinfo_full": PsycInfoFullAdapter,
    "pubmed": PubMedAdapter,
    "pubmed_central": PubMedCentralAdapter,
    "redalyc": RedalycAdapter,
    "sage_full": SageFullAdapter,
    "scielo": ScieloAdapter,
    "scielo_preprints": ScieloPreprintsAdapter,
    "sciencedirect_full": ScienceDirectFullAdapter,
    "scioteca": SciotecaAdapter,
    "scopus_full": ScopusFullAdapter,
    "semantic_scholar": SemanticScholarAdapter,
    "spell": SpellAdapter,
    "springer_full": SpringerFullAdapter,
    "ssrn_full": SsrnFullAdapter,
    "wiley_tdm": WileyTdmAdapter,
    "wos_full": WosFullAdapter,
    "zenodo": ZenodoAdapter,
}


class AdapterFactory(AdapterFactoryPort):
    """Build adapters on demand, sharing a single :class:`HttpClient`."""

    def __init__(self, http: HttpClient) -> None:
        """Wire the factory to the shared HTTP client."""
        self._http = http

    def create(self, source_id: str) -> AdapterPort:
        """Return a fresh adapter for ``source_id``.

        Raises:
            KeyError: when ``source_id`` is not registered.
        """
        try:
            builder = _REGISTRY[source_id]
        except KeyError as exc:
            raise KeyError(f"No adapter registered for source: {source_id!r}") from exc
        return builder(self._http)

    @staticmethod
    def known_sources() -> tuple[str, ...]:
        """Return every registered source identifier in registration order."""
        return tuple(_REGISTRY)
