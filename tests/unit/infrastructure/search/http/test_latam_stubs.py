"""Identity + behaviour tests for the 7 LATAM stub adapters.

Each class only sets ``source_id`` and ``source_tier`` on top of
:class:`_NoApiAdapter`. The base's behaviour (REAL_ERROR + empty
items, no HTTP call) is covered by ``test_no_api_adapter.py``; here
we just pin down each adapter's identity so renames or accidental
inheritance changes surface immediately.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.dabi import DabiAdapter
from ignorantia.infrastructure.search.http.dialnet import DialnetAdapter
from ignorantia.infrastructure.search.http.lilacs import LilacsAdapter
from ignorantia.infrastructure.search.http.pepsic import PepsicAdapter
from ignorantia.infrastructure.search.http.periodicos_capes import (
    PeriodicosCapesAdapter,
)
from ignorantia.infrastructure.search.http.redalyc import RedalycAdapter
from ignorantia.infrastructure.search.http.spell import SpellAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called")

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("HTTP must not be called")


_CASES: tuple[tuple[type[AdapterPort], str, Tier], ...] = (
    (LilacsAdapter, "lilacs", Tier.TIER1),
    (PepsicAdapter, "pepsic", Tier.TIER1),
    (RedalycAdapter, "redalyc", Tier.TIER1),
    (DialnetAdapter, "dialnet", Tier.TIER1),
    (DabiAdapter, "dabi", Tier.TIER1),
    (SpellAdapter, "spell", Tier.TIER1),
    (PeriodicosCapesAdapter, "periodicos_capes", Tier.TIER1),
)


@pytest.mark.parametrize(("adapter_cls", "source_id", "tier"), _CASES)
def test_source_id(adapter_cls: type[AdapterPort], source_id: str, tier: Tier) -> None:
    del tier
    assert adapter_cls(_NoopHttp()).source_id == source_id


@pytest.mark.parametrize(("adapter_cls", "source_id", "tier"), _CASES)
def test_source_tier(adapter_cls: type[AdapterPort], source_id: str, tier: Tier) -> None:
    del source_id
    assert adapter_cls(_NoopHttp()).source_tier is tier


@pytest.mark.parametrize(("adapter_cls", "source_id", "tier"), _CASES)
def test_fetch_returns_real_error_empty(
    adapter_cls: type[AdapterPort], source_id: str, tier: Tier
) -> None:
    del source_id, tier
    result = adapter_cls(_NoopHttp()).fetch(SearchQuery(text="x"))
    assert result.method is Method.REAL_ERROR
    assert result.items == ()
