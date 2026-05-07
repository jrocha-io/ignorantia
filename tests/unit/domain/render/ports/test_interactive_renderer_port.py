"""Contract tests for :class:`InteractiveRendererPort`.

The port narrows :class:`RendererPort` for HTML-specific incremental
output (analogue of v2's chunks pipeline). LaTeX and DOCX renderers
deliberately do *not* implement it — those formats serialise as a
single document and have no per-section append semantics.
"""

from __future__ import annotations

import inspect
from abc import ABC

import pytest

from ignorantia.domain.render.entities import ManuscriptDoc, Section
from ignorantia.domain.render.ports.interactive_renderer_port import (
    InteractiveRendererPort,
)
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import OutputFormat


class _StubInteractiveRenderer(InteractiveRendererPort):
    """Minimal concrete renderer used for contract assertions."""

    @property
    def output_format(self) -> OutputFormat:
        return OutputFormat.HTML

    def render(self, doc: ManuscriptDoc) -> bytes:
        return doc.title.encode("utf-8")

    def render_section(self, section: Section) -> bytes:
        return section.title.encode("utf-8")


class TestPortIsAbstract:
    def test_is_abc(self) -> None:
        assert issubclass(InteractiveRendererPort, ABC)

    def test_extends_renderer_port(self) -> None:
        assert issubclass(InteractiveRendererPort, RendererPort)

    def test_cannot_instantiate_without_implementations(self) -> None:
        with pytest.raises(TypeError):
            InteractiveRendererPort()  # type: ignore[abstract]

    def test_required_methods(self) -> None:
        members = {name for name, _ in inspect.getmembers(InteractiveRendererPort)}
        assert "render" in members
        assert "render_section" in members
        assert "output_format" in members


class TestStubSatisfiesContract:
    def test_concrete_subclass_can_instantiate(self) -> None:
        renderer = _StubInteractiveRenderer()
        assert renderer.output_format is OutputFormat.HTML

    def test_render_returns_bytes(self) -> None:
        renderer = _StubInteractiveRenderer()
        doc = ManuscriptDoc(title="Hello", abstract="x", sections=(), references=())
        assert renderer.render(doc) == b"Hello"

    def test_render_section_returns_bytes(self) -> None:
        renderer = _StubInteractiveRenderer()
        section = Section(id="introduction", title="Introduction", body_md="x")
        assert renderer.render_section(section) == b"Introduction"
