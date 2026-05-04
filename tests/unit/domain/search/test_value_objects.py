"""Unit tests for the search bounded context value objects.

These tests pin the canonical wire format of ``Tier`` and ``Method`` so the
v2 → v3 transition does not silently break the 62 search adapters or
downstream consumers (orchestration_summary.json, search_result.json).
"""

from __future__ import annotations

import json

import pytest

from ignorantia.domain.search.value_objects import Method, Tier


class TestTierCanonicalValues:
    """Pin the wire format that v2.23.0 already exposes (audit #5, fix E1)."""

    def test_tier0_is_canonical_string(self) -> None:
        assert Tier.TIER0.value == "tier0"

    def test_tier1_is_canonical_string(self) -> None:
        assert Tier.TIER1.value == "tier1"

    def test_tier2_is_canonical_string(self) -> None:
        assert Tier.TIER2.value == "tier2"

    def test_tier3_is_canonical_string(self) -> None:
        assert Tier.TIER3.value == "tier3"

    def test_only_four_canonical_tiers(self) -> None:
        assert {t.value for t in Tier} == {"tier0", "tier1", "tier2", "tier3"}


class TestTierStringBehaviour:
    """``Tier`` must be a ``str`` so JSON serialization is transparent."""

    def test_tier_is_str_subclass(self) -> None:
        assert isinstance(Tier.TIER1, str)

    def test_str_returns_canonical_value(self) -> None:
        assert str(Tier.TIER1) == "tier1"

    def test_json_dumps_round_trip(self) -> None:
        encoded = json.dumps({"source_tier": Tier.TIER2})
        assert json.loads(encoded) == {"source_tier": "tier2"}


class TestTierConstruction:
    """Construction from external strings (e.g. JSON payloads)."""

    @pytest.mark.parametrize("value", ["tier0", "tier1", "tier2", "tier3"])
    def test_construct_from_canonical_string(self, value: str) -> None:
        assert Tier(value).value == value

    @pytest.mark.parametrize("invalid", ["TIER1", "tier4", "premium", "", "1"])
    def test_rejects_non_canonical_strings(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            Tier(invalid)


class TestMethodCanonicalValues:
    """Pin the wire format introduced as ``AdapterMethod`` enum in v2.23.0 (E6)."""

    def test_canonical_values(self) -> None:
        assert {m.value for m in Method} == {
            "mock",
            "real",
            "real_partial",
            "real_error",
        }

    def test_method_is_str_subclass(self) -> None:
        assert isinstance(Method.REAL, str)

    @pytest.mark.parametrize("value", ["mock", "real", "real_partial", "real_error"])
    def test_construct_from_canonical_string(self, value: str) -> None:
        assert Method(value).value == value

    @pytest.mark.parametrize("invalid", ["MOCK", "Real", "fake", ""])
    def test_rejects_non_canonical_strings(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            Method(invalid)
