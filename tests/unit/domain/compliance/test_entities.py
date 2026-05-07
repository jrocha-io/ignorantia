"""Unit tests for compliance entities.

Two aggregates pinned by these tests:

* :class:`VenueProfile` — the editorial profile of a publication
  venue (journal, conference). Bundles identity (``venue_id``,
  ``name``) with structured requirement value objects (length,
  abstract, mandatory sections, mandatory declarations, etc.).
  Supersedes the loose dict shape v2 carried in YAML profiles.
* :class:`ComplianceReport` — the per-manuscript audit artefact
  produced by the engine. Carries the venue, the timestamp, and
  every :class:`Decision` the engine produced; computes aggregates
  (blocking-ness, gaps, pass-rate) from the decision list rather
  than letting callers re-derive them.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.compliance.entities import (
    AbstractRequirement,
    ComplianceReport,
    LengthRequirement,
    MandatoryDeclaration,
    VenueProfile,
)
from ignorantia.domain.compliance.value_objects import (
    Decision,
    DecisionStatus,
    Severity,
)

# ----------------------------------------------------------------------
# Requirement value objects
# ----------------------------------------------------------------------


class TestLengthRequirement:
    def test_word_max_only(self) -> None:
        req = LengthRequirement(unit="words", max=8000)
        assert req.unit == "words"
        assert req.max == 8000
        assert req.min is None

    def test_word_min_and_max(self) -> None:
        req = LengthRequirement(unit="words", min=5000, max=10000)
        assert req.min == 5000
        assert req.max == 10000

    def test_unit_must_be_known(self) -> None:
        with pytest.raises(ValueError, match="unit"):
            LengthRequirement(unit="paragraphs", max=10)

    def test_min_must_not_exceed_max(self) -> None:
        with pytest.raises(ValueError, match="min"):
            LengthRequirement(unit="words", min=10000, max=5000)

    def test_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        req = LengthRequirement(unit="words", max=100)
        with pytest.raises(FrozenInstanceError):
            req.unit = "characters_with_spaces"  # type: ignore[misc]


class TestAbstractRequirement:
    def test_default_unstructured(self) -> None:
        req = AbstractRequirement(max_words=300)
        assert req.max_words == 300
        assert req.structured is False

    def test_structured_flag(self) -> None:
        req = AbstractRequirement(max_words=250, structured=True)
        assert req.structured is True


class TestMandatoryDeclaration:
    def test_construction(self) -> None:
        decl = MandatoryDeclaration(id="conflicts_of_interest", severity=Severity.BLOCKING)
        assert decl.id == "conflicts_of_interest"
        assert decl.severity is Severity.BLOCKING

    def test_id_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="id"):
            MandatoryDeclaration(id="", severity=Severity.MAJOR)


# ----------------------------------------------------------------------
# VenueProfile
# ----------------------------------------------------------------------


class TestVenueProfileMinimum:
    def test_minimum_fields(self) -> None:
        venue = VenueProfile(
            venue_id="cp_fcc",
            name="Cadernos de Pesquisa",
            citation_style="abnt-nbr-6023",
        )
        assert venue.venue_id == "cp_fcc"
        assert venue.name == "Cadernos de Pesquisa"
        assert venue.citation_style == "abnt-nbr-6023"
        # All optional collections default to empty tuples
        assert venue.mandatory_sections == ()
        assert venue.mandatory_declarations == ()
        assert venue.review_types_accepted == ()
        assert venue.length is None
        assert venue.abstract is None
        assert venue.title_max_words is None


class TestVenueProfileFull:
    def test_full_construction(self) -> None:
        venue = VenueProfile(
            venue_id="cp_fcc",
            name="Cadernos de Pesquisa",
            citation_style="abnt-nbr-6023",
            length=LengthRequirement(unit="characters_with_spaces", max=40000),
            abstract=AbstractRequirement(max_words=200, structured=False),
            title_max_words=18,
            mandatory_sections=("Introdução", "Metodologia", "Resultados"),
            mandatory_declarations=(
                MandatoryDeclaration(id="conflicts_of_interest", severity=Severity.BLOCKING),
                MandatoryDeclaration(id="ai_usage", severity=Severity.BLOCKING),
            ),
            review_types_accepted=("systematic_review_strict", "scoping_review"),
        )
        assert venue.length is not None
        assert venue.length.max == 40000
        assert venue.abstract is not None
        assert venue.abstract.max_words == 200
        assert venue.title_max_words == 18
        assert "Introdução" in venue.mandatory_sections
        assert len(venue.mandatory_declarations) == 2


class TestVenueProfileInvariants:
    def test_venue_id_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="venue_id"):
            VenueProfile(venue_id="", name="x", citation_style="apa")

    def test_name_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="name"):
            VenueProfile(venue_id="x", name="", citation_style="apa")

    def test_citation_style_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="citation_style"):
            VenueProfile(venue_id="x", name="X", citation_style="")


# ----------------------------------------------------------------------
# ComplianceReport
# ----------------------------------------------------------------------


def _venue() -> VenueProfile:
    return VenueProfile(venue_id="x", name="X", citation_style="apa")


def _decision(status: DecisionStatus, severity: Severity = Severity.MINOR) -> Decision:
    return Decision(rule_id="r", rule_name="R", status=status, severity=severity)


class TestComplianceReportConstruction:
    def test_minimum_fields(self) -> None:
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert report.manuscript_id == "m1"
        assert report.venue.venue_id == "x"
        assert report.decisions == ()


class TestComplianceReportInvariants:
    def test_manuscript_id_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="manuscript_id"):
            ComplianceReport(
                manuscript_id="",
                venue=_venue(),
                decisions=(),
                timestamp_iso8601="2026-05-07T12:00:00Z",
            )

    def test_timestamp_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="timestamp"):
            ComplianceReport(
                manuscript_id="m1",
                venue=_venue(),
                decisions=(),
                timestamp_iso8601="",
            )


class TestComplianceReportAggregations:
    def test_is_blocking_when_any_decision_is_blocking(self) -> None:
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(
                _decision(DecisionStatus.PASS),
                _decision(DecisionStatus.FAIL, Severity.BLOCKING),
                _decision(DecisionStatus.PASS),
            ),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert report.is_blocking is True

    def test_not_blocking_when_no_decision_is_blocking(self) -> None:
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(
                _decision(DecisionStatus.PASS),
                _decision(DecisionStatus.FAIL, Severity.MAJOR),
                _decision(DecisionStatus.PASS),
            ),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert report.is_blocking is False

    def test_not_blocking_when_no_decisions(self) -> None:
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert report.is_blocking is False

    def test_gaps_returns_only_failed_decisions(self) -> None:
        decisions = (
            _decision(DecisionStatus.PASS),
            _decision(DecisionStatus.FAIL, Severity.BLOCKING),
            _decision(DecisionStatus.NOT_APPLICABLE),
            _decision(DecisionStatus.FAIL, Severity.MINOR),
            _decision(DecisionStatus.NEEDS_REVIEW),
        )
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=decisions,
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        gaps = report.gaps
        assert len(gaps) == 2
        assert all(d.status is DecisionStatus.FAIL for d in gaps)

    def test_pass_rate_excludes_not_applicable(self) -> None:
        decisions = (
            _decision(DecisionStatus.PASS),
            _decision(DecisionStatus.PASS),
            _decision(DecisionStatus.FAIL),
            _decision(DecisionStatus.NOT_APPLICABLE),
        )
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=decisions,
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        # 2 pass / 3 applicable (excludes the NOT_APPLICABLE)
        assert report.pass_rate == pytest.approx(2 / 3)

    def test_pass_rate_is_zero_when_all_not_applicable(self) -> None:
        # 0 applicable rules → pass_rate is 0.0 by convention (no
        # division by zero, no NaN).
        decisions = (
            _decision(DecisionStatus.NOT_APPLICABLE),
            _decision(DecisionStatus.NOT_APPLICABLE),
        )
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=decisions,
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert report.pass_rate == 0.0

    def test_pass_rate_is_zero_when_no_decisions(self) -> None:
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert report.pass_rate == 0.0


class TestComplianceReportImmutability:
    def test_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        with pytest.raises(FrozenInstanceError):
            report.manuscript_id = "m2"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        report = ComplianceReport(
            manuscript_id="m1",
            venue=_venue(),
            decisions=(),
            timestamp_iso8601="2026-05-07T12:00:00Z",
        )
        assert ComplianceReport.__slots__
        assert not hasattr(report, "__dict__")
