"""Unit tests for the render bounded context entities.

These entities are the *vocabulary* every renderer and citation
formatter speaks. Keep them frozen, slots, and minimal; downstream
flexibility belongs in the ports, not in mutable state on the entities.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section


class TestReferenceConstruction:
    def test_minimal_reference(self) -> None:
        ref = Reference(type="article", title="Hello", authors=("Silva, J.",))
        assert ref.type == "article"
        assert ref.title == "Hello"
        assert ref.authors == ("Silva, J.",)
        assert ref.year is None

    def test_reference_is_frozen(self) -> None:
        ref = Reference(type="article", title="Hello", authors=())
        with pytest.raises(AttributeError):
            ref.title = "Other"  # type: ignore[misc]

    def test_authors_must_be_tuple_for_immutability(self) -> None:
        ref = Reference(type="book", title="Book", authors=("A", "B"))
        assert isinstance(ref.authors, tuple)

    def test_reference_supports_full_metadata(self) -> None:
        ref = Reference(
            type="article",
            title="A study",
            authors=("Silva, J.", "Pereira, A."),
            year=2024,
            venue="Journal X",
            volume="10",
            issue="2",
            pages="100-110",
            doi="10.1234/x",
            url="https://example.org/x",
            language="pt-BR",
        )
        assert ref.year == 2024
        assert ref.doi == "10.1234/x"
        assert ref.language == "pt-BR"


class TestReferenceTypeValidation:
    @pytest.mark.parametrize(
        "valid",
        [
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
        ],
    )
    def test_accepts_canonical_types(self, valid: str) -> None:
        assert Reference(type=valid, title="t", authors=()).type == valid

    @pytest.mark.parametrize("invalid", ["", "ARTICLE", "blogpost", "tweet"])
    def test_rejects_non_canonical_types(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            Reference(type=invalid, title="t", authors=())


class TestSection:
    def test_section_is_frozen(self) -> None:
        s = Section(id="intro", title="Introduction", body_md="hello")
        with pytest.raises(AttributeError):
            s.title = "Other"  # type: ignore[misc]

    def test_section_minimal(self) -> None:
        s = Section(id="intro", title="Introduction", body_md="")
        assert s.id == "intro"
        assert s.body_md == ""

    def test_id_cannot_be_empty(self) -> None:
        with pytest.raises(ValueError):
            Section(id="", title="Introduction", body_md="hi")


class TestManuscriptDoc:
    def _ref(self) -> Reference:
        return Reference(type="article", title="A", authors=("X",))

    def test_minimal_doc(self) -> None:
        doc = ManuscriptDoc(
            title="My SLR",
            abstract="Abstract.",
            sections=(),
            references=(),
        )
        assert doc.title == "My SLR"
        assert doc.sections == ()
        assert doc.references == ()

    def test_doc_is_frozen(self) -> None:
        doc = ManuscriptDoc(title="t", abstract="a", sections=(), references=())
        with pytest.raises(AttributeError):
            doc.title = "Other"  # type: ignore[misc]

    def test_full_doc(self) -> None:
        doc = ManuscriptDoc(
            title="My SLR",
            abstract="Abstract.",
            sections=(Section(id="intro", title="Intro", body_md="hi"),),
            references=(self._ref(),),
            language="pt-BR",
            keywords=("review", "prisma"),
        )
        assert len(doc.sections) == 1
        assert len(doc.references) == 1
        assert doc.language == "pt-BR"
        assert doc.keywords == ("review", "prisma")

    def test_title_cannot_be_empty(self) -> None:
        with pytest.raises(ValueError):
            ManuscriptDoc(title="", abstract="a", sections=(), references=())
