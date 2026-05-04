"""Unit tests for the SLR bounded context value objects.

``DOI`` and ``ISSN`` normalise raw identifiers received from the search
context (where they are still ``str``). Validation here is the
anti-corruption boundary between external data and the SLR aggregate.
"""

from __future__ import annotations

import dataclasses

import pytest

from ignorantia.domain.slr.value_objects import (
    DOI,
    ISSN,
    Language,
    ScreeningDecision,
)


class TestDOIConstruction:
    """Construction and validation of canonical DOIs (Crossref grammar)."""

    @pytest.mark.parametrize(
        "raw",
        [
            "10.1234/foo.bar",
            "10.1038/s41586-021-03819-2",
            "10.1109/TIT.2023.1234567",
            "10.1234/abc-def_ghi.jkl",
        ],
    )
    def test_accepts_well_formed_dois(self, raw: str) -> None:
        assert DOI(raw).value == raw.lower()

    @pytest.mark.parametrize(
        "raw",
        ["", "10.", "10.1/", "abc/def", "11.1234/x", "10/1234"],
    )
    def test_rejects_malformed(self, raw: str) -> None:
        with pytest.raises(ValueError):
            DOI(raw)


class TestDOINormalization:
    """The canonical form is lowercase, with no URL prefix."""

    def test_strips_doi_org_url_prefix(self) -> None:
        assert DOI("https://doi.org/10.1234/x").value == "10.1234/x"

    def test_strips_dx_doi_org_url_prefix(self) -> None:
        assert DOI("http://dx.doi.org/10.1234/x").value == "10.1234/x"

    def test_lowercases(self) -> None:
        assert DOI("10.1234/ABC").value == "10.1234/abc"

    def test_strips_whitespace(self) -> None:
        assert DOI("  10.1234/x  ").value == "10.1234/x"


class TestDOIEquality:
    """Two DOIs that normalise to the same canonical form are equal."""

    def test_equal_after_normalization(self) -> None:
        a = DOI("https://doi.org/10.1234/X")
        b = DOI("10.1234/x")
        assert a == b

    def test_doi_is_immutable(self) -> None:
        d = DOI("10.1234/x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.value = "10.5678/y"  # type: ignore[misc]

    def test_str_returns_canonical_value(self) -> None:
        assert str(DOI("https://doi.org/10.1234/X")) == "10.1234/x"


class TestISSNConstruction:
    """Construction and validation of ISSN identifiers."""

    @pytest.mark.parametrize(
        "raw,canonical",
        [
            ("0028-0836", "0028-0836"),
            ("00280836", "0028-0836"),
            ("1234-567X", "1234-567X"),
            ("1234567X", "1234-567X"),
            ("  0028-0836  ", "0028-0836"),
        ],
    )
    def test_accepts_and_normalizes(self, raw: str, canonical: str) -> None:
        assert ISSN(raw).value == canonical

    @pytest.mark.parametrize(
        "raw",
        ["", "0028-083", "0028-08366", "ABCD-1234", "0028 0836", "0028-083x"],
    )
    def test_rejects_malformed(self, raw: str) -> None:
        with pytest.raises(ValueError):
            ISSN(raw)

    def test_issn_is_immutable(self) -> None:
        i = ISSN("0028-0836")
        with pytest.raises(dataclasses.FrozenInstanceError):
            i.value = "0000-0000"  # type: ignore[misc]


class TestLanguage:
    """Language identifiers (ISO 639-1 two-letter codes)."""

    @pytest.mark.parametrize("code", ["en", "pt", "es", "fr", "de"])
    def test_accepts_two_letter_codes(self, code: str) -> None:
        assert Language(code).value == code

    def test_lowercases(self) -> None:
        assert Language("EN").value == "en"

    @pytest.mark.parametrize("invalid", ["", "e", "eng", "12", "x!"])
    def test_rejects_malformed(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            Language(invalid)

    def test_language_is_immutable(self) -> None:
        lang = Language("en")
        with pytest.raises(dataclasses.FrozenInstanceError):
            lang.value = "pt"  # type: ignore[misc]


class TestScreeningDecision:
    """Editorial outcome of a screening pass on a single :class:`Study`."""

    def test_canonical_values(self) -> None:
        assert {d.value for d in ScreeningDecision} == {
            "include",
            "exclude",
            "undecided",
        }

    def test_is_str_subclass(self) -> None:
        assert isinstance(ScreeningDecision.INCLUDE, str)

    def test_str_returns_canonical_value(self) -> None:
        assert str(ScreeningDecision.EXCLUDE) == "exclude"

    @pytest.mark.parametrize("value", ["include", "exclude", "undecided"])
    def test_construct_from_canonical_string(self, value: str) -> None:
        assert ScreeningDecision(value).value == value

    @pytest.mark.parametrize("invalid", ["INCLUDE", "yes", "no", ""])
    def test_rejects_non_canonical_strings(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            ScreeningDecision(invalid)
