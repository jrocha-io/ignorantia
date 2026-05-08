"""``JaneVenueClassifier`` — JANE (Journal/Author Name Estimator) stub.

JANE (``jane.biosemantics.org``) is a MEDLINE-trained model that takes a
manuscript title + abstract and returns ranked candidate journals. v2
posted form-encoded text and parsed the resulting HTML page; in v3 that
violates DD-6 (no HTML scraping) because JANE exposes no JSON or REST
API.

This stub satisfies :class:`VenueClassifierPort` and always returns an
empty tuple. It exists so the F8 submission workflow can wire the port
without conditional logic; when JANE (or a successor) ships a structured
API, replace the body of :meth:`suggest_venues`.
"""

from __future__ import annotations

from ignorantia.domain.slr.ports.venue_classifier_port import VenueClassifierPort
from ignorantia.domain.slr.value_objects import VenueSuggestion


class JaneVenueClassifier(VenueClassifierPort):
    """Stub adapter for JANE; always returns ``()`` per DD-6."""

    def suggest_venues(
        self, text: str, *, max_suggestions: int = 10
    ) -> tuple[VenueSuggestion, ...]:
        """Return an empty tuple; JANE has no structured API in v3."""
        del text, max_suggestions
        return ()
