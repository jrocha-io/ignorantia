"""JSON schemas + runtime validators for the CLI's wire formats.

Per ``V3_ARCHITECTURE_PLAN.md`` (DRY § Schemas validados em runtime
via jsonschema) every CLI subcommand validates its JSON output
against the schema for its result type *before* echoing it. The
contract is enforced at the boundary, so:

* DTO drift (a domain entity adds a field, the use case forwards it,
  but the schema doesn't know about it) trips the validator and
  fails the CLI loudly rather than silently shipping a new wire
  format to downstream tooling.
* Downstream consumers can ``$ref`` the published schemas and trust
  the contract.

The schemas themselves live as ``.schema.json`` files in this package
so they are easy to publish (one file each) and discoverable. The
public surface of this module is :func:`load_schema` and
:func:`validate_manifest` — both used by ``commands.py``.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA_DIR = Path(__file__).parent

# Maps the logical manifest name to its ``.schema.json`` filename.
# Keep this dict centralised: every CLI subcommand looks its schema
# up by name, and adding a new schema means appending one entry.
_SCHEMA_FILES: dict[str, str] = {
    "audit_result": "audit_result.schema.json",
    "finalize_pipeline_result": "finalize_pipeline_result.schema.json",
    "render_result": "render_result.schema.json",
    "search_result": "search_result.schema.json",
}


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Return the JSON-schema document for ``name``.

    Cached because schemas are small immutable JSON files; reading
    them once per process keeps the validator hot path allocation-
    free without sacrificing correctness.

    Raises:
        KeyError: ``name`` is not a registered manifest type.
    """
    try:
        filename = _SCHEMA_FILES[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown manifest schema: {name!r}; valid options are {sorted(_SCHEMA_FILES)}"
        ) from exc
    text = (_SCHEMA_DIR / filename).read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


def validate_manifest(name: str, payload: dict[str, Any]) -> None:
    """Validate ``payload`` against the schema named ``name``.

    Raises:
        jsonschema.ValidationError: when ``payload`` does not match.
        KeyError: when ``name`` is not a registered manifest type.
    """
    schema = load_schema(name)
    jsonschema.validate(instance=payload, schema=schema)


def known_manifests() -> tuple[str, ...]:
    """Return every registered manifest name in registration order."""
    return tuple(_SCHEMA_FILES)
