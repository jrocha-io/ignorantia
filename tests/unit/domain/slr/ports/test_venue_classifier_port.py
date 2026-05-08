"""Unit tests for the :class:`VenueClassifierPort` contract."""

from __future__ import annotations

import pytest

from ignorantia.domain.slr.ports.venue_classifier_port import VenueClassifierPort
from ignorantia.domain.slr.value_objects import VenueSuggestion


class TestPortContract:
    def test_cannot_instantiate_abstract_port(self) -> None:
        with pytest.raises(TypeError):
            VenueClassifierPort()  # type: ignore[abstract]

    def test_subclass_must_implement_suggest_venues(self) -> None:
        class _IncompletePort(VenueClassifierPort):
            pass

        with pytest.raises(TypeError):
            _IncompletePort()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        class _ConcretePort(VenueClassifierPort):
            def suggest_venues(
                self, text: str, *, max_suggestions: int = 10
            ) -> tuple[VenueSuggestion, ...]:
                del text, max_suggestions
                return ()

        port = _ConcretePort()
        assert port.suggest_venues("title abstract") == ()


class TestPortMethodSignature:
    def test_text_only_call(self) -> None:
        class _Stub(VenueClassifierPort):
            def suggest_venues(
                self, text: str, *, max_suggestions: int = 10
            ) -> tuple[VenueSuggestion, ...]:
                return (VenueSuggestion(venue=text[:10] or "x", score=0.5, ranking=1),)

        result = _Stub().suggest_venues("a manuscript title and abstract")
        assert len(result) == 1
        assert result[0].ranking == 1

    def test_max_suggestions_propagates(self) -> None:
        seen: list[int] = []

        class _Stub(VenueClassifierPort):
            def suggest_venues(
                self, text: str, *, max_suggestions: int = 10
            ) -> tuple[VenueSuggestion, ...]:
                del text
                seen.append(max_suggestions)
                return ()

        _Stub().suggest_venues("x", max_suggestions=5)
        assert seen == [5]
