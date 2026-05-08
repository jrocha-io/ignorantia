"""``InteractiveRendererPort`` — ISP-style extension over :class:`RendererPort`.

HTML output is the only format in v3 that benefits from incremental
rendering: the v2 ``render_chunks`` pipeline (Decision 18) appended one
section at a time to a partially built HTML file so transient failures
in section *N* did not invalidate sections 0…N-1. LaTeX and DOCX have
no equivalent — both are document-as-a-whole serialisations, so they
do *not* implement this port.

Per V3_ARCHITECTURE_PLAN.md (Interface Segregation Principle): every
renderer satisfies the basic :class:`RendererPort` contract, but
HTML-specific features live behind a narrower port that LaTeX and
DOCX do not need to satisfy.
"""

from __future__ import annotations

from abc import abstractmethod

from ignorantia.domain.render.entities import Section
from ignorantia.domain.render.ports.renderer_port import RendererPort


class InteractiveRendererPort(RendererPort):
    """Renderer that supports incremental, section-at-a-time output.

    Concrete implementations must still satisfy the full
    :class:`RendererPort` contract — :meth:`render` produces the
    complete document — and additionally expose
    :meth:`render_section`, returning the bytes for a *single*
    section in the same target format.

    The application layer can then assemble a manuscript chunk by
    chunk (caching previously rendered sections, retrying only the
    one that failed, streaming progressive output to a UI, etc.)
    without coupling to the renderer's full-document machinery.
    """

    @abstractmethod
    def render_section(self, section: Section) -> bytes:
        """Render ``section`` in isolation and return the bytes.

        The output is a *fragment* — title heading and body — without
        the surrounding document scaffold (``<html>``, ``<head>``,
        title, references). Callers are responsible for embedding the
        fragment in a host document.
        """
