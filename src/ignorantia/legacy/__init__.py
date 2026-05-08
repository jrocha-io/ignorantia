"""Backwards-compatibility shims for v2 entry points.

The v2 (2.x) Ignorantia API lived as standalone scripts in the
project's ``scripts/`` directory:

* ``scripts/render_v2.py``         — single-pass HTML renderer
* ``scripts/render_chunks.py``     — incremental HTML chunks renderer
                                      (Decision 18 / DD-13 canonical)
* ``scripts/render_manuscript.py`` — top-level renderer dispatcher
* ``scripts/format_abnt.py``       — ABNT NBR 6023 reference formatter
* ``scripts/pipeline_finalize.py`` — Phase-7 pipeline orchestrator (E10)

v3 reorganises that surface area into bounded contexts under
:mod:`ignorantia.domain`, :mod:`ignorantia.application` and
:mod:`ignorantia.interface`. This compat layer exists so callers
still depending on the v2 import paths get a clear, actionable
deprecation warning the first time they reach for the old name.

Importing :mod:`ignorantia.legacy` (or any submodule) emits a
:class:`DeprecationWarning`. The ``pyproject.toml`` test config
turns those into errors so tests touching the legacy surface must
opt-in with ``pytest.warns(DeprecationWarning)``.

The :func:`migration_guide` function returns a structured table of
the v2 → v3 mapping, keyed by v2 entry-point name.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

warnings.warn(
    "ignorantia.legacy provides v2 compatibility shims and will be removed "
    "in v4. Migrate to the v3 CLI (`ignorantia --help`) or the use cases "
    "in `ignorantia.application.use_cases`. See "
    "`ignorantia.legacy.migration_guide()` for the v2 → v3 mapping.",
    DeprecationWarning,
    stacklevel=2,
)


@dataclass(frozen=True, slots=True)
class MigrationEntry:
    """One row of the v2 → v3 mapping returned by :func:`migration_guide`.

    Attributes:
        v2_entry: The v2 script / function name (e.g.
            ``"scripts/render_v2.py"``).
        v3_target: Where the equivalent v3 surface lives (e.g.
            ``"ignorantia render --format html"``).
        notes: Free-form migration notes — gotchas, semantic changes,
            optional flags worth highlighting.
    """

    v2_entry: str
    v3_target: str
    notes: str


_MIGRATION_TABLE: tuple[MigrationEntry, ...] = (
    MigrationEntry(
        v2_entry="scripts/render_v2.py",
        v3_target="`ignorantia render --format html` (HtmlRenderer)",
        notes=(
            "v3 produces a clean academic skeleton with no themes / no JS. "
            "DD-13 (v2.22.0) marked render_v2.py as alternative; v3 ships "
            "only the canonical HTML output."
        ),
    ),
    MigrationEntry(
        v2_entry="scripts/render_chunks.py",
        v3_target="HtmlRenderer.render_section + InteractiveRendererPort",
        notes=(
            "Incremental rendering moves to the InteractiveRendererPort "
            "abstraction (PR #56). Full-document and section-by-section "
            "share the same renderer; the latter is exposed for callers "
            "that need to append per-section."
        ),
    ),
    MigrationEntry(
        v2_entry="scripts/render_manuscript.py",
        v3_target="`ignorantia render` (with --format and --citation-style)",
        notes=(
            "The dispatcher's runtime branches on (--format, --citation-style) "
            "are now Click options on the unified `render` subcommand."
        ),
    ),
    MigrationEntry(
        v2_entry="scripts/format_abnt.py",
        v3_target="ignorantia.infrastructure.render.citation.abnt_formatter",
        notes=(
            "ABNT NBR 6023:2018 + NBR 10520:2023 lives behind the "
            "CitationFormatterPort Strategy. Use `--citation-style abnt` "
            "from the `render` CLI subcommand or instantiate "
            "AbntCitationFormatter directly."
        ),
    ),
    MigrationEntry(
        v2_entry="scripts/pipeline_finalize.py",
        v3_target="`ignorantia finalize` + ignorantia.domain.pipeline.PipelineExecutor",
        notes=(
            "PIPELINE_STEPS registry preserved as the registry pattern in "
            "domain/pipeline; the CLI wraps it via FinalizePipelineUseCase. "
            "Concrete v2 steps migrate into infrastructure/pipeline/ "
            "incrementally — see V3_ARCHITECTURE_PLAN.md."
        ),
    ),
)


def migration_guide() -> tuple[MigrationEntry, ...]:
    """Return the v2 → v3 migration mapping in entry-name order.

    Useful for tooling that wants to display the migration table to
    users (CLI doctor, docs site, IDE extension). The tuple is
    immutable; callers should treat it as read-only.
    """
    return _MIGRATION_TABLE


def lookup(v2_entry: str) -> MigrationEntry | None:
    """Return the migration entry for ``v2_entry``, or ``None`` if not listed.

    The match is exact — callers pass the full v2 path
    (``"scripts/render_v2.py"``) or the function name and get back
    the migration target. Returns ``None`` so callers can fall back
    to the generic guide in their own UX.
    """
    for entry in _MIGRATION_TABLE:
        if entry.v2_entry == v2_entry:
            return entry
    return None
