"""Entities for the SLR bounded context.

Entities here have *identity* — two ``Study`` records with the same
``study_id`` are considered equal, even if their other fields differ. This
matters because the same physical record can be observed multiple times
through deduplication (D3 audit) and we need to merge data into a single
canonical entity.

Entities are still immutable: workflow steps that "change" a study's
state (e.g. recording a screening decision) construct a *new*
:class:`Study` rather than mutating the existing one. This keeps the
domain free of hidden side effects while still allowing identity-based
comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ignorantia.domain.slr.value_objects import DOI, ISSN, Language, ScreeningDecision


@dataclass(frozen=True, slots=True, eq=False)
class Study:
    """A bibliographic record under review.

    Equality and hashing are based on :attr:`study_id` alone — see
    module docstring for the rationale.

    Attributes:
        study_id: Reviewer-assigned identifier (e.g. ``"S001"``).
        title: Title as published.
        authors: Author names in publication order.
        year: Publication year, when known.
        doi: Canonical :class:`DOI`, when available.
        issn: Canonical :class:`ISSN`, when available.
        venue: Journal or conference name.
        language: Publication language.
        abstract: Abstract text.
        decision: Screening outcome; defaults to ``UNDECIDED``.
    """

    study_id: str
    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: DOI | None = None
    issn: ISSN | None = None
    venue: str | None = None
    language: Language | None = None
    abstract: str = ""
    decision: ScreeningDecision = ScreeningDecision.UNDECIDED

    def __eq__(self, other: object) -> bool:
        """Equality on ``study_id`` alone."""
        if not isinstance(other, Study):
            return NotImplemented
        return self.study_id == other.study_id

    def __hash__(self) -> int:
        """Hash on ``study_id`` alone."""
        return hash(self.study_id)


@dataclass(frozen=True, slots=True)
class Manuscript:
    """The paper produced by the review.

    Sections are stored as already-rendered text (HTML or plain) — the
    rendering pipeline operates outside the domain.

    Attributes:
        title: Manuscript title.
        abstract: Abstract section text.
        introduction: Introduction section text.
        methodology: Methodology section text.
        synthesis: Synthesis / results section text.
        discussion: Discussion section text.
        conclusion: Conclusion section text.
        keywords: Author keywords.
        references: Already-formatted reference strings.
    """

    title: str
    abstract: str = ""
    introduction: str = ""
    methodology: str = ""
    synthesis: str = ""
    discussion: str = ""
    conclusion: str = ""
    keywords: tuple[str, ...] = ()
    references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class Review:
    """A systematic literature review aggregate.

    Equality and hashing are based on :attr:`review_id` alone.

    Attributes:
        review_id: Stable identifier for this review project.
        title: Human-readable review title.
        studies: All studies known to this review (post-deduplication).
        manuscript: The paper, when produced. ``None`` while writing.
    """

    review_id: str
    title: str
    studies: tuple[Study, ...] = field(default_factory=tuple)
    manuscript: Manuscript | None = None

    def __eq__(self, other: object) -> bool:
        """Equality on ``review_id`` alone."""
        if not isinstance(other, Review):
            return NotImplemented
        return self.review_id == other.review_id

    def __hash__(self) -> int:
        """Hash on ``review_id`` alone."""
        return hash(self.review_id)
