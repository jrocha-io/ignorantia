"""``EdArxivAdapter`` — EdArXiv education preprints (OSF-hosted).

EdArXiv is one of the themed preprint servers on OSF. The adapter
inherits from :class:`OsfPreprintsAdapter` and only overrides the
``_PROVIDER`` filter and the ``source_id`` so it appears as a distinct
source in manifests.
"""

from __future__ import annotations

from typing import ClassVar

from ignorantia.infrastructure.search.http.osf_preprints import OsfPreprintsAdapter


class EdArxivAdapter(OsfPreprintsAdapter):
    """Adapter for EdArXiv via OSF (``filter[provider]=edarxiv``)."""

    source_id = "edarxiv"
    _PROVIDER: ClassVar[str | None] = "edarxiv"
