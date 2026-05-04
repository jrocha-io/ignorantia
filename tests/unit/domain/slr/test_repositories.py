"""Unit tests for SLR repository ABCs.

Repositories are *interfaces* (ABCs) here; concrete implementations
(YAML, JSON, SQLite, ...) live in ``ignorantia.infrastructure.persistence``
and are introduced by F5. These tests pin the contract.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.slr.entities import Manuscript, Study
from ignorantia.domain.slr.repositories import ManuscriptRepository, StudyRepository


class _InMemoryStudyRepository(StudyRepository):
    """Minimal concrete subclass used to verify the abstract surface."""

    def __init__(self) -> None:
        self._items: dict[str, Study] = {}

    def get(self, study_id: str) -> Study | None:
        return self._items.get(study_id)

    def list_all(self) -> tuple[Study, ...]:
        return tuple(self._items.values())

    def save(self, study: Study) -> None:
        self._items[study.study_id] = study

    def delete(self, study_id: str) -> None:
        self._items.pop(study_id, None)


class _InMemoryManuscriptRepository(ManuscriptRepository):
    """Minimal concrete subclass used to verify the abstract surface."""

    def __init__(self) -> None:
        self._items: dict[str, Manuscript] = {}

    def get(self, review_id: str) -> Manuscript | None:
        return self._items.get(review_id)

    def save(self, review_id: str, manuscript: Manuscript) -> None:
        self._items[review_id] = manuscript


class TestStudyRepositoryIsAbstract:
    """The base class cannot be used directly."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            StudyRepository()  # type: ignore[abstract]

    def test_concrete_implementation_can_be_instantiated(self) -> None:
        assert isinstance(_InMemoryStudyRepository(), StudyRepository)


class TestStudyRepositoryContract:
    """The interface methods behave correctly when implemented."""

    def test_save_then_get_returns_same_study(self) -> None:
        repo = _InMemoryStudyRepository()
        s = Study(study_id="S001", title="A")
        repo.save(s)
        assert repo.get("S001") == s

    def test_get_unknown_id_returns_none(self) -> None:
        assert _InMemoryStudyRepository().get("S999") is None

    def test_list_all_yields_all_saved_studies(self) -> None:
        repo = _InMemoryStudyRepository()
        a = Study(study_id="S001", title="A")
        b = Study(study_id="S002", title="B")
        repo.save(a)
        repo.save(b)
        assert set(repo.list_all()) == {a, b}

    def test_delete_removes_existing_study(self) -> None:
        repo = _InMemoryStudyRepository()
        repo.save(Study(study_id="S001", title="A"))
        repo.delete("S001")
        assert repo.get("S001") is None

    def test_delete_unknown_id_is_idempotent(self) -> None:
        _InMemoryStudyRepository().delete("S999")  # must not raise


class TestManuscriptRepositoryIsAbstract:
    """The base class cannot be used directly."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            ManuscriptRepository()  # type: ignore[abstract]

    def test_concrete_implementation_can_be_instantiated(self) -> None:
        assert isinstance(_InMemoryManuscriptRepository(), ManuscriptRepository)


class TestManuscriptRepositoryContract:
    """The interface methods behave correctly when implemented."""

    def test_save_then_get_returns_same_manuscript(self) -> None:
        repo = _InMemoryManuscriptRepository()
        m = Manuscript(title="A review")
        repo.save("R-1", m)
        assert repo.get("R-1") == m

    def test_get_unknown_review_id_returns_none(self) -> None:
        assert _InMemoryManuscriptRepository().get("R-999") is None
