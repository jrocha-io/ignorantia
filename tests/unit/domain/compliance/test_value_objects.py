"""Unit tests for compliance value objects.

Two value objects pinned by these tests:

* :class:`Decision` — the outcome of a single compliance rule check
  against a manuscript. Replaces v2's ``CheckResult`` with a typed,
  immutable shape and an explicit ``DecisionStatus`` enum.
* :class:`DesignDecision` — a pointer to a recorded Architecture
  Decision (DECISIONS.md DD-1 … DD-13). The compliance engine cites
  these to justify rule choices.

Both are frozen dataclasses with ``slots=True`` (search-context
convention). Equality is by value; hashing works.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.compliance.value_objects import (
    Decision,
    DecisionStatus,
    DesignDecision,
    Severity,
)


class TestDecisionStatus:
    def test_canonical_wire_values(self) -> None:
        assert DecisionStatus.PASS.value == "pass"
        assert DecisionStatus.FAIL.value == "fail"
        assert DecisionStatus.NEEDS_REVIEW.value == "needs_review"
        assert DecisionStatus.NOT_APPLICABLE.value == "not_applicable"

    def test_str_returns_wire_value(self) -> None:
        assert str(DecisionStatus.PASS) == "pass"

    def test_is_str_subtype(self) -> None:
        assert isinstance(DecisionStatus.FAIL, str)


class TestSeverity:
    def test_canonical_wire_values(self) -> None:
        assert Severity.BLOCKING.value == "blocking"
        assert Severity.MAJOR.value == "major"
        assert Severity.MINOR.value == "minor"

    def test_str_returns_wire_value(self) -> None:
        assert str(Severity.BLOCKING) == "blocking"

    def test_is_str_subtype(self) -> None:
        assert isinstance(Severity.MAJOR, str)


class TestDecisionConstruction:
    def test_minimum_required_fields(self) -> None:
        d = Decision(
            rule_id="hard.length",
            rule_name="Length",
            status=DecisionStatus.PASS,
        )
        assert d.rule_id == "hard.length"
        assert d.status is DecisionStatus.PASS
        # Default severity is MINOR — non-blocking unless caller upgrades.
        assert d.severity is Severity.MINOR
        assert d.evidence == ""

    def test_full_construction_with_all_fields(self) -> None:
        d = Decision(
            rule_id="hard.abstract",
            rule_name="Abstract length",
            status=DecisionStatus.FAIL,
            severity=Severity.MAJOR,
            evidence="Abstract has 600 words",
            expected="≤ 300",
            actual="600",
        )
        assert d.severity is Severity.MAJOR
        assert d.evidence == "Abstract has 600 words"
        assert d.expected == "≤ 300"
        assert d.actual == "600"


class TestDecisionInvariants:
    def test_rule_id_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="rule_id"):
            Decision(rule_id="", rule_name="x", status=DecisionStatus.PASS)

    def test_rule_name_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="rule_name"):
            Decision(rule_id="x", rule_name="", status=DecisionStatus.PASS)


class TestDecisionImmutability:
    def test_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        d = Decision(rule_id="x", rule_name="X", status=DecisionStatus.PASS)
        with pytest.raises(FrozenInstanceError):
            d.rule_id = "y"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        # frozen=True intercepts setattr first, so probe the slots
        # contract directly instead of via assignment.
        assert Decision.__slots__  # truthy = non-empty tuple
        d = Decision(rule_id="x", rule_name="X", status=DecisionStatus.PASS)
        assert not hasattr(d, "__dict__")

    def test_equal_by_value(self) -> None:
        a = Decision(rule_id="x", rule_name="X", status=DecisionStatus.PASS)
        b = Decision(rule_id="x", rule_name="X", status=DecisionStatus.PASS)
        assert a == b
        assert hash(a) == hash(b)

    def test_inequal_when_status_differs(self) -> None:
        a = Decision(rule_id="x", rule_name="X", status=DecisionStatus.PASS)
        b = Decision(rule_id="x", rule_name="X", status=DecisionStatus.FAIL)
        assert a != b


class TestDecisionConvenienceFlags:
    def test_passed_returns_true_only_for_pass(self) -> None:
        for status in DecisionStatus:
            d = Decision(rule_id="x", rule_name="X", status=status)
            assert d.passed is (status is DecisionStatus.PASS)

    def test_blocking_when_severity_is_blocking_and_failed(self) -> None:
        d = Decision(
            rule_id="x",
            rule_name="X",
            status=DecisionStatus.FAIL,
            severity=Severity.BLOCKING,
        )
        assert d.is_blocking is True

    def test_not_blocking_when_passed_even_with_blocking_severity(self) -> None:
        d = Decision(
            rule_id="x",
            rule_name="X",
            status=DecisionStatus.PASS,
            severity=Severity.BLOCKING,
        )
        assert d.is_blocking is False

    def test_not_blocking_when_severity_below_blocking(self) -> None:
        d = Decision(
            rule_id="x",
            rule_name="X",
            status=DecisionStatus.FAIL,
            severity=Severity.MAJOR,
        )
        assert d.is_blocking is False


class TestDesignDecisionConstruction:
    def test_minimum_required_fields(self) -> None:
        dd = DesignDecision(
            id="DD-13",
            title="Renderer HTML canônico vs alternativo",
            version="2.22.0",
            rationale="render_chunks.py é canônico; render_v2.py é alternativo standalone.",
        )
        assert dd.id == "DD-13"
        assert dd.title.startswith("Renderer")
        assert dd.version == "2.22.0"
        assert dd.rationale.startswith("render_chunks")
        assert dd.supersedes == ()
        assert dd.superseded_by is None

    def test_with_supersedes_chain(self) -> None:
        dd = DesignDecision(
            id="DD-7",
            title="A revised decision",
            version="2.11.1",
            rationale="Refines DD-5.",
            supersedes=("DD-5",),
            superseded_by=None,
        )
        assert dd.supersedes == ("DD-5",)


class TestDesignDecisionInvariants:
    def test_id_must_match_dd_pattern(self) -> None:
        with pytest.raises(ValueError, match="DD-"):
            DesignDecision(id="X-1", title="t", version="v", rationale="r")

    def test_id_dd_dash_required(self) -> None:
        with pytest.raises(ValueError, match="DD-"):
            DesignDecision(id="DD13", title="t", version="v", rationale="r")

    def test_title_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="title"):
            DesignDecision(id="DD-1", title="", version="v", rationale="r")

    def test_rationale_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="rationale"):
            DesignDecision(id="DD-1", title="t", version="v", rationale="")

    def test_version_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="version"):
            DesignDecision(id="DD-1", title="t", version="", rationale="r")


class TestDesignDecisionImmutability:
    def test_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        dd = DesignDecision(id="DD-1", title="t", version="v", rationale="r")
        with pytest.raises(FrozenInstanceError):
            dd.id = "DD-2"  # type: ignore[misc]

    def test_equal_by_value(self) -> None:
        a = DesignDecision(id="DD-1", title="t", version="v", rationale="r")
        b = DesignDecision(id="DD-1", title="t", version="v", rationale="r")
        assert a == b
        assert hash(a) == hash(b)
