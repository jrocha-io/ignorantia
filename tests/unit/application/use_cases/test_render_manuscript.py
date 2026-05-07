"""Unit tests for :class:`RenderManuscriptUseCase`.

The use case is exercised against a real :class:`HtmlRenderer` +
:class:`ApaCitationFormatter` pair. Renderers are deterministic and
fast, so mocking them adds friction without value — the real
assembly is what we want to pin.
"""

from __future__ import annotations

import pytest

from ignorantia.application.dtos import (
    ReferenceInputDto,
    RenderManuscriptCommand,
    RenderManuscriptResult,
    SectionInputDto,
)
from ignorantia.application.use_cases.render_manuscript import (
    RenderManuscriptUseCase,
)
from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.value_objects import OutputFormat
from ignorantia.infrastructure.render.citation.apa_formatter import (
    ApaCitationFormatter,
)
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer
from ignorantia.infrastructure.render.latex_renderer import LatexRenderer


@pytest.fixture
def html_use_case() -> RenderManuscriptUseCase:
    return RenderManuscriptUseCase(
        renderer=HtmlRenderer(formatter=ApaCitationFormatter()),
        formatter=ApaCitationFormatter(),
    )


@pytest.fixture
def latex_use_case() -> RenderManuscriptUseCase:
    return RenderManuscriptUseCase(
        renderer=LatexRenderer(formatter=ApaCitationFormatter()),
        formatter=ApaCitationFormatter(),
    )


def _full_command() -> RenderManuscriptCommand:
    return RenderManuscriptCommand(
        title="A Systematic Review",
        abstract="This study evaluates X.",
        language="en",
        keywords=("evidence", "review"),
        sections=(
            SectionInputDto(id="intro", title="Introduction", body_md="Body."),
            SectionInputDto(id="methods", title="Methods", body_md="Methods body."),
        ),
        references=(
            ReferenceInputDto(
                type="article",
                title="Quality of evidence",
                authors=("Silva, J. P.",),
                year=2024,
                venue="Journal",
            ),
        ),
    )


class TestRenderManuscriptUseCaseHappyPath:
    def test_execute_returns_render_manuscript_result(
        self, html_use_case: RenderManuscriptUseCase
    ) -> None:
        result = html_use_case.execute(_full_command())
        assert isinstance(result, RenderManuscriptResult)

    def test_artifact_bytes_carry_rendered_output(
        self, html_use_case: RenderManuscriptUseCase
    ) -> None:
        result = html_use_case.execute(_full_command())
        assert isinstance(result.artifact_bytes, bytes)
        assert result.artifact_bytes
        # Title surfaces in the rendered HTML.
        assert b"A Systematic Review" in result.artifact_bytes

    def test_output_format_matches_renderer(self, html_use_case: RenderManuscriptUseCase) -> None:
        result = html_use_case.execute(_full_command())
        assert result.output_format == "html"

    def test_byte_size_matches_artifact(self, html_use_case: RenderManuscriptUseCase) -> None:
        result = html_use_case.execute(_full_command())
        assert result.byte_size == len(result.artifact_bytes)


class TestRenderManuscriptUseCaseRenderersAreInterchangeable:
    def test_latex_renderer_produces_latex_output(
        self, latex_use_case: RenderManuscriptUseCase
    ) -> None:
        result = latex_use_case.execute(_full_command())
        assert result.output_format == OutputFormat.LATEX.value
        assert b"\\documentclass" in result.artifact_bytes


class TestRenderManuscriptUseCaseTranslation:
    def test_minimum_command_renders_without_error(
        self, html_use_case: RenderManuscriptUseCase
    ) -> None:
        # Missing optional fields (no sections, no references) must
        # still produce a valid artefact — the use case should not
        # require sections / references to be present.
        result = html_use_case.execute(RenderManuscriptCommand(title="Bare"))
        assert b"Bare" in result.artifact_bytes

    def test_section_dto_propagates_to_rendered_output(
        self, html_use_case: RenderManuscriptUseCase
    ) -> None:
        cmd = RenderManuscriptCommand(
            title="x",
            sections=(SectionInputDto(id="s1", title="Methods", body_md="Body."),),
        )
        result = html_use_case.execute(cmd)
        assert b'id="s1"' in result.artifact_bytes
        assert b"Methods" in result.artifact_bytes

    def test_reference_dto_propagates_through_formatter(
        self, html_use_case: RenderManuscriptUseCase
    ) -> None:
        cmd = RenderManuscriptCommand(
            title="x",
            references=(
                ReferenceInputDto(
                    type="article",
                    title="Quality of evidence",
                    authors=("Silva, J. P.",),
                    year=2024,
                    venue="Journal",
                ),
            ),
        )
        result = html_use_case.execute(cmd)
        # APA formatter renders the author + year inline.
        assert b"Silva" in result.artifact_bytes
        assert b"2024" in result.artifact_bytes


class TestRenderManuscriptUseCaseDoesNotLeakDomain:
    def test_execute_returns_dto_not_manuscript_doc(
        self, html_use_case: RenderManuscriptUseCase
    ) -> None:
        result = html_use_case.execute(_full_command())
        assert not isinstance(result, ManuscriptDoc)
        assert not isinstance(result, (Section, Reference))
        assert isinstance(result, RenderManuscriptResult)
