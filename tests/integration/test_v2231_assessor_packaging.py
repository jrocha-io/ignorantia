"""Tests v2.23.1 (Fix 15 of RS-42 dogfood remediation) — assessor in dist package.

The dogfood RS-42 transcripts diagnosed that ``render_v2.py`` (which imports
``from assessor.visual_aids import ...``) and ``unified_assessment.py``
(which depends on the same package) failed at runtime in deployed skills
because ``scripts/assessor/`` was not in the production package allowlist.

Before Fix 15, ``build_production_package.py`` only shipped ``scripts/*.py``
(top-level) and ``scripts/searches/*.py``. The 10+ modules in
``scripts/assessor/`` (``visual_aids``, ``eliminators``, ``helpers``,
``audit``, ``main``, ``plagiarism``, ``rubric``, ``self_test``,
``sprint_badge``) never reached the deployed zip.

Fix 15 adds ``("scripts/assessor", "*.py")`` to ``SCRIPTS_SUBDIR_GLOB``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_build_module():
    """Load build_production_package.py as a module (not via plain import,
    because the script lives in scripts/ which Python doesn't treat as a
    package)."""
    spec = importlib.util.spec_from_file_location(
        "build_production_package",
        ROOT / "scripts" / "build_production_package.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Allowlist contents
# ---------------------------------------------------------------------------


def test_scripts_assessor_is_in_subdir_allowlist() -> None:
    """The packaging script must include ``scripts/assessor/*.py``."""
    mod = _load_build_module()
    paths = [entry[0] for entry in mod.SCRIPTS_SUBDIR_GLOB]
    assert "scripts/assessor" in paths, (
        "scripts/assessor/ must be in SCRIPTS_SUBDIR_GLOB so render_v2.py "
        "and unified_assessment.py can import from it in deployed skills."
    )


def test_scripts_assessor_glob_pattern_is_python_files() -> None:
    mod = _load_build_module()
    for rel_dir, pattern in mod.SCRIPTS_SUBDIR_GLOB:
        if rel_dir == "scripts/assessor":
            assert pattern == "*.py", (
                "scripts/assessor/ entry should glob *.py to ship all "
                "modules; got pattern: " + repr(pattern)
            )


# ---------------------------------------------------------------------------
# Resolved allowlist actually contains the assessor modules
# ---------------------------------------------------------------------------


def test_resolved_allowlist_contains_visual_aids() -> None:
    """End-to-end: ``resolve_allowlist`` returns ``scripts/assessor/visual_aids.py``.

    This is the specific module that ``render_v2.py`` imports — its absence
    was the root cause of the runtime breakage diagnosed in the dogfood.
    """
    mod = _load_build_module()
    paths = mod.resolve_allowlist(ROOT)
    assert any(
        p.name == "visual_aids.py" and p.parent.name == "assessor" for p in paths
    ), (
        "scripts/assessor/visual_aids.py is missing from resolved allowlist; "
        "render_v2.py will fail at runtime in deployed skill."
    )


def test_resolved_allowlist_contains_unified_assessment_dependencies() -> None:
    """``unified_assessment.py`` lives at ``scripts/`` top-level, but it
    depends on the assessor package. Verify both ship together."""
    mod = _load_build_module()
    paths = mod.resolve_allowlist(ROOT)
    has_unified = any(p.name == "unified_assessment.py" for p in paths)
    has_assessor_main = any(
        p.name == "main.py" and p.parent.name == "assessor" for p in paths
    )
    # unified_assessment.py is in scripts/ top-level (already shipped via
    # SCRIPTS_TOP_GLOB), but assessor.main is the entry it depends on.
    if has_unified:
        assert has_assessor_main, (
            "unified_assessment.py is shipped but its dependency "
            "scripts/assessor/main.py is missing — runtime ImportError."
        )


# ---------------------------------------------------------------------------
# Regression: how many assessor modules are now shipped
# ---------------------------------------------------------------------------


def test_resolved_allowlist_includes_all_assessor_modules() -> None:
    """All ``scripts/assessor/*.py`` files in source-tree must reach dist."""
    mod = _load_build_module()
    paths = mod.resolve_allowlist(ROOT)
    assessor_dir = ROOT / "scripts" / "assessor"
    if not assessor_dir.is_dir():
        return  # source-tree state without assessor dir — nothing to assert
    expected = {p.name for p in assessor_dir.glob("*.py") if p.is_file()}
    actual = {p.name for p in paths if p.parent.name == "assessor"}
    missing = expected - actual
    assert not missing, (
        f"assessor modules missing from resolved allowlist: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# File-count guard
# ---------------------------------------------------------------------------


def test_total_file_count_within_max_files_after_fix_15() -> None:
    """Adding scripts/assessor/ must not push allowlist above MAX_FILES."""
    mod = _load_build_module()
    paths = mod.resolve_allowlist(ROOT)
    assert len(paths) <= mod.MAX_FILES, (
        f"Allowlist resolved to {len(paths)} files but MAX_FILES is {mod.MAX_FILES}. "
        f"Fix 15 added assessor/; trim something else or bump MAX_FILES "
        f"deliberately."
    )
