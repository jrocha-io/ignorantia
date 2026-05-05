"""``PubMedCentralAdapter`` — NCBI PubMed Central via E-utilities (db=pmc).

PMC is the OA full-text repository underlying PubMed; everything indexed
in PMC is open access by definition. This adapter inherits the
two-call ``esearch`` / ``esummary`` protocol from
:class:`~ignorantia.infrastructure.search.http.pubmed.PubMedAdapter`,
overriding only:

* ``_DB = "pmc"``
* :attr:`source_id` and :attr:`source_tier`
* :meth:`_canonical_url` — PMC's record URL pattern
* :meth:`_pdf_url_from_record` — PMC pdf URL
* :meth:`_record_is_oa` — always ``True`` for PMC
"""

from __future__ import annotations

from typing import Any, ClassVar

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http.pubmed import PubMedAdapter


class PubMedCentralAdapter(PubMedAdapter):
    """Adapter for NCBI PubMed Central (db=pmc) via the E-utilities API."""

    source_id = "pubmed_central"
    source_tier = Tier.TIER1
    _DB: ClassVar[str] = "pmc"

    def _canonical_url(self, record_id: str) -> str | None:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{record_id}/"

    def _pdf_url_from_record(self, pmcid: str | None) -> str | None:
        # PMC's canonical record URL *is* the full-text landing — no
        # separate PDF endpoint exists for most items, so we return the
        # same URL pattern. Callers that want the PDF specifically can
        # append ``pdf/`` themselves; not every record has that variant.
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else None

    def _record_is_oa(self, record: dict[str, Any], pmcid: str | None) -> bool:
        del record, pmcid
        return True
