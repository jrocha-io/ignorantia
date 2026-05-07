"""Unit tests for the :class:`ComplianceEngine` service.

The engine takes a :class:`ManuscriptMetrics` snapshot of the document
under review and a :class:`VenueProfile` describing the target venue's
editorial requirements, then emits a :class:`ComplianceReport` with
one :class:`Decision` per rule it can evaluate.

Rules pinned by these tests:

* ``hard.length`` — exceed venue's ``LengthRequirement.max`` → FAIL
  blocking; below ``min`` → FAIL major; within bounds → PASS;
  unit mismatch → NEEDS_REVIEW; venue has no length → NOT_APPLICABLE.
* ``hard.abstract`` — abstract word count vs. ``AbstractRequirement.max_words``.
* ``hard.title`` — title word count vs. ``title_max_words``.
* ``hard.mandatory_sections`` — venue's required section titles must
  appear in ``ManuscriptMetrics.present_sections``.
* ``hard.mandatory_declarations`` — venue's required declarations must
  appear in ``ManuscriptMetrics.declared_declarations``; severity from
  the venue's :class:`MandatoryDeclaration` carries to the Decision.
* ``hard.citation_style`` — manuscript's declared citation style must
  match the venue's.

The engine takes an injected ``clock`` callable (``() -> str``) for
the report timestamp — aligns with issue #13 (datetime.now() injection
for reproducibility).
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
from ignorantia.domain.compliance.services import (
    ComplianceEngine,
    ManuscriptMetrics,
)
from ignorantia.domain.compliance.value_objects import DecisionStatus, Severity

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _venue(**overrides: object) -> VenueProfile:
    base: dict[str, object] = {
        "venue_id": "v",
        "name": "V",
        "citation_style": "apa-7",
    }
    base.update(overrides)
    return VenueProfile(**base)  # type: ignore[arg-type]


def _metrics(**overrides: object) -> ManuscriptMetrics:
    base: dict[str, object] = {
        "length_value": 5000,
        "length_unit": "words",
        "abstract_word_count": 200,
        "title_word_count": 12,
        "present_sections": (),
        "declared_declarations": (),
        "citation_style": "apa-7",
    }
    base.update(overrides)
    return ManuscriptMetrics(**base)  # type: ignore[arg-type]


def _frozen_clock(value: str = "2026-05-07T12:00:00Z"):
    def _clock() -> str:
        return value

    return _clock


@pytest.fixture
def engine() -> ComplianceEngine:
    return ComplianceEngine(clock=_frozen_clock())


def _decision_for(report: ComplianceReport, rule_id: str):
    matches = [d for d in report.decisions if d.rule_id == rule_id]
    assert matches, f"expected rule {rule_id!r} in report"
    return matches[0]


# ----------------------------------------------------------------------
# ManuscriptMetrics
# ----------------------------------------------------------------------


class TestManuscriptMetricsConstruction:
    def test_minimum_construction(self) -> None:
        m = ManuscriptMetrics(
            length_value=1000,
            length_unit="words",
            abstract_word_count=200,
            title_word_count=10,
            present_sections=(),
            declared_declarations=(),
            citation_style="apa-7",
        )
        assert m.length_value == 1000
        assert m.length_unit == "words"
        assert m.citation_style == "apa-7"

    def test_negative_length_rejected(self) -> None:
        with pytest.raises(ValueError, match="length_value"):
            ManuscriptMetrics(
                length_value=-1,
                length_unit="words",
                abstract_word_count=0,
                title_word_count=0,
                present_sections=(),
                declared_declarations=(),
                citation_style="apa-7",
            )

    def test_unknown_length_unit_rejected(self) -> None:
        with pytest.raises(ValueError, match="length_unit"):
            ManuscriptMetrics(
                length_value=1000,
                length_unit="paragraphs",
                abstract_word_count=0,
                title_word_count=0,
                present_sections=(),
                declared_declarations=(),
                citation_style="apa-7",
            )


# ----------------------------------------------------------------------
# Engine wiring
# ----------------------------------------------------------------------


class TestEngineProducesReport:
    def test_returns_compliance_report(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(_metrics(), _venue())
        assert isinstance(report, ComplianceReport)

    def test_report_carries_venue(self, engine: ComplianceEngine) -> None:
        venue = _venue(venue_id="cp_fcc")
        report = engine.evaluate(_metrics(), venue)
        assert report.venue.venue_id == "cp_fcc"

    def test_report_uses_injected_clock(self) -> None:
        engine = ComplianceEngine(clock=_frozen_clock("2030-01-01T00:00:00Z"))
        report = engine.evaluate(_metrics(), _venue())
        assert report.timestamp_iso8601 == "2030-01-01T00:00:00Z"

    def test_report_has_manuscript_id_from_metrics(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(
            _metrics(manuscript_id="m-42"),
            _venue(),
        )
        assert report.manuscript_id == "m-42"


# ----------------------------------------------------------------------
# Length rule
# ----------------------------------------------------------------------


class TestLengthRule:
    def test_pass_within_bounds(self, engine: ComplianceEngine) -> None:
        venue = _venue(length=LengthRequirement(unit="words", max=8000))
        report = engine.evaluate(_metrics(length_value=5000, length_unit="words"), venue)
        d = _decision_for(report, "hard.length")
        assert d.status is DecisionStatus.PASS

    def test_fail_blocking_when_above_max(self, engine: ComplianceEngine) -> None:
        venue = _venue(length=LengthRequirement(unit="words", max=8000))
        report = engine.evaluate(_metrics(length_value=10000, length_unit="words"), venue)
        d = _decision_for(report, "hard.length")
        assert d.status is DecisionStatus.FAIL
        assert d.severity is Severity.BLOCKING
        assert d.is_blocking is True

    def test_fail_major_when_below_min(self, engine: ComplianceEngine) -> None:
        venue = _venue(length=LengthRequirement(unit="words", min=2000, max=8000))
        report = engine.evaluate(_metrics(length_value=500, length_unit="words"), venue)
        d = _decision_for(report, "hard.length")
        assert d.status is DecisionStatus.FAIL
        assert d.severity is Severity.MAJOR

    def test_needs_review_on_unit_mismatch(self, engine: ComplianceEngine) -> None:
        venue = _venue(length=LengthRequirement(unit="characters_with_spaces", max=40000))
        report = engine.evaluate(_metrics(length_value=5000, length_unit="words"), venue)
        d = _decision_for(report, "hard.length")
        assert d.status is DecisionStatus.NEEDS_REVIEW

    def test_not_applicable_when_venue_has_no_length(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(_metrics(), _venue(length=None))
        d = _decision_for(report, "hard.length")
        assert d.status is DecisionStatus.NOT_APPLICABLE


# ----------------------------------------------------------------------
# Abstract rule
# ----------------------------------------------------------------------


class TestAbstractRule:
    def test_pass_within_word_cap(self, engine: ComplianceEngine) -> None:
        venue = _venue(abstract=AbstractRequirement(max_words=300))
        report = engine.evaluate(_metrics(abstract_word_count=250), venue)
        d = _decision_for(report, "hard.abstract")
        assert d.status is DecisionStatus.PASS

    def test_fail_when_above_word_cap(self, engine: ComplianceEngine) -> None:
        venue = _venue(abstract=AbstractRequirement(max_words=300))
        report = engine.evaluate(_metrics(abstract_word_count=600), venue)
        d = _decision_for(report, "hard.abstract")
        assert d.status is DecisionStatus.FAIL

    def test_not_applicable_when_venue_has_no_abstract_req(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(_metrics(), _venue(abstract=None))
        d = _decision_for(report, "hard.abstract")
        assert d.status is DecisionStatus.NOT_APPLICABLE


# ----------------------------------------------------------------------
# Title rule
# ----------------------------------------------------------------------


class TestTitleRule:
    def test_pass_within_word_cap(self, engine: ComplianceEngine) -> None:
        venue = _venue(title_max_words=18)
        report = engine.evaluate(_metrics(title_word_count=10), venue)
        d = _decision_for(report, "hard.title")
        assert d.status is DecisionStatus.PASS

    def test_fail_when_above_word_cap(self, engine: ComplianceEngine) -> None:
        venue = _venue(title_max_words=18)
        report = engine.evaluate(_metrics(title_word_count=25), venue)
        d = _decision_for(report, "hard.title")
        assert d.status is DecisionStatus.FAIL

    def test_not_applicable_when_venue_has_no_cap(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(_metrics(), _venue(title_max_words=None))
        d = _decision_for(report, "hard.title")
        assert d.status is DecisionStatus.NOT_APPLICABLE


# ----------------------------------------------------------------------
# Mandatory sections rule
# ----------------------------------------------------------------------


class TestMandatorySectionsRule:
    def test_pass_when_all_present(self, engine: ComplianceEngine) -> None:
        venue = _venue(mandatory_sections=("Intro", "Methods", "Results"))
        report = engine.evaluate(
            _metrics(present_sections=("Intro", "Methods", "Results", "Discussion")),
            venue,
        )
        d = _decision_for(report, "hard.mandatory_sections")
        assert d.status is DecisionStatus.PASS

    def test_fail_when_one_missing(self, engine: ComplianceEngine) -> None:
        venue = _venue(mandatory_sections=("Intro", "Methods", "Results"))
        report = engine.evaluate(_metrics(present_sections=("Intro", "Results")), venue)
        d = _decision_for(report, "hard.mandatory_sections")
        assert d.status is DecisionStatus.FAIL
        # Evidence cites the missing section title.
        assert "Methods" in d.evidence

    def test_not_applicable_when_venue_lists_none(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(_metrics(), _venue(mandatory_sections=()))
        d = _decision_for(report, "hard.mandatory_sections")
        assert d.status is DecisionStatus.NOT_APPLICABLE


# ----------------------------------------------------------------------
# Mandatory declarations rule
# ----------------------------------------------------------------------


class TestMandatoryDeclarationsRule:
    def test_pass_when_all_declared(self, engine: ComplianceEngine) -> None:
        venue = _venue(
            mandatory_declarations=(
                MandatoryDeclaration(id="conflicts_of_interest", severity=Severity.BLOCKING),
                MandatoryDeclaration(id="funding", severity=Severity.MAJOR),
            )
        )
        report = engine.evaluate(
            _metrics(declared_declarations=("conflicts_of_interest", "funding")),
            venue,
        )
        d = _decision_for(report, "hard.mandatory_declarations")
        assert d.status is DecisionStatus.PASS

    def test_fail_blocking_when_blocking_declaration_missing(
        self, engine: ComplianceEngine
    ) -> None:
        venue = _venue(
            mandatory_declarations=(
                MandatoryDeclaration(id="conflicts_of_interest", severity=Severity.BLOCKING),
                MandatoryDeclaration(id="funding", severity=Severity.MAJOR),
            )
        )
        report = engine.evaluate(
            _metrics(declared_declarations=("funding",)),  # missing CoI
            venue,
        )
        d = _decision_for(report, "hard.mandatory_declarations")
        assert d.status is DecisionStatus.FAIL
        # Highest unmet severity propagates → BLOCKING wins over MAJOR.
        assert d.severity is Severity.BLOCKING

    def test_fail_major_when_only_major_declaration_missing(self, engine: ComplianceEngine) -> None:
        venue = _venue(
            mandatory_declarations=(
                MandatoryDeclaration(id="conflicts_of_interest", severity=Severity.BLOCKING),
                MandatoryDeclaration(id="funding", severity=Severity.MAJOR),
            )
        )
        report = engine.evaluate(
            _metrics(declared_declarations=("conflicts_of_interest",)),
            venue,
        )
        d = _decision_for(report, "hard.mandatory_declarations")
        assert d.status is DecisionStatus.FAIL
        assert d.severity is Severity.MAJOR


# ----------------------------------------------------------------------
# Citation style rule
# ----------------------------------------------------------------------


class TestCitationStyleRule:
    def test_pass_when_styles_match(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(
            _metrics(citation_style="apa-7"),
            _venue(citation_style="apa-7"),
        )
        d = _decision_for(report, "hard.citation_style")
        assert d.status is DecisionStatus.PASS

    def test_fail_when_styles_differ(self, engine: ComplianceEngine) -> None:
        report = engine.evaluate(
            _metrics(citation_style="apa-7"),
            _venue(citation_style="abnt-nbr-6023"),
        )
        d = _decision_for(report, "hard.citation_style")
        assert d.status is DecisionStatus.FAIL


# ----------------------------------------------------------------------
# Aggregate behaviour
# ----------------------------------------------------------------------


class TestAggregateReport:
    def test_report_is_blocking_propagates(self, engine: ComplianceEngine) -> None:
        venue = _venue(length=LengthRequirement(unit="words", max=8000))
        report = engine.evaluate(_metrics(length_value=10000, length_unit="words"), venue)
        assert report.is_blocking is True

    def test_report_pass_rate_excludes_not_applicable(self, engine: ComplianceEngine) -> None:
        # Default _venue() has no requirements → most rules emit
        # NOT_APPLICABLE; only citation_style is checked (PASS).
        report = engine.evaluate(_metrics(), _venue())
        assert report.pass_rate == 1.0
