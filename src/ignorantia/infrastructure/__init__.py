"""Infrastructure layer — concrete implementations of domain ports.

Modules here may depend on ``ignorantia.domain`` and on standard-library
I/O facilities (urllib, sqlite3, ...). The dependency direction is *from
infrastructure to domain*, never the reverse.
"""

from __future__ import annotations
