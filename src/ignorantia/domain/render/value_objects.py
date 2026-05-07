"""Value objects for the render bounded context.

Pinned wire formats below are load-bearing: pipeline manifests and
renderer configuration files persist these strings verbatim. Renaming
them is a breaking change.
"""

from __future__ import annotations

from enum import Enum


class CitationStyle(str, Enum):
    """Citation style used for both the reference list and inline cites.

    Per issue #5 (F4) the v3 render context supports four styles. The
    Strategy pattern (one :class:`CitationFormatterPort` per value)
    keeps the renderer agnostic to formatting rules.

    ``CitationStyle`` derives from :class:`str` so JSON serialisation is
    transparent — ``json.dumps(CitationStyle.ABNT) == '"abnt"'``.
    """

    ABNT = "abnt"
    """Brazilian Association of Technical Standards (NBR 6023:2018 +
    NBR 10520:2023). Mandatory when the manuscript language is ``pt-BR``."""

    APA = "apa"
    """American Psychological Association, 7th edition."""

    IEEE = "ieee"
    """Institute of Electrical and Electronics Engineers numeric style."""

    VANCOUVER = "vancouver"
    """Vancouver / ICMJE numeric style used by biomedical journals."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"abnt"``)."""
        return self.value


class OutputFormat(str, Enum):
    """Output format produced by a :class:`RendererPort` implementation."""

    HTML = "html"
    """Browser-renderable HTML5 manuscript."""

    DOCX = "docx"
    """Word-compatible Office Open XML (``.docx``)."""

    LATEX = "latex"
    """LaTeX source consumable by ``pdflatex`` / ``xelatex`` /
    ``lualatex``."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"html"``)."""
        return self.value
