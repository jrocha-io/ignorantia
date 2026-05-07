"""F3 closeout smoke: ``SearchOrchestrator`` over 5+ adapters in parallel.

This is the integration smoke test required by issue #4 acceptance
criteria for Phase 3. It wires the *real* :class:`HttpClient`, the
*real* :class:`AdapterFactory`, and the *real* :class:`SearchOrchestrator`
together — only the ``urlopen`` opener is faked so the test is
hermetic.

The point is not to validate adapter parsing (that is what the unit
tests and the property-based contract test do); the point is to prove
the wiring composes correctly when more than one adapter runs through
the same orchestrator with a single shared HTTP client.

Sources covered: ``openalex``, ``doaj``, ``europepmc``, ``crossref``,
``arxiv``, ``zenodo`` — six free Open Access sources spanning JSON,
Solr-style and Atom XML response shapes.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.services.search_orchestrator import SearchOrchestrator
from ignorantia.domain.search.value_objects import Method
from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.search.adapter_factory import AdapterFactory

_EMPTY_BY_HOST: dict[str, bytes] = {
    "api.openalex.org": b'{"results": [], "meta": {"count": 0}}',
    "doaj.org": b'{"results": []}',
    "europepmc.org": b'{"resultList": {"result": []}, "hitCount": 0}',
    "api.crossref.org": b'{"message": {"items": []}}',
    "export.arxiv.org": b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>',
    "zenodo.org": b'{"hits": {"hits": [], "total": 0}}',
}


class _FakeResponse:
    """Minimal context-managed response wrapping a canned payload."""

    def __init__(self, body: bytes) -> None:
        self._stream = BytesIO(body)

    def read(self) -> bytes:
        return self._stream.read()

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self._stream.close()


def _opener_dispatcher(request: Any, timeout: float) -> _FakeResponse:
    del timeout
    url: str = request.full_url
    for host, body in _EMPTY_BY_HOST.items():
        if host in url:
            return _FakeResponse(body)
    return _FakeResponse(b"{}")


_SOURCES: tuple[str, ...] = (
    "openalex",
    "doaj",
    "europepmc",
    "crossref",
    "arxiv",
    "zenodo",
)


def test_orchestrator_runs_six_adapters_through_real_factory() -> None:
    http = HttpClient(user_agent="ignorantia-smoke/3.0", opener=_opener_dispatcher)
    orchestrator = SearchOrchestrator(AdapterFactory(http))

    results = orchestrator.run(SearchQuery(text="systematic review"), _SOURCES)

    assert set(results) == set(_SOURCES)
    for sid in _SOURCES:
        result = results[sid]
        assert result.source == sid
        assert result.method is Method.REAL
        assert result.items == ()


def test_orchestrator_deduplicated_items_is_empty_when_all_sources_return_empty() -> None:
    http = HttpClient(user_agent="ignorantia-smoke/3.0", opener=_opener_dispatcher)
    orchestrator = SearchOrchestrator(AdapterFactory(http))

    results = orchestrator.run(SearchQuery(text="systematic review"), _SOURCES)

    assert orchestrator.deduplicated_items(results) == ()
