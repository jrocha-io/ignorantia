"""Contract tests for :class:`CitationFormatterPort`.

The port is the seam between the render bounded context and the four
concrete citation strategies (ABNT, APA, IEEE, Vancouver). These tests
pin the *shape* of the port — they do not yet assert the formatted
output of any particular style; that is the job of each formatter's
own unit tests in F4b-F4e.
"""

from __future__ import annotations

import inspect
from abc import ABC

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle


class _StubFormatter(CitationFormatterPort):
    """Minimal concrete implementation used to assert the contract."""

    @property
    def style(self) -> CitationStyle:
        return CitationStyle.ABNT

    def format_reference(self, ref: Reference) -> str:
        return ref.title

    def format_inline_citation(
        self,
        ref: Reference,
        *,
        page: str | None = None,
        index: int | None = None,
    ) -> str:
        del page, index
        return ref.title


class TestPortIsAbstract:
    def test_is_abc(self) -> None:
        assert issubclass(CitationFormatterPort, ABC)

    def test_cannot_instantiate_without_implementations(self) -> None:
        with pytest.raises(TypeError):
            CitationFormatterPort()  # type: ignore[abstract]

    def test_required_methods(self) -> None:
        members = {name for name, _ in inspect.getmembers(CitationFormatterPort)}
        assert "format_reference" in members
        assert "format_inline_citation" in members
        assert "style" in members


class TestStubSatisfiesContract:
    def test_concrete_subclass_can_instantiate(self) -> None:
        formatter = _StubFormatter()
        assert formatter.style is CitationStyle.ABNT

    def test_format_reference_returns_str(self) -> None:
        formatter = _StubFormatter()
        ref = Reference(type="article", title="Hello", authors=())
        assert formatter.format_reference(ref) == "Hello"

    def test_format_inline_citation_returns_str(self) -> None:
        formatter = _StubFormatter()
        ref = Reference(type="article", title="Hello", authors=())
        assert formatter.format_inline_citation(ref) == "Hello"

    def test_format_inline_citation_accepts_page_keyword(self) -> None:
        formatter = _StubFormatter()
        ref = Reference(type="article", title="Hello", authors=())
        assert formatter.format_inline_citation(ref, page="42") == "Hello"

    def test_format_inline_citation_accepts_index_keyword(self) -> None:
        formatter = _StubFormatter()
        ref = Reference(type="article", title="Hello", authors=())
        assert formatter.format_inline_citation(ref, index=1) == "Hello"
