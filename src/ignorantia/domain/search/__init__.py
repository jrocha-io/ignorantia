"""Search bounded context — discovering bibliographic records.

This context contains the value objects, entities, and (in F2) ports for
acquiring records from external databases. Adapters live in
``ignorantia.infrastructure.search`` and depend on the abstractions defined
here.
"""

from __future__ import annotations
