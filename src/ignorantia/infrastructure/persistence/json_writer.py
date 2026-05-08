"""``JsonWriter`` — single point of JSON output writes for the v3 package.

Per ``V3_ARCHITECTURE_PLAN.md`` (DRY § Schemas validados em runtime
via jsonschema) and issue #14: every JSON payload that leaves the
process — written to disk or echoed on stdout — must be validated
against a registered schema in :mod:`ignorantia.interface.manifests`
before the bytes hit the destination. Drift between the DTO surface
and the schema fails the run loudly rather than silently shipping a
new wire format.

This module provides the infrastructure-layer counterpart to
``commands._emit`` (which validates + ``click.echo``s on stdout).
``JsonWriter.write_json`` validates + writes UTF-8 to the supplied
path, atomically (via a temporary file rename) so a crashing
process cannot leave a half-written manifest behind.

The validator is :func:`validate_manifest` from
:mod:`ignorantia.interface.manifests`, so adding a schema
automatically extends the writer's vocabulary.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ignorantia.interface.manifests import validate_manifest


class JsonWriter:
    """Write JSON manifests atomically, with schema validation up-front.

    Stateless: instances exist only because injection sites prefer
    holding a writer over importing a module-level function. Methods
    are equally fine as ``@staticmethod`` calls — :class:`JsonWriter`
    is the convention so application/infrastructure code can swap
    in test doubles without monkey-patching.
    """

    def write_json(
        self,
        payload: dict[str, Any],
        *,
        schema_name: str,
        path: Path,
        indent: int | None = None,
    ) -> int:
        """Validate ``payload`` against ``schema_name`` and write to ``path``.

        Args:
            payload: The mapping to serialise.
            schema_name: The registered manifest name in
                :mod:`ignorantia.interface.manifests` (e.g.
                ``"search_result"``).
            path: Destination file. Parent directories are created
                if missing.
            indent: Optional pretty-print indent for human-readable
                manifests. Default ``None`` (single-line, smallest).

        Returns:
            The number of bytes written.

        Raises:
            jsonschema.ValidationError: ``payload`` does not match
                ``schema_name``'s schema.
            KeyError: ``schema_name`` is not registered.
        """
        # Round-trip through json before validating so the validator
        # sees the *on-disk* shape (tuples become lists, etc.). This
        # also catches non-JSON-serialisable values up-front.
        text = json.dumps(payload, ensure_ascii=False, indent=indent)
        validate_manifest(schema_name, json.loads(text))
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = text.encode("utf-8")
        # Write to a same-directory temp file then rename, so
        # partial writes never appear at `path` (POSIX rename is
        # atomic within the same filesystem).
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(encoded)
            tmp.flush()
            os.fsync(tmp.fileno())
        # Atomic on POSIX; on Windows, replaces an existing file.
        tmp_path.replace(path)
        return len(encoded)
