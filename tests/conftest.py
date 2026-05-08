"""Shared pytest configuration for ignorantia.

Responsibilities:
    1. Wire ``sys.path`` so legacy modules under ``scripts/`` are importable
       from any subdirectory of ``tests/`` during the v2 → v3 transition.
    2. Auto-mark tests by directory: ``unit/``, ``integration/``, ``e2e/``,
       ``contract/`` get the corresponding pytest marker without each test
       file having to declare it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO_ROOT / "scripts"
_SEARCHES = _SCRIPTS / "searches"
_COMPARISON = _SCRIPTS / "comparison"

for _path in (_SCRIPTS, _SEARCHES, _COMPARISON):
    _str = str(_path)
    if _path.exists() and _str not in sys.path:
        sys.path.insert(0, _str)


_DIR_MARKERS: dict[str, pytest.MarkDecorator] = {
    "/tests/unit/": pytest.mark.unit,
    "/tests/integration/": pytest.mark.integration,
    "/tests/e2e/": pytest.mark.e2e,
    "/tests/contract/": pytest.mark.contract,
    "/scripts/comparison/tests/": pytest.mark.integration,
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply directory-derived markers to each collected test item."""
    del config
    for item in items:
        path = str(item.fspath)
        for fragment, marker in _DIR_MARKERS.items():
            if fragment in path:
                item.add_marker(marker)
                break
