"""Entities for the compliance bounded context.

Two aggregates anchor the compliance domain:

* :class:`VenueProfile` — the editorial profile of a publication
  venue (journal, conference). Bundles identity (``venue_id``,
  ``name``) with structured requirement value objects (length,
  abstract, mandatory sections, mandatory declarations). Replaces
  v2's loose dict shape carried in YAML profiles
  (``references/profiles/**/*.yaml``).
* :class:`ComplianceReport` — the per-manuscript audit artefact
  produced by the engine. Carries the venue, the timestamp, and
  every :class:`Decision` the engine emitted. Computed properties
  expose the aggregate signals callers care about
  (:attr:`is_blocking`, :attr:`gaps`, :attr:`pass_rate`) so
  consumers do not re-derive them from the decision list.

Cross-context note: this module deliberately does *not* import from
``ignorantia.domain.render``. ``citation_style`` is a string field
with documented valid values — the architecture plan keeps each
bounded context self-contained, communicating across boundaries via
DTOs in ``application/`` rather than direct imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ignorantia.domain.compliance.value_objects import (
    Decision,
    DecisionStatus,
    Severity,
)

_VALID_LENGTH_UNITS: frozenset[str] = frozenset({"words", "characters_with_spaces", "pages"})


@dataclass(frozen=True, slots=True)
class LengthRequirement:
    """Length cap (and optional floor) for a manuscript.

    Attributes:
        unit: One of ``"words"``, ``"characters_with_spaces"``,
            ``"pages"``. The unit is part of the contract so engines
            don't silently mis-compare different units.
        max: Upper bound; ``None`` means "no upper bound".
        min: Lower bound; ``None`` means "no lower bound".
    """

    unit: str
    max: int | None = None
    min: int | None = None

    def __post_init__(self) -> None:
        """Reject unknown units and inverted min/max bounds."""
        if self.unit not in _VALID_LENGTH_UNITS:
            raise ValueError(
                f"LengthRequirement.unit must be one of {sorted(_VALID_LENGTH_UNITS)}; "
                f"got {self.unit!r}"
            )
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"LengthRequirement.min ({self.min}) must not exceed max ({self.max})")


@dataclass(frozen=True, slots=True)
class AbstractRequirement:
    """Abstract length and structure constraint."""

    max_words: int | None = None
    structured: bool = False


@dataclass(frozen=True, slots=True)
class MandatoryDeclaration:
    """A statement the manuscript must include (e.g. conflict of interest).

    Attributes:
        id: Stable declaration identifier
            (e.g. ``"conflicts_of_interest"``, ``"funding"``,
            ``"ai_usage"``).
        severity: How serious the absence of the declaration is —
            blocking declarations stop submission, others lower the
            aggregate score.
    """

    id: str
    severity: Severity

    def __post_init__(self) -> None:
        """Empty ids would break audit lookups."""
        if not self.id:
            raise ValueError("MandatoryDeclaration.id must be a non-empty string")


@dataclass(frozen=True, slots=True)
class VenueProfile:
    """Editorial profile of a publication venue (journal, conference).

    Attributes:
        venue_id: Stable identifier (e.g. ``"cp_fcc"``).
        name: Human-readable venue name.
        citation_style: Wire string for the required citation style
            (e.g. ``"abnt-nbr-6023"``, ``"apa-7"``). Kept loose to
            keep the compliance context independent of
            ``domain/render``.
        length: Optional :class:`LengthRequirement`. ``None`` means
            "no length constraint".
        abstract: Optional :class:`AbstractRequirement`.
        title_max_words: Optional title-length cap.
        mandatory_sections: Section titles the manuscript must
            include, in venue-canonical wording.
        mandatory_declarations: Declarations the manuscript must
            include, with their severity.
        review_types_accepted: Tuple of review-type identifiers the
            venue accepts (e.g. ``"systematic_review_strict"``).
    """

    venue_id: str
    name: str
    citation_style: str
    length: LengthRequirement | None = None
    abstract: AbstractRequirement | None = None
    title_max_words: int | None = None
    mandatory_sections: tuple[str, ...] = field(default_factory=tuple)
    mandatory_declarations: tuple[MandatoryDeclaration, ...] = field(default_factory=tuple)
    review_types_accepted: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Pin identity invariants — empty ids make profiles unusable."""
        if not self.venue_id:
            raise ValueError("VenueProfile.venue_id must be a non-empty string")
        if not self.name:
            raise ValueError("VenueProfile.name must be a non-empty string")
        if not self.citation_style:
            raise ValueError("VenueProfile.citation_style must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ComplianceReport:
    """Per-manuscript compliance audit produced by the engine.

    Attributes:
        manuscript_id: Stable manuscript identifier.
        venue: The :class:`VenueProfile` this manuscript was checked
            against.
        decisions: Tuple of :class:`Decision` outcomes, in the order
            the engine produced them.
        timestamp_iso8601: When the report was produced
            (``YYYY-MM-DDTHH:MM:SSZ``).
    """

    manuscript_id: str
    venue: VenueProfile
    decisions: tuple[Decision, ...]
    timestamp_iso8601: str

    def __post_init__(self) -> None:
        """Empty manuscript ids and missing timestamps break audit replay."""
        if not self.manuscript_id:
            raise ValueError("ComplianceReport.manuscript_id must be a non-empty string")
        if not self.timestamp_iso8601:
            raise ValueError("ComplianceReport.timestamp_iso8601 must be a non-empty string")

    @property
    def is_blocking(self) -> bool:
        """``True`` when at least one decision is a blocking failure."""
        return any(d.is_blocking for d in self.decisions)

    @property
    def gaps(self) -> tuple[Decision, ...]:
        """The :class:`Decision` instances that failed (any severity)."""
        return tuple(d for d in self.decisions if d.status is DecisionStatus.FAIL)

    @property
    def pass_rate(self) -> float:
        """Fraction of *applicable* rules that passed.

        ``NOT_APPLICABLE`` decisions are excluded from the
        denominator so a venue's optional rules don't dilute the
        signal. Returns ``0.0`` when no applicable decisions exist —
        the alternative (``NaN``) breaks downstream aggregation.
        """
        applicable = [d for d in self.decisions if d.status is not DecisionStatus.NOT_APPLICABLE]
        if not applicable:
            return 0.0
        passed = sum(1 for d in applicable if d.status is DecisionStatus.PASS)
        return passed / len(applicable)
