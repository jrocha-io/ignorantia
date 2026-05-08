"""Unit tests for SLR bounded context entities."""

from __future__ import annotations

import dataclasses

import pytest

from ignorantia.domain.slr.entities import Manuscript, Review, Study
from ignorantia.domain.slr.value_objects import DOI, ISSN, Language, ScreeningDecision


def _study(**overrides: object) -> Study:
    payload: dict[str, object] = {"study_id": "S001", "title": "A study"}
    payload.update(overrides)
    return Study(**payload)  # type: ignore[arg-type]


class TestStudyConstruction:
    """Required fields and sensible defaults."""

    def test_minimal_study_only_requires_id_and_title(self) -> None:
        s = _study()
        assert s.study_id == "S001"
        assert s.title == "A study"

    def test_authors_default_to_empty_tuple(self) -> None:
        assert _study().authors == ()

    def test_optional_fields_default_to_none(self) -> None:
        s = _study()
        assert s.doi is None
        assert s.issn is None
        assert s.year is None
        assert s.venue is None
        assert s.language is None

    def test_decision_defaults_to_undecided(self) -> None:
        assert _study().decision is ScreeningDecision.UNDECIDED


class TestStudyValueObjectFields:
    """Identifier fields use canonical VOs from the SLR context."""

    def test_doi_field_accepts_doi_value_object(self) -> None:
        doi = DOI("10.1234/x")
        assert _study(doi=doi).doi is doi

    def test_issn_field_accepts_issn_value_object(self) -> None:
        issn = ISSN("0028-0836")
        assert _study(issn=issn).issn is issn

    def test_language_field_accepts_language_value_object(self) -> None:
        lang = Language("pt")
        assert _study(language=lang).language is lang


class TestStudyImmutability:
    """Studies are frozen — workflow steps construct new instances."""

    def test_assignment_to_frozen_field_raises(self) -> None:
        s = _study()
        with pytest.raises(dataclasses.FrozenInstanceError):
            s.title = "mutated"  # type: ignore[misc]


class TestStudyIdentity:
    """A Study is an entity: identity comes from ``study_id`` only."""

    def test_studies_with_same_id_are_equal_even_with_different_titles(self) -> None:
        a = _study(study_id="S001", title="A")
        b = _study(study_id="S001", title="B")
        assert a == b

    def test_studies_with_different_ids_are_unequal(self) -> None:
        a = _study(study_id="S001")
        b = _study(study_id="S002")
        assert a != b

    def test_hash_uses_study_id(self) -> None:
        a = _study(study_id="S001", title="A")
        b = _study(study_id="S001", title="B")
        assert hash(a) == hash(b)


class TestManuscriptConstruction:
    """Manuscript = the paper produced by the review."""

    def test_minimal_manuscript_only_requires_title(self) -> None:
        m = Manuscript(title="A review")
        assert m.title == "A review"

    def test_section_fields_default_to_empty_strings(self) -> None:
        m = Manuscript(title="A review")
        assert m.abstract == ""
        assert m.introduction == ""
        assert m.methodology == ""
        assert m.synthesis == ""
        assert m.discussion == ""
        assert m.conclusion == ""

    def test_references_default_is_empty_tuple(self) -> None:
        assert Manuscript(title="x").references == ()

    def test_manuscript_is_immutable(self) -> None:
        m = Manuscript(title="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            m.title = "y"  # type: ignore[misc]


class TestReviewConstruction:
    """Review aggregates studies and produces a manuscript."""

    def test_minimal_review_only_requires_review_id_and_title(self) -> None:
        r = Review(review_id="R-2026-01", title="Letramento digital de idosos")
        assert r.review_id == "R-2026-01"
        assert r.title == "Letramento digital de idosos"

    def test_studies_default_is_empty_tuple(self) -> None:
        r = Review(review_id="R", title="x")
        assert r.studies == ()

    def test_manuscript_defaults_to_none(self) -> None:
        assert Review(review_id="R", title="x").manuscript is None

    def test_review_is_immutable(self) -> None:
        r = Review(review_id="R", title="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.title = "y"  # type: ignore[misc]


class TestReviewIdentity:
    """A Review is an entity: identity comes from ``review_id`` only."""

    def test_reviews_with_same_id_are_equal_even_with_different_titles(self) -> None:
        a = Review(review_id="R-1", title="A")
        b = Review(review_id="R-1", title="B")
        assert a == b

    def test_reviews_with_different_ids_are_unequal(self) -> None:
        a = Review(review_id="R-1", title="A")
        b = Review(review_id="R-2", title="A")
        assert a != b
