"""Unit tests for :class:`VenueSuggestion`."""

from __future__ import annotations

import pytest

from ignorantia.domain.slr.value_objects import ISSN, VenueSuggestion


class TestConstruction:
    def test_minimal_construction(self) -> None:
        suggestion = VenueSuggestion(venue="Journal X", score=0.5, ranking=1)
        assert suggestion.venue == "Journal X"
        assert suggestion.score == 0.5
        assert suggestion.ranking == 1

    def test_optional_fields_default(self) -> None:
        suggestion = VenueSuggestion(venue="Journal X", score=0.5, ranking=1)
        assert suggestion.venue_url is None
        assert suggestion.venue_issn is None
        assert suggestion.estimated_jcr_quartile is None
        assert suggestion.is_oa is False

    def test_with_all_fields(self) -> None:
        suggestion = VenueSuggestion(
            venue="Journal X",
            score=0.87,
            ranking=1,
            venue_url="https://example.org/jx",
            venue_issn=ISSN("1234-5678"),
            estimated_jcr_quartile="Q1",
            is_oa=True,
        )
        assert suggestion.estimated_jcr_quartile == "Q1"
        assert suggestion.is_oa is True
        assert str(suggestion.venue_issn) == "1234-5678"


class TestValidation:
    def test_empty_venue_rejected(self) -> None:
        with pytest.raises(ValueError, match="venue"):
            VenueSuggestion(venue="", score=0.5, ranking=1)

    def test_whitespace_only_venue_rejected(self) -> None:
        with pytest.raises(ValueError, match="venue"):
            VenueSuggestion(venue="   ", score=0.5, ranking=1)

    @pytest.mark.parametrize("score", [-0.01, 1.01, -1.0, 2.0])
    def test_score_outside_unit_interval_rejected(self, score: float) -> None:
        with pytest.raises(ValueError, match="score"):
            VenueSuggestion(venue="Journal X", score=score, ranking=1)

    @pytest.mark.parametrize("score", [0.0, 0.5, 1.0])
    def test_score_at_or_inside_unit_interval_accepted(self, score: float) -> None:
        VenueSuggestion(venue="Journal X", score=score, ranking=1)

    @pytest.mark.parametrize("ranking", [0, -1, -100])
    def test_ranking_below_one_rejected(self, ranking: int) -> None:
        with pytest.raises(ValueError, match="ranking"):
            VenueSuggestion(venue="Journal X", score=0.5, ranking=ranking)

    @pytest.mark.parametrize("quartile", ["Q1", "Q2", "Q3", "Q4"])
    def test_known_quartiles_accepted(self, quartile: str) -> None:
        VenueSuggestion(venue="Journal X", score=0.5, ranking=1, estimated_jcr_quartile=quartile)

    @pytest.mark.parametrize("quartile", ["q1", "Q5", "Q0", "first", ""])
    def test_unknown_quartiles_rejected(self, quartile: str) -> None:
        with pytest.raises(ValueError, match="estimated_jcr_quartile"):
            VenueSuggestion(
                venue="Journal X",
                score=0.5,
                ranking=1,
                estimated_jcr_quartile=quartile,
            )

    def test_quartile_none_accepted(self) -> None:
        VenueSuggestion(venue="Journal X", score=0.5, ranking=1, estimated_jcr_quartile=None)


class TestImmutability:
    def test_is_frozen(self) -> None:
        suggestion = VenueSuggestion(venue="Journal X", score=0.5, ranking=1)
        with pytest.raises(AttributeError):
            suggestion.score = 0.9  # type: ignore[misc]


class TestEquality:
    def test_equal_when_all_fields_match(self) -> None:
        a = VenueSuggestion(venue="Journal X", score=0.5, ranking=1)
        b = VenueSuggestion(venue="Journal X", score=0.5, ranking=1)
        assert a == b

    def test_different_score_not_equal(self) -> None:
        a = VenueSuggestion(venue="Journal X", score=0.5, ranking=1)
        b = VenueSuggestion(venue="Journal X", score=0.6, ranking=1)
        assert a != b
