"""``RenderManuscriptUseCase`` — translate a DTO to a rendered artefact.

Wraps :class:`RendererPort` + :class:`CitationFormatterPort` (F4)
behind the F6 use-case pattern. The use case takes a flat
:class:`RenderManuscriptCommand` from the interface layer, builds a
domain :class:`ManuscriptDoc` via the F4j Builder, calls the injected
renderer, and returns a flat :class:`RenderManuscriptResult` DTO so
the interface layer never touches a domain entity directly.

The renderer and citation formatter are both injected at construction
(DIP). Production wiring binds them to a concrete pair (e.g.
``HtmlRenderer + AbntCitationFormatter``); a future
``CitationFormatterFactory`` (F4f) will pick the formatter from a
:class:`CitationStyle` enum.
"""

from __future__ import annotations

from ignorantia.application.dtos import (
    ReferenceInputDto,
    RenderManuscriptCommand,
    RenderManuscriptResult,
    SectionInputDto,
)
from ignorantia.domain.render.entities import (
    ManuscriptDoc,
    Reference,
    Section,
)
from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.domain.render.ports.renderer_port import RendererPort


class RenderManuscriptUseCase:
    """Render a manuscript to a target format and return a result DTO."""

    def __init__(
        self,
        *,
        renderer: RendererPort,
        formatter: CitationFormatterPort,
    ) -> None:
        """Wire the use case to a renderer and a citation formatter.

        Args:
            renderer: The :class:`RendererPort` (DIP — production
                wiring binds it to ``HtmlRenderer`` / ``LatexRenderer``
                / ``DocxRenderer`` based on the requested format).
            formatter: The :class:`CitationFormatterPort` the renderer
                uses for the references list.
        """
        self._renderer = renderer
        self._formatter = formatter

    def execute(
        self,
        command: RenderManuscriptCommand,
    ) -> RenderManuscriptResult:
        """Build the manuscript, render it, and return the result DTO."""
        doc = _build_manuscript(command)
        artifact = self._renderer.render(doc)
        return RenderManuscriptResult(
            output_format=str(self._renderer.output_format),
            artifact_bytes=artifact,
            byte_size=len(artifact),
        )


def _build_manuscript(command: RenderManuscriptCommand) -> ManuscriptDoc:
    """Translate the flat command DTO to a domain :class:`ManuscriptDoc`."""
    builder = (
        ManuscriptDoc.builder()
        .title(command.title)
        .abstract(command.abstract)
        .language(command.language)
        .keywords(command.keywords)
    )
    for section in command.sections:
        builder = builder.add_section(_to_section(section))
    for reference in command.references:
        builder = builder.add_reference(_to_reference(reference))
    return builder.build()


def _to_section(dto: SectionInputDto) -> Section:
    return Section(id=dto.id, title=dto.title, body_md=dto.body_md)


def _to_reference(dto: ReferenceInputDto) -> Reference:
    return Reference(
        type=dto.type,
        title=dto.title,
        authors=dto.authors,
        year=dto.year,
        venue=dto.venue,
        volume=dto.volume,
        issue=dto.issue,
        pages=dto.pages,
        doi=dto.doi,
        url=dto.url,
        accessed=dto.accessed,
        location=dto.location,
        publisher=dto.publisher,
        chapter_title=dto.chapter_title,
        book_editors=dto.book_editors,
        program=dto.program,
        institution=dto.institution,
        language=dto.language,
    )
