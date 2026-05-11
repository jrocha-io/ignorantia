"""Value objects for the compliance bounded context.

Two immutable shapes anchor the compliance language:

* :class:`Decision` — the outcome of a single compliance rule check
  against a manuscript. v2's ``CheckResult`` (``scripts/compliance/
  hard_rules.py``) is the predecessor; the v3 form replaces the
  loose ``passed: bool + severity: str`` pair with an explicit
  :class:`DecisionStatus` enum, so callers never have to interpret
  the truth-table of those two fields together.
* :class:`DesignDecision` — a typed pointer to a recorded
  Architecture Decision (DECISIONS.md DD-1 … DD-13). The compliance
  engine cites these to justify rule choices in audit trails.

Both are frozen dataclasses with ``slots=True`` (search-context
convention). Values are equal by content; instances are hashable.

Pinned wire formats are load-bearing: persisted compliance reports
and audit JSONs round-trip these values, so renaming an enum member
or its ``.value`` is a breaking change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class DecisionStatus(str, Enum):
    """Outcome of a single compliance rule check.

    The four values are exhaustive: a rule either passes, fails, is
    deferred to a human reviewer, or is not applicable to the
    manuscript at hand. ``DecisionStatus`` derives from :class:`str`
    so JSON serialisation is transparent —
    ``json.dumps(DecisionStatus.PASS) == '"pass"'``.
    """

    PASS = "pass"  # noqa: S105  # nosec B105 — false-positive on the literal "pass"
    """Rule satisfied. Counts as a green check in the report."""

    FAIL = "fail"
    """Rule violated. Severity determines whether it is blocking."""

    NEEDS_REVIEW = "needs_review"
    """Rule outcome cannot be determined automatically; defer to a human."""

    NOT_APPLICABLE = "not_applicable"
    """Rule does not apply to this manuscript (e.g. registration check
    on a non-empirical review). Excluded from aggregate scoring."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"pass"``)."""
        return self.value


class Severity(str, Enum):
    """How serious a failed compliance rule is.

    The three levels mirror v2: ``blocking`` failures stop submission,
    ``major`` failures lower the aggregate score sharply, ``minor``
    failures lower it slightly.
    """

    BLOCKING = "blocking"
    """Manuscript cannot be submitted with this rule failing."""

    MAJOR = "major"
    """Significant compliance gap; reviewer must address."""

    MINOR = "minor"
    """Cosmetic / soft compliance gap."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"blocking"``)."""
        return self.value


@dataclass(frozen=True, slots=True)
class Decision:
    """Outcome of a single compliance rule check against a manuscript.

    Attributes:
        rule_id: Stable rule identifier, e.g. ``"hard.length"``. Used
            as the key in audit trails and machine-readable reports.
        rule_name: Human-readable rule name shown to authors.
        status: One of the four canonical :class:`DecisionStatus`
            outcomes.
        severity: How serious a ``FAIL`` is. Ignored when
            ``status`` is not :attr:`DecisionStatus.FAIL`.
        evidence: Free-text excerpt explaining the outcome (e.g. the
            offending sentence, the missing section).
        expected: Machine-readable expected value (e.g. ``"≤ 300"``).
        actual: Machine-readable actual value (e.g. ``"600"``).
    """

    rule_id: str
    rule_name: str
    status: DecisionStatus
    severity: Severity = Severity.MINOR
    evidence: str = ""
    expected: str = ""
    actual: str = ""

    def __post_init__(self) -> None:
        """Reject empty rule identifiers — they break audit lookups."""
        if not self.rule_id:
            raise ValueError("Decision.rule_id must be a non-empty string")
        if not self.rule_name:
            raise ValueError("Decision.rule_name must be a non-empty string")

    @property
    def passed(self) -> bool:
        """``True`` when the rule check produced :attr:`DecisionStatus.PASS`."""
        return self.status is DecisionStatus.PASS

    @property
    def is_blocking(self) -> bool:
        """``True`` when this decision is a blocking failure.

        A decision is blocking only when *both* the status is
        :attr:`DecisionStatus.FAIL` and the severity is
        :attr:`Severity.BLOCKING`. Passing rules are never blocking,
        even if their severity is ``BLOCKING``.
        """
        return self.status is DecisionStatus.FAIL and self.severity is Severity.BLOCKING


_DD_ID_RE = re.compile(r"^DD-\d+$")


@dataclass(frozen=True, slots=True)
class DesignDecision:
    """Pointer to a recorded Architecture Decision (ADR).

    Mirrors the entries kept in ``dev-docs/DECISIONS.xml`` (e.g.
    DD-13 — *"Renderer HTML canônico vs alternativo"*). Compliance
    engine outputs cite these to justify rule choices, so the value
    object encodes the same metadata the markdown table holds.

    Attributes:
        id: Canonical identifier, must match ``DD-<digits>``.
        title: Short decision title.
        version: Project version where the decision was first
            recorded (e.g. ``"2.22.0"``).
        rationale: Single-paragraph rationale text.
        supersedes: Tuple of DD ids this decision replaces.
        superseded_by: Optional later DD id that replaces this one.
    """

    id: str
    title: str
    version: str
    rationale: str
    supersedes: tuple[str, ...] = field(default_factory=tuple)
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        """Pin the canonical ``DD-<digits>`` shape — audit trails depend on it."""
        if not _DD_ID_RE.match(self.id):
            raise ValueError(f"DesignDecision.id must match 'DD-<digits>'; got {self.id!r}")
        if not self.title:
            raise ValueError("DesignDecision.title must be a non-empty string")
        if not self.version:
            raise ValueError("DesignDecision.version must be a non-empty string")
        if not self.rationale:
            raise ValueError("DesignDecision.rationale must be a non-empty string")
