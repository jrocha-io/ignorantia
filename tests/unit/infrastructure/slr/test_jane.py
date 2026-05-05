"""Unit tests for :class:`JaneVenueClassifier`."""

from __future__ import annotations

from ignorantia.domain.slr.ports.venue_classifier_port import VenueClassifierPort
from ignorantia.infrastructure.slr.jane import JaneVenueClassifier


class TestJaneVenueClassifier:
    def test_implements_port(self) -> None:
        assert isinstance(JaneVenueClassifier(), VenueClassifierPort)

    def test_returns_empty_tuple(self) -> None:
        result = JaneVenueClassifier().suggest_venues("a title and abstract")
        assert result == ()

    def test_max_suggestions_argument_accepted_and_ignored(self) -> None:
        result = JaneVenueClassifier().suggest_venues("text", max_suggestions=5)
        assert result == ()

    def test_returns_tuple_type(self) -> None:
        result = JaneVenueClassifier().suggest_venues("text")
        assert isinstance(result, tuple)
