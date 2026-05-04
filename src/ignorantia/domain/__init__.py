"""Domain layer — pure business logic with no I/O dependencies.

The domain layer is divided into bounded contexts (DDD):

* :mod:`ignorantia.domain.search` — discovering and fetching bibliographic
  records from external databases.
* :mod:`ignorantia.domain.slr` — systematic literature review aggregate
  (studies, manuscripts, reviews) and the editorial workflow that operates
  on it.

Every module under this package is forbidden from importing from
``ignorantia.infrastructure`` or any third-party I/O library. Dependencies
are injected via ports defined under each context.
"""

from __future__ import annotations
