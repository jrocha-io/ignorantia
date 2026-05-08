"""``VenueClassifierPort`` — contract for venue/journal classifiers.

Venue classification answers a different question than search adapters:
given a manuscript's title + abstract, *which journals would accept it?*
Implementations include MEDLINE-trained models such as JANE
(``jane.biosemantics.org``) and similar tools.

This port lives in the SLR bounded context (not search), because venue
selection is part of the manuscript-submission lifecycle, not the
study-discovery pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.slr.value_objects import VenueSuggestion


class VenueClassifierPort(ABC):
    """Abstract base class for venue classifiers.

    Implementations live in ``ignorantia.infrastructure.slr`` (or any
    other adapter package) and must subclass this ABC. The application
    layer talks to classifiers through this port and never knows the
    concrete implementation, satisfying the *Dependency Inversion
    Principle*.
    """

    @abstractmethod
    def suggest_venues(
        self, text: str, *, max_suggestions: int = 10
    ) -> tuple[VenueSuggestion, ...]:
        """Return ranked venue suggestions for the given manuscript text.

        Args:
            text: Combined manuscript title + abstract.
            max_suggestions: Cap on returned suggestions (rank-1 is best).

        Returns:
            A tuple of :class:`VenueSuggestion`, ordered by ``ranking``
            ascending. May be empty when the classifier has no usable
            backend (e.g. an HTML-only source forbidden by DD-6).
        """
