"""Ports (abstract interfaces) for the search bounded context.

A *port* in hexagonal architecture is a domain-defined interface that the
application speaks through. The concrete adapters live in
``ignorantia.infrastructure.search`` and implement these ports without the
domain ever importing them.
"""

from __future__ import annotations
