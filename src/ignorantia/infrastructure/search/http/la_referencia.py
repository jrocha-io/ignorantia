"""``LaReferenciaAdapter`` — VuFind-backed Iberoamerican OA aggregator."""

from __future__ import annotations

from typing import ClassVar

from ignorantia.infrastructure.search.http._vufind_rss import _VuFindRssAdapter


class LaReferenciaAdapter(_VuFindRssAdapter):
    """Adapter for LA Referencia (``lareferencia.info`` VuFind)."""

    source_id = "la_referencia"
    _SEARCH_URL: ClassVar[str] = "https://www.lareferencia.info/vufind/Search/Results"
