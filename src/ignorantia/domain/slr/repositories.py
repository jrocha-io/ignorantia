"""Repository ABCs for the SLR bounded context.

These interfaces describe how the domain talks to *some* persistence
mechanism without depending on any specific one. Concrete implementations
(YAML files, JSON, SQLite, ...) live in
``ignorantia.infrastructure.persistence`` and are wired by the
composition root.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.slr.entities import Manuscript, Study


class StudyRepository(ABC):
    """Persistence boundary for :class:`~ignorantia.domain.slr.entities.Study`."""

    @abstractmethod
    def get(self, study_id: str) -> Study | None:
        """Return the study with ``study_id`` or ``None`` if unknown."""

    @abstractmethod
    def list_all(self) -> tuple[Study, ...]:
        """Return every persisted study."""

    @abstractmethod
    def save(self, study: Study) -> None:
        """Insert or replace ``study`` (upsert semantics)."""

    @abstractmethod
    def delete(self, study_id: str) -> None:
        """Remove the study with ``study_id``; idempotent if unknown."""


class ManuscriptRepository(ABC):
    """Persistence boundary for :class:`~ignorantia.domain.slr.entities.Manuscript`.

    A manuscript is owned by one review, so the key is the review's ID.
    """

    @abstractmethod
    def get(self, review_id: str) -> Manuscript | None:
        """Return the manuscript for ``review_id`` or ``None``."""

    @abstractmethod
    def save(self, review_id: str, manuscript: Manuscript) -> None:
        """Insert or replace the manuscript associated with ``review_id``."""
