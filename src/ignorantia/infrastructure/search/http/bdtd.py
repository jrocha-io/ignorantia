"""``BdtdAdapter`` — Brazilian Digital Library of Theses and Dissertations.

BDTD shares the VuFind stack with LA Referencia; only the search URL
differs. The shared parser lives in :mod:`._vufind_rss`.
"""

from __future__ import annotations

from typing import ClassVar

from ignorantia.infrastructure.search.http._vufind_rss import _VuFindRssAdapter


class BdtdAdapter(_VuFindRssAdapter):
    """Adapter for BDTD (``bdtd.ibict.br`` VuFind)."""

    source_id = "bdtd"
    _SEARCH_URL: ClassVar[str] = "https://bdtd.ibict.br/vufind/Search/Results"
