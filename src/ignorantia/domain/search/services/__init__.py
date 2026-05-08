"""Domain services for the search bounded context.

A *domain service* in DDD encapsulates behaviour that does not naturally
belong on an entity or value object — typically because it coordinates
multiple objects (deduplication across adapters, orchestration of fetches,
...).
"""

from __future__ import annotations
