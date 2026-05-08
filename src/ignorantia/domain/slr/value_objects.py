"""Value objects for the SLR bounded context.

These VOs validate raw identifiers crossing into the SLR aggregate from
the search context. They are deliberately *narrow* — only the
information needed to compare and persist studies — and immutable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_DOI_URL_PREFIX_PATTERN = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)
_DOI_GRAMMAR = re.compile(r"^10\.\d{4,9}/[\w.\-]+$")
_ISSN_PATTERN = re.compile(r"^\d{4}-?\d{3}[\dX]$")
_LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")


@dataclass(frozen=True, slots=True)
class DOI:
    """A Digital Object Identifier in canonical (URL-stripped, lowercased) form.

    Construction normalises three common variants:

    * ``"https://doi.org/10.1/x"`` (recommended URL form)
    * ``"http://dx.doi.org/10.1/x"`` (legacy URL form)
    * ``"10.1/x"`` (registrant-prefix form)

    All collapse to ``"10.1/x"``. Equality is structural, so two DOIs
    constructed from any of the above are equal.

    Raises:
        ValueError: when the string does not match the Crossref DOI
            grammar after URL stripping.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate and normalise the input string in place."""
        normalised = _DOI_URL_PREFIX_PATTERN.sub("", self.value.strip()).lower()
        if not _DOI_GRAMMAR.match(normalised):
            raise ValueError(f"Invalid DOI: {self.value!r}")
        object.__setattr__(self, "value", normalised)

    def __str__(self) -> str:
        """Return the canonical DOI string."""
        return self.value


@dataclass(frozen=True, slots=True)
class ISSN:
    """An International Standard Serial Number in canonical form ``XXXX-XXXX``.

    Accepts inputs with or without the hyphen and trims whitespace.

    Raises:
        ValueError: when the input does not match the ISSN grammar.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate and normalise to ``XXXX-XXXX`` (with literal hyphen)."""
        stripped = self.value.strip().replace("-", "")
        if len(stripped) != 8 or not re.match(r"^\d{7}[\dX]$", stripped):
            raise ValueError(f"Invalid ISSN: {self.value!r}")
        canonical = f"{stripped[:4]}-{stripped[4:]}"
        object.__setattr__(self, "value", canonical)

    def __str__(self) -> str:
        """Return the canonical hyphenated ISSN."""
        return self.value


@dataclass(frozen=True, slots=True)
class Language:
    """An ISO 639-1 two-letter language code (lowercase canonical form)."""

    value: str

    def __post_init__(self) -> None:
        """Validate and lowercase the input."""
        normalised = self.value.strip().lower()
        if not _LANGUAGE_PATTERN.match(normalised):
            raise ValueError(f"Invalid ISO 639-1 language code: {self.value!r}")
        object.__setattr__(self, "value", normalised)

    def __str__(self) -> str:
        """Return the lowercase language code."""
        return self.value


_JCR_QUARTILES: frozenset[str] = frozenset({"Q1", "Q2", "Q3", "Q4"})


@dataclass(frozen=True, slots=True)
class VenueSuggestion:
    """A ranked venue suggestion for a manuscript awaiting submission.

    Produced by a
    :class:`~ignorantia.domain.slr.ports.venue_classifier_port.VenueClassifierPort`
    given the manuscript's title + abstract. The downstream submission
    workflow consumes a tuple of these to recommend 3-5 candidate venues.

    Attributes:
        venue: Canonical journal/conference name.
        score: Similarity score in ``[0.0, 1.0]``; higher is better.
        ranking: 1-indexed position in the list (rank 1 is best).
        venue_url: Landing page of the venue, when known.
        venue_issn: ISSN of the venue, when known.
        estimated_jcr_quartile: One of ``"Q1"`` / ``"Q2"`` / ``"Q3"``
            / ``"Q4"``; ``None`` when not estimable.
        is_oa: Whether the venue is Open Access.
    """

    venue: str
    score: float
    ranking: int
    venue_url: str | None = None
    venue_issn: ISSN | None = None
    estimated_jcr_quartile: str | None = None
    is_oa: bool = False

    def __post_init__(self) -> None:
        """Enforce score range, ranking >= 1, and quartile vocabulary."""
        if not self.venue.strip():
            raise ValueError("venue must be non-empty")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0]: {self.score!r}")
        if self.ranking < 1:
            raise ValueError(f"ranking must be >= 1: {self.ranking!r}")
        if (
            self.estimated_jcr_quartile is not None
            and self.estimated_jcr_quartile not in _JCR_QUARTILES
        ):
            raise ValueError(
                f"estimated_jcr_quartile must be one of "
                f"{sorted(_JCR_QUARTILES)} or None: "
                f"{self.estimated_jcr_quartile!r}"
            )


class ScreeningDecision(str, Enum):
    """Outcome of a screening pass on a single :class:`Study`."""

    INCLUDE = "include"
    """Study satisfies the inclusion criteria."""

    EXCLUDE = "exclude"
    """Study fails one or more inclusion criteria."""

    UNDECIDED = "undecided"
    """Awaiting full-text retrieval or second-reviewer adjudication."""

    def __str__(self) -> str:
        """Return the canonical wire value."""
        return self.value
