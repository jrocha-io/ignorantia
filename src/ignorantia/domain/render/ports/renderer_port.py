"""``RendererPort`` — the seam between the render context and concrete formats.

Each output format (HTML, DOCX, LaTeX, per issue #5) is one
:class:`RendererPort` implementation. Renderers receive a fully
prepared :class:`ManuscriptDoc` and emit the artefact as ``bytes``,
which the application layer can persist or stream without further
format-specific knowledge.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.render.entities import ManuscriptDoc
from ignorantia.domain.render.value_objects import OutputFormat


class RendererPort(ABC):
    """Abstract Strategy for serialising a :class:`ManuscriptDoc`."""

    @property
    @abstractmethod
    def output_format(self) -> OutputFormat:
        """The :class:`OutputFormat` this renderer emits."""

    @abstractmethod
    def render(self, doc: ManuscriptDoc) -> bytes:
        """Render ``doc`` and return the artefact as bytes."""
