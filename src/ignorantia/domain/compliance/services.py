"""Compliance domain services.

This module exposes :class:`ComplianceEngine`, the v3 successor to
v2's ``scripts/compliance/engine.py``. The engine is intentionally
minimal at this stage: one rule per editorial requirement, each
emitting one :class:`Decision`. Aggregation, gap prioritisation and
multi-venue ranking — the heavyweight stages 5-7 of the v2 engine —
are deliberately *not* migrated yet (YAGNI; those features stay in
v2 until the v3 application layer needs them).

Time injection: :class:`ComplianceEngine` takes a ``clock`` callable
in its constructor instead of calling :func:`datetime.now` directly.
This aligns with issue #13 (datetime.now() injection for
reproducibility) — every report's ``timestamp_iso8601`` is fully
determined by the caller's wiring, so unit tests pin a frozen value
and audit replay produces identical bytes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from ignorantia.domain.compliance.entities import (
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

_VALID_LENGTH_UNITS: frozenset[str] = frozenset({"words", "characters_with_spaces", "pages"})


@dataclass(frozen=True, slots=True)
class ManuscriptMetrics:
    """Numeric snapshot of the document under review.

    The engine consumes only the metrics it needs to evaluate rules —
    it does *not* operate on a full manuscript body or AST. Callers
    (use cases in ``application/``) are responsible for parsing the
    source document and deriving these counts.

    Attributes:
        manuscript_id: Stable manuscript identifier; flows into the
            :class:`ComplianceReport`.
        length_value: Numeric length, interpreted in
            :attr:`length_unit`.
        length_unit: One of ``"words"``, ``"characters_with_spaces"``,
            ``"pages"``.
        abstract_word_count: Word count of the abstract.
        title_word_count: Word count of the title.
        present_sections: Section titles present in the manuscript,
            in canonical wording the venue expects.
        declared_declarations: Identifiers of the declarations the
            manuscript already contains (e.g.
            ``"conflicts_of_interest"``).
        citation_style: Wire string for the citation style the
            manuscript currently uses (matches the venue's
            ``citation_style`` field).
    """

    length_value: int
    length_unit: str
    abstract_word_count: int
    title_word_count: int
    present_sections: tuple[str, ...]
    declared_declarations: tuple[str, ...]
    citation_style: str
    manuscript_id: str = "manuscript"

    def __post_init__(self) -> None:
        """Reject negative counts and unknown length units up-front."""
        if self.length_value < 0:
            raise ValueError(f"ManuscriptMetrics.length_value must be ≥ 0; got {self.length_value}")
        if self.length_unit not in _VALID_LENGTH_UNITS:
            raise ValueError(
                f"ManuscriptMetrics.length_unit must be one of "
                f"{sorted(_VALID_LENGTH_UNITS)}; got {self.length_unit!r}"
            )


class ComplianceEngine:
    """Evaluate a manuscript against a venue's editorial requirements.

    Rules emitted, one :class:`Decision` per call to :meth:`evaluate`:

    * ``hard.length`` — manuscript length vs. ``LengthRequirement``.
    * ``hard.abstract`` — abstract word count vs. ``AbstractRequirement``.
    * ``hard.title`` — title word count vs. ``title_max_words``.
    * ``hard.mandatory_sections`` — every required section title must be
      present in the manuscript.
    * ``hard.mandatory_declarations`` — every required declaration must
      be declared; missing declarations propagate the venue's
      :class:`Severity` (BLOCKING wins over MAJOR / MINOR).
    * ``hard.citation_style`` — declared citation style must match the
      venue's.

    The constructor takes an injected ``clock`` callable returning the
    timestamp string for the report (e.g. a frozen value in tests, a
    real ``datetime.now(UTC).isoformat()`` in production wiring).
    """

    def __init__(self, *, clock: Callable[[], str]) -> None:
        """Wire the engine to a deterministic clock (issue #13)."""
        self._clock = clock

    def evaluate(
        self,
        metrics: ManuscriptMetrics,
        venue: VenueProfile,
    ) -> ComplianceReport:
        """Run every rule and return a :class:`ComplianceReport`."""
        decisions: tuple[Decision, ...] = (
            self._check_length(metrics, venue),
            self._check_abstract(metrics, venue),
            self._check_title(metrics, venue),
            self._check_mandatory_sections(metrics, venue),
            self._check_mandatory_declarations(metrics, venue),
            self._check_citation_style(metrics, venue),
        )
        return ComplianceReport(
            manuscript_id=metrics.manuscript_id,
            venue=venue,
            decisions=decisions,
            timestamp_iso8601=self._clock(),
        )

    # ------------------------------------------------------------------
    # Individual rules
    # ------------------------------------------------------------------

    def _check_length(self, metrics: ManuscriptMetrics, venue: VenueProfile) -> Decision:
        if venue.length is None:
            return _na("hard.length", "Length")
        req: LengthRequirement = venue.length
        if metrics.length_unit != req.unit:
            return Decision(
                rule_id="hard.length",
                rule_name="Length",
                status=DecisionStatus.NEEDS_REVIEW,
                severity=Severity.MAJOR,
                evidence=(
                    f"Manuscript length is in {metrics.length_unit!r}; "
                    f"venue expects {req.unit!r}. Reviewer must convert."
                ),
                expected=req.unit,
                actual=metrics.length_unit,
            )
        if req.max is not None and metrics.length_value > req.max:
            return Decision(
                rule_id="hard.length",
                rule_name="Length",
                status=DecisionStatus.FAIL,
                severity=Severity.BLOCKING,
                evidence=f"Manuscript exceeds maximum length ({req.unit}).",
                expected=f"≤ {req.max}",
                actual=str(metrics.length_value),
            )
        if req.min is not None and metrics.length_value < req.min:
            return Decision(
                rule_id="hard.length",
                rule_name="Length",
                status=DecisionStatus.FAIL,
                severity=Severity.MAJOR,
                evidence=f"Manuscript below minimum length ({req.unit}).",
                expected=f"≥ {req.min}",
                actual=str(metrics.length_value),
            )
        return Decision(
            rule_id="hard.length",
            rule_name="Length",
            status=DecisionStatus.PASS,
            evidence=f"{metrics.length_value} {req.unit} within bounds.",
        )

    def _check_abstract(self, metrics: ManuscriptMetrics, venue: VenueProfile) -> Decision:
        if venue.abstract is None or venue.abstract.max_words is None:
            return _na("hard.abstract", "Abstract length")
        cap = venue.abstract.max_words
        if metrics.abstract_word_count > cap:
            return Decision(
                rule_id="hard.abstract",
                rule_name="Abstract length",
                status=DecisionStatus.FAIL,
                severity=Severity.MAJOR,
                evidence="Abstract exceeds word cap.",
                expected=f"≤ {cap} words",
                actual=f"{metrics.abstract_word_count} words",
            )
        return Decision(
            rule_id="hard.abstract",
            rule_name="Abstract length",
            status=DecisionStatus.PASS,
        )

    def _check_title(self, metrics: ManuscriptMetrics, venue: VenueProfile) -> Decision:
        if venue.title_max_words is None:
            return _na("hard.title", "Title length")
        cap = venue.title_max_words
        if metrics.title_word_count > cap:
            return Decision(
                rule_id="hard.title",
                rule_name="Title length",
                status=DecisionStatus.FAIL,
                severity=Severity.MINOR,
                evidence="Title exceeds word cap.",
                expected=f"≤ {cap} words",
                actual=f"{metrics.title_word_count} words",
            )
        return Decision(
            rule_id="hard.title",
            rule_name="Title length",
            status=DecisionStatus.PASS,
        )

    def _check_mandatory_sections(
        self, metrics: ManuscriptMetrics, venue: VenueProfile
    ) -> Decision:
        if not venue.mandatory_sections:
            return _na("hard.mandatory_sections", "Mandatory sections")
        present = set(metrics.present_sections)
        missing = tuple(s for s in venue.mandatory_sections if s not in present)
        if missing:
            return Decision(
                rule_id="hard.mandatory_sections",
                rule_name="Mandatory sections",
                status=DecisionStatus.FAIL,
                severity=Severity.MAJOR,
                evidence=f"Missing required sections: {', '.join(missing)}.",
                expected=", ".join(venue.mandatory_sections),
                actual=", ".join(metrics.present_sections),
            )
        return Decision(
            rule_id="hard.mandatory_sections",
            rule_name="Mandatory sections",
            status=DecisionStatus.PASS,
        )

    def _check_mandatory_declarations(
        self, metrics: ManuscriptMetrics, venue: VenueProfile
    ) -> Decision:
        if not venue.mandatory_declarations:
            return _na("hard.mandatory_declarations", "Mandatory declarations")
        declared = set(metrics.declared_declarations)
        missing: list[MandatoryDeclaration] = [
            decl for decl in venue.mandatory_declarations if decl.id not in declared
        ]
        if missing:
            severity = _highest_severity(decl.severity for decl in missing)
            ids = ", ".join(decl.id for decl in missing)
            return Decision(
                rule_id="hard.mandatory_declarations",
                rule_name="Mandatory declarations",
                status=DecisionStatus.FAIL,
                severity=severity,
                evidence=f"Missing required declarations: {ids}.",
                expected=", ".join(decl.id for decl in venue.mandatory_declarations),
                actual=", ".join(metrics.declared_declarations),
            )
        return Decision(
            rule_id="hard.mandatory_declarations",
            rule_name="Mandatory declarations",
            status=DecisionStatus.PASS,
        )

    def _check_citation_style(self, metrics: ManuscriptMetrics, venue: VenueProfile) -> Decision:
        if metrics.citation_style != venue.citation_style:
            return Decision(
                rule_id="hard.citation_style",
                rule_name="Citation style",
                status=DecisionStatus.FAIL,
                severity=Severity.MAJOR,
                evidence="Manuscript citation style differs from venue's.",
                expected=venue.citation_style,
                actual=metrics.citation_style,
            )
        return Decision(
            rule_id="hard.citation_style",
            rule_name="Citation style",
            status=DecisionStatus.PASS,
        )


def _na(rule_id: str, rule_name: str) -> Decision:
    return Decision(
        rule_id=rule_id,
        rule_name=rule_name,
        status=DecisionStatus.NOT_APPLICABLE,
        evidence="Venue declares no requirement for this rule.",
    )


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.MINOR: 0,
    Severity.MAJOR: 1,
    Severity.BLOCKING: 2,
}


def _highest_severity(severities: Iterable[Severity]) -> Severity:
    return max(severities, key=_SEVERITY_RANK.__getitem__)
