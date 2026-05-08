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

    @classmethod
    def builder(cls) -> ManuscriptDocBuilder:
        """Return a fresh :class:`ManuscriptDocBuilder`.

        The Builder offers a fluent way to assemble a manuscript when
        sections and references arrive incrementally — instead of
        accumulating ``list``s and converting them to tuples at the
        end, callers chain ``add_section`` / ``add_reference`` calls.
        """
        return ManuscriptDocBuilder()


class ManuscriptDocBuilder:
    """Fluent builder producing :class:`ManuscriptDoc` instances.

    All setters return ``self`` so calls can be chained. The Builder
    keeps mutable internal state for sections, references and
    keywords; :meth:`build` snapshots that state into the immutable
    frozen ``ManuscriptDoc`` and the Builder remains reusable
    afterwards (useful when assembling related documents that share
    most metadata).
    """

    __slots__ = (
        "_abstract",
        "_keywords",
        "_language",
        "_references",
        "_sections",
        "_title",
    )

    def __init__(self) -> None:
        """Start with empty fields; ``title`` is required by :meth:`build`."""
        self._title: str = ""
        self._abstract: str = ""
        self._language: str = "en"
        self._sections: list[Section] = []
        self._references: list[Reference] = []
        self._keywords: list[str] = []

    def title(self, value: str) -> ManuscriptDocBuilder:
        """Set the manuscript title."""
        self._title = value
        return self

    def abstract(self, value: str) -> ManuscriptDocBuilder:
        """Set the abstract."""
        self._abstract = value
        return self

    def language(self, code: str) -> ManuscriptDocBuilder:
        """Set the ISO 639-1 / locale code."""
        self._language = code
        return self

    def keywords(self, values: tuple[str, ...]) -> ManuscriptDocBuilder:
        """Replace the keyword list."""
        self._keywords = list(values)
        return self

    def add_keyword(self, value: str) -> ManuscriptDocBuilder:
        """Append a single keyword."""
        if not value:
            raise ValueError("keyword must be a non-empty string")
        self._keywords.append(value)
        return self

    def add_section(self, section: Section) -> ManuscriptDocBuilder:
        """Append a body section in insertion order."""
        self._sections.append(section)
        return self

    def add_reference(self, reference: Reference) -> ManuscriptDocBuilder:
        """Append a reference in citation order."""
        self._references.append(reference)
        return self

    def build(self) -> ManuscriptDoc:
        """Snapshot the current state into a frozen :class:`ManuscriptDoc`."""
        return ManuscriptDoc(
            title=self._title,
            abstract=self._abstract,
            sections=tuple(self._sections),
            references=tuple(self._references),
            language=self._language,
            keywords=tuple(self._keywords),
        )
