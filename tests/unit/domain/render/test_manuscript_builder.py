"""Unit tests for :class:`ManuscriptDocBuilder`.

The Builder is a thin fluent wrapper around :class:`ManuscriptDoc`
that lets callers assemble a document step-by-step before freezing
it. This makes the ergonomic difference between::

    doc = ManuscriptDoc(
        title="...",
        abstract="...",
        sections=(s1, s2, s3),
        references=(r1, r2, r3),
        ...
    )

and::

    doc = (
        ManuscriptDoc.builder()
        .title("...")
        .abstract("...")
        .add_section(s1)
        .add_section(s2)
        .add_reference(r1)
        .build()
    )

Both forms are equivalent; the Builder simply removes the awkward
``tuple(...)`` shuffling when the caller doesn't have all sections
ready at once.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import (
    ManuscriptDoc,
    ManuscriptDocBuilder,
    Reference,
    Section,
)


class TestBuilderEntryPoint:
    def test_builder_classmethod_returns_builder(self) -> None:
        b = ManuscriptDoc.builder()
        assert isinstance(b, ManuscriptDocBuilder)

    def test_each_call_returns_a_fresh_builder(self) -> None:
        a = ManuscriptDoc.builder()
        b = ManuscriptDoc.builder()
        assert a is not b


class TestRequiredFields:
    def test_build_requires_title(self) -> None:
        with pytest.raises(ValueError):
            ManuscriptDoc.builder().build()

    def test_build_with_just_a_title(self) -> None:
        doc = ManuscriptDoc.builder().title("Hello").build()
        assert doc.title == "Hello"
        assert doc.abstract == ""
        assert doc.sections == ()
        assert doc.references == ()
        assert doc.language == "en"
        assert doc.keywords == ()


class TestFluentApi:
    def test_methods_return_self(self) -> None:
        b = ManuscriptDoc.builder()
        assert b.title("t") is b
        assert b.abstract("a") is b
        assert b.language("pt-BR") is b

    def test_full_chain(self) -> None:
        doc = (
            ManuscriptDoc.builder()
            .title("My SLR")
            .abstract("Abstract.")
            .language("pt-BR")
            .keywords(("review", "prisma"))
            .add_section(Section(id="intro", title="Intro", body_md="Hi."))
            .add_section(Section(id="meth", title="Methods", body_md=""))
            .add_reference(Reference(type="article", title="A", authors=("X",)))
            .build()
        )
        assert doc.title == "My SLR"
        assert doc.abstract == "Abstract."
        assert doc.language == "pt-BR"
        assert doc.keywords == ("review", "prisma")
        assert len(doc.sections) == 2
        assert doc.sections[0].id == "intro"
        assert doc.sections[1].id == "meth"
        assert len(doc.references) == 1


class TestSectionAndReferenceOrdering:
    def test_sections_kept_in_insertion_order(self) -> None:
        b = ManuscriptDoc.builder().title("t")
        for i in range(5):
            b.add_section(Section(id=f"s{i}", title=str(i), body_md=""))
        doc = b.build()
        assert tuple(s.id for s in doc.sections) == ("s0", "s1", "s2", "s3", "s4")

    def test_references_kept_in_insertion_order(self) -> None:
        b = ManuscriptDoc.builder().title("t")
        for i in range(3):
            b.add_reference(Reference(type="article", title=f"R{i}", authors=("X",)))
        doc = b.build()
        assert tuple(r.title for r in doc.references) == ("R0", "R1", "R2")


class TestKeywordsAndExtensionMethods:
    def test_keywords_replaces_existing(self) -> None:
        doc = ManuscriptDoc.builder().title("t").keywords(("a",)).keywords(("b", "c")).build()
        assert doc.keywords == ("b", "c")

    def test_add_keyword_appends(self) -> None:
        doc = ManuscriptDoc.builder().title("t").add_keyword("a").add_keyword("b").build()
        assert doc.keywords == ("a", "b")

    def test_add_keyword_rejects_empty(self) -> None:
        b = ManuscriptDoc.builder().title("t")
        with pytest.raises(ValueError):
            b.add_keyword("")


class TestImmutability:
    def test_build_returns_frozen_doc(self) -> None:
        doc = ManuscriptDoc.builder().title("t").build()
        with pytest.raises(AttributeError):
            doc.title = "Other"  # type: ignore[misc]

    def test_builder_can_be_reused_after_build(self) -> None:
        # Building doesn't lock the builder — useful when assembling
        # related documents that share most metadata.
        b = ManuscriptDoc.builder().title("Original")
        first = b.build()
        b.title("Variant")
        second = b.build()
        assert first.title == "Original"
        assert second.title == "Variant"
