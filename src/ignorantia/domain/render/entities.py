"""Entities for the render bounded context.

Following the search context conventions, entities here are frozen
:func:`dataclasses.dataclass` instances with ``slots=True``. They carry
no behaviour beyond invariant checks; rendering and citation logic
live in their respective ports.

Reference type vocabulary mirrors v2's ``format_abnt.Reference`` so the
v2 → v3 migration is a one-to-one mapping for existing fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass

_VALID_REFERENCE_TYPES: frozenset[str] = frozenset(
    {
        "article",
        "book",
        "book_chapter",
        "thesis",
        "dissertation",
        "conference",
        "electronic",
        "legislation",
        "av_resource",
        "website",
    }
)


@dataclass(frozen=True, slots=True)
class Reference:
    """A bibliographic reference rendered into a manuscript's reference list.

    The fields cover every attribute the four supported citation styles
    (ABNT, APA, IEEE, Vancouver) need. Citation formatters consume this
    flat structure and emit a fully formatted string.

    Attributes:
        type: One of the canonical reference types
            (``article``, ``book``, ...).
        title: Mandatory title of the work.
        authors: Author display names in source order, e.g. ``("Silva, J.",)``.
        year: Publication year, when known.
        venue: Journal name / publisher / conference name / institution.
        volume: Volume number (articles, journals).
        issue: Issue number (articles).
        pages: Page range, e.g. ``"100-110"``.
        doi: Digital Object Identifier in raw form.
        url: Landing page or repository URL.
        accessed: ISO date the resource was accessed (electronic refs).
        location: Place of publication (city).
        publisher: Publisher name (books, conference proceedings).
        chapter_title: Chapter title for ``book_chapter`` references.
        book_editors: Editor names for ``book_chapter`` references.
        program: Graduate program name (theses, dissertations).
        institution: Granting institution (theses, dissertations).
        language: ISO 639-1 / locale code; ``"en"`` by default.
    """

    type: str
    title: str
    authors: tuple[str, ...]
    year: int | None = None
    venue: str = ""
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    accessed: str | None = None
    location: str | None = None
    publisher: str | None = None
    chapter_title: str | None = None
    book_editors: tuple[str, ...] | None = None
    program: str | None = None
    institution: str | None = None
    language: str = "en"

    def __post_init__(self) -> None:
        """Reject reference types outside the canonical vocabulary."""
        if self.type not in _VALID_REFERENCE_TYPES:
            raise ValueError(
                f"unknown reference type: {self.type!r}; "
                f"valid options are {sorted(_VALID_REFERENCE_TYPES)}"
            )


@dataclass(frozen=True, slots=True)
class Section:
    """A first-level section in the manuscript body.

    Attributes:
        id: Stable identifier used for cross-references and anchors.
        title: Display title (rendered as a heading).
        body_md: Markdown body. Renderers convert it to their target
            format (HTML, LaTeX, ...).
    """

    id: str
    title: str
    body_md: str

    def __post_init__(self) -> None:
        """Section identifiers are required for stable anchors."""
        if not self.id:
            raise ValueError("Section.id must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ManuscriptDoc:
    """The full manuscript ready for rendering.

    A :class:`ManuscriptDoc` is the input contract of every
    :class:`RendererPort` implementation. It bundles the metadata,
    body sections and reference list a renderer needs to produce a
    self-contained artefact (HTML, DOCX, LaTeX).

    Attributes:
        title: Manuscript title (mandatory).
        abstract: Plain-text abstract.
        sections: Body sections in document order.
        references: Reference list in citation order.
        language: ISO 639-1 / locale code; ``"en"`` by default. ABNT is
            mandatory when ``language == "pt-BR"`` (DD-12).
        keywords: Optional keyword list rendered after the abstract.
    """

    title: str
    abstract: str
    sections: tuple[Section, ...]
    references: tuple[Reference, ...]
    language: str = "en"
    keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Manuscripts without a title are not renderable."""
        if not self.title:
            raise ValueError("ManuscriptDoc.title must be a non-empty string")
