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
