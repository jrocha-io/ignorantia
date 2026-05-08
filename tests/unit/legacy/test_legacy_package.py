"""Unit tests for :mod:`ignorantia.legacy`.

The package emits a :class:`DeprecationWarning` at import time. The
project's ``pyproject.toml`` turns those into errors for the
``ignorantia`` namespace, so tests must opt in with
:func:`pytest.warns` — the warning *must* fire, otherwise the
project's compatibility-layer contract is broken.
"""

from __future__ import annotations

import importlib
import sys

import pytest


def _reload_legacy():
    """Force a fresh import so the module-level warning fires again.

    Tests that need to observe the import-time warning evict the
    cached module and re-import. Without this the second invocation
    of ``import ignorantia.legacy`` would be a no-op (Python caches
    successful imports).
    """
    sys.modules.pop("ignorantia.legacy", None)
    return importlib.import_module("ignorantia.legacy")


class TestImportWarning:
    def test_import_emits_deprecation_warning(self) -> None:
        with pytest.warns(DeprecationWarning, match="ignorantia.legacy"):
            _reload_legacy()

    def test_warning_points_users_at_v3_cli(self) -> None:
        with pytest.warns(DeprecationWarning) as captured:
            _reload_legacy()
        joined = " ".join(str(w.message) for w in captured)
        assert "ignorantia --help" in joined
        assert "migration_guide" in joined


class TestMigrationGuide:
    def test_returns_a_tuple_with_entries(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        guide = legacy.migration_guide()
        assert isinstance(guide, tuple)
        assert len(guide) >= 5  # render_v2, chunks, manuscript, format_abnt, finalize

    def test_entries_have_required_fields(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        for entry in legacy.migration_guide():
            assert entry.v2_entry
            assert entry.v3_target
            assert entry.notes

    def test_known_v2_entries_are_present(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        v2_paths = {e.v2_entry for e in legacy.migration_guide()}
        for required in (
            "scripts/render_v2.py",
            "scripts/render_chunks.py",
            "scripts/render_manuscript.py",
            "scripts/format_abnt.py",
            "scripts/pipeline_finalize.py",
        ):
            assert required in v2_paths, f"{required!r} missing from migration table"

    def test_entries_are_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        entry = legacy.migration_guide()[0]
        with pytest.raises(FrozenInstanceError):
            entry.v2_entry = "x"  # type: ignore[misc]


class TestLookup:
    def test_lookup_returns_entry_for_known_v2_path(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        entry = legacy.lookup("scripts/render_v2.py")
        assert entry is not None
        assert "render" in entry.v3_target.lower()

    def test_lookup_returns_none_for_unknown_v2_path(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        assert legacy.lookup("scripts/no_such_script.py") is None

    def test_lookup_does_not_match_partial_paths(self) -> None:
        # The contract is exact-match. Callers passing a function name
        # without the path get None and should fall back to the table.
        with pytest.warns(DeprecationWarning):
            legacy = _reload_legacy()
        assert legacy.lookup("render_v2.py") is None
