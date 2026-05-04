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
from ignorantia.infrastructure.search.http.sciencedirect_full import (
    ScienceDirectFullAdapter,
)
from ignorantia.infrastructure.search.http.scopus_full import ScopusFullAdapter
from ignorantia.infrastructure.search.http.semantic_scholar import (
    SemanticScholarAdapter,
)
from ignorantia.infrastructure.search.http.springer_full import SpringerFullAdapter
from ignorantia.infrastructure.search.http.wos_full import WosFullAdapter
from ignorantia.infrastructure.search.http.zenodo import ZenodoAdapter

_AdapterBuilder = Callable[[HttpClient], AdapterPort]


_REGISTRY: dict[str, _AdapterBuilder] = {
    "arxiv": ArxivAdapter,
    "bdtd": BdtdAdapter,
    "biorxiv": BioRxivAdapter,
    "crossref": CrossrefAdapter,
    "doaj": DoajAdapter,
    "eric": EricAdapter,
    "europepmc": EuropePmcAdapter,
    "hal": HalAdapter,
    "ieee_full": IeeeFullAdapter,
    "la_referencia": LaReferenciaAdapter,
    "medrxiv": MedRxivAdapter,
    "openalex": OpenAlexAdapter,
    "pubmed": PubMedAdapter,
    "scielo": ScieloAdapter,
    "sciencedirect_full": ScienceDirectFullAdapter,
    "scopus_full": ScopusFullAdapter,
    "semantic_scholar": SemanticScholarAdapter,
    "springer_full": SpringerFullAdapter,
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
