"""Contract tests for :class:`RendererPort`.

A renderer turns a fully-prepared :class:`ManuscriptDoc` into bytes.
The port is intentionally narrow — formats (HTML, DOCX, LaTeX) all
agree to produce ``bytes`` so the F4 application layer can persist the
artefact via a single sink.
"""

from __future__ import annotations

import inspect
from abc import ABC

import pytest

from ignorantia.domain.render.entities import ManuscriptDoc
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import OutputFormat


class _StubRenderer(RendererPort):
    """Minimal concrete renderer used for contract assertions."""

    @property
    def output_format(self) -> OutputFormat:
        return OutputFormat.HTML

    def render(self, doc: ManuscriptDoc) -> bytes:
        return doc.title.encode("utf-8")


class TestPortIsAbstract:
    def test_is_abc(self) -> None:
        assert issubclass(RendererPort, ABC)

    def test_cannot_instantiate_without_implementations(self) -> None:
        with pytest.raises(TypeError):
            RendererPort()  # type: ignore[abstract]

    def test_required_methods(self) -> None:
        members = {name for name, _ in inspect.getmembers(RendererPort)}
        assert "render" in members
        assert "output_format" in members


class TestStubSatisfiesContract:
    def test_concrete_subclass_can_instantiate(self) -> None:
        renderer = _StubRenderer()
        assert renderer.output_format is OutputFormat.HTML

    def test_render_returns_bytes(self) -> None:
        renderer = _StubRenderer()
        doc = ManuscriptDoc(title="Hello", abstract="x", sections=(), references=())
        assert renderer.render(doc) == b"Hello"
