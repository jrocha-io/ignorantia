"""Data Transfer Objects between layers.

This module hosts the typed DTOs that flow across the application
boundary. Per ``V3_ARCHITECTURE_PLAN.md`` the rule is *no domain leak
to CLI* — interfaces (CLI, HTTP, etc.) only ever see DTOs from this
module, never raw domain entities or value objects.

DTOs are frozen dataclasses with ``slots=True`` (search-context
convention). They are intentionally simple shape-only carriers — no
business logic, no validation beyond "non-empty identity field".
That belongs in the domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SectionInputDto:
    """One body section in a :class:`RenderManuscriptCommand`."""

    id: str
    title: str
    body_md: str


@dataclass(frozen=True, slots=True)
class ReferenceInputDto:
    """One reference entry in a :class:`RenderManuscriptCommand`.

    The shape mirrors :class:`Reference` from ``domain.render``, with
    the same field names. The DTO exists so the interface layer can
    build references without importing domain types — translation to
    the domain happens inside the use case.
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


@dataclass(frozen=True, slots=True)
class RenderManuscriptCommand:
    """Input DTO for :class:`RenderManuscriptUseCase`.

    The shape is intentionally flat — interface code (CLI, HTTP)
    constructs this from raw inputs without ever touching a domain
    entity. The use case translates it to a :class:`ManuscriptDoc`
    via the F4j Builder.
    """

    title: str
    abstract: str = ""
    language: str = "en"
    keywords: tuple[str, ...] = field(default_factory=tuple)
    sections: tuple[SectionInputDto, ...] = field(default_factory=tuple)
    references: tuple[ReferenceInputDto, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Manuscripts without titles are not renderable; reject early."""
        if not self.title:
            raise ValueError("RenderManuscriptCommand.title must be a non-empty string")


@dataclass(frozen=True, slots=True)
class RenderManuscriptResult:
    """Output DTO for :class:`RenderManuscriptUseCase`.

    Attributes:
        output_format: Wire string for the format produced
            (``"html"``, ``"docx"``, ``"latex"``). Mirrors
            :class:`OutputFormat.value`.
        artifact_bytes: The rendered artefact as raw bytes. The
            interface layer is responsible for persisting / streaming.
        byte_size: ``len(artifact_bytes)``. Echoed for convenience —
            saves callers the size lookup when logging progress.
    """

    output_format: str
    artifact_bytes: bytes
    byte_size: int
