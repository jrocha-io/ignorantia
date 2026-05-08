"""Unit tests for the render bounded context value objects.

The wire format of :class:`CitationStyle` and :class:`OutputFormat` is
load-bearing: downstream artefacts (renderer manifests, pipeline
orchestration JSON) carry these values verbatim. The tests below pin
them so the v2 → v3 transition cannot silently relabel a citation
style.
"""

from __future__ import annotations

import json

import pytest

from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat


class TestCitationStyleCanonicalValues:
    """Pin the four supported citation styles (issue #5)."""

    def test_abnt_is_canonical_string(self) -> None:
        assert CitationStyle.ABNT.value == "abnt"

    def test_apa_is_canonical_string(self) -> None:
        assert CitationStyle.APA.value == "apa"

    def test_ieee_is_canonical_string(self) -> None:
        assert CitationStyle.IEEE.value == "ieee"

    def test_vancouver_is_canonical_string(self) -> None:
        assert CitationStyle.VANCOUVER.value == "vancouver"

    def test_only_four_canonical_styles(self) -> None:
        assert {s.value for s in CitationStyle} == {"abnt", "apa", "ieee", "vancouver"}


class TestCitationStyleStringBehaviour:
    def test_is_str_subclass(self) -> None:
        assert isinstance(CitationStyle.ABNT, str)

    def test_str_returns_canonical_value(self) -> None:
        assert str(CitationStyle.APA) == "apa"

    def test_json_dumps_round_trip(self) -> None:
        encoded = json.dumps({"style": CitationStyle.IEEE})
        assert json.loads(encoded) == {"style": "ieee"}


class TestCitationStyleConstruction:
    @pytest.mark.parametrize("value", ["abnt", "apa", "ieee", "vancouver"])
    def test_construct_from_canonical_string(self, value: str) -> None:
        assert CitationStyle(value).value == value

    @pytest.mark.parametrize("invalid", ["ABNT", "mla", "chicago", "", "ABNT-2018"])
    def test_rejects_non_canonical_strings(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            CitationStyle(invalid)


class TestOutputFormatCanonicalValues:
    def test_html(self) -> None:
        assert OutputFormat.HTML.value == "html"

    def test_docx(self) -> None:
        assert OutputFormat.DOCX.value == "docx"

    def test_latex(self) -> None:
        assert OutputFormat.LATEX.value == "latex"

    def test_only_three_canonical_formats(self) -> None:
        assert {f.value for f in OutputFormat} == {"html", "docx", "latex"}


class TestOutputFormatStringBehaviour:
    def test_is_str_subclass(self) -> None:
        assert isinstance(OutputFormat.HTML, str)

    def test_str_returns_canonical_value(self) -> None:
        assert str(OutputFormat.LATEX) == "latex"
