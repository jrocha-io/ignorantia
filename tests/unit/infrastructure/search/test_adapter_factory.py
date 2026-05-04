"""Unit tests for :class:`AdapterFactory`.

The factory is the seam between the orchestrator (domain) and the
concrete adapters (infrastructure). For F2 it knows only the arxiv
adapter; F3 will register the remaining 61 sources.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.search.adapter_factory import AdapterFactory
from ignorantia.infrastructure.search.http.arxiv import ArxivAdapter


def _client() -> HttpClient:
    return HttpClient(user_agent="ignorantia-test/1.0", opener=lambda *_a, **_k: None)  # type: ignore[arg-type]


class TestFactoryShape:
    def test_implements_adapter_factory_port(self) -> None:
        assert isinstance(AdapterFactory(_client()), AdapterFactoryPort)


class TestKnownAdapters:
    def test_creates_arxiv_adapter(self) -> None:
        adapter = AdapterFactory(_client()).create("arxiv")
        assert isinstance(adapter, ArxivAdapter)

    def test_arxiv_adapter_is_wired_with_provided_client(self) -> None:
        client = _client()
        adapter = AdapterFactory(client).create("arxiv")
        assert isinstance(adapter, ArxivAdapter)
        assert adapter._http is client


class TestUnknownAdapters:
    def test_unknown_source_id_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="unknown_source"):
            AdapterFactory(_client()).create("unknown_source")

    def test_known_sources_lists_registered_adapters(self) -> None:
        assert "arxiv" in AdapterFactory(_client()).known_sources()
