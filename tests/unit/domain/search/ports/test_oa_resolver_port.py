"""Unit tests for ``OaResolverPort`` — tier-0 OA resolver contract."""

from __future__ import annotations

import pytest

from ignorantia.domain.search.entities import OaLocation
from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort


class _CompleteResolver(OaResolverPort):
    source_id = "stub"

    def resolve(self, doi: str) -> OaLocation | None:
        if doi == "found":
            return OaLocation(url="https://example.org/x", resolver=self.source_id)
        return None


class _NoSourceId(OaResolverPort):
    def resolve(self, doi: str) -> OaLocation | None:
        return None


class _NoResolve(OaResolverPort):
    source_id = "stub"


class TestOaResolverPortIsAbstract:
    def test_cannot_instantiate_base_class(self) -> None:
        with pytest.raises(TypeError):
            OaResolverPort()  # type: ignore[abstract]

    def test_cannot_instantiate_subclass_missing_source_id(self) -> None:
        with pytest.raises(TypeError):
            _NoSourceId()  # type: ignore[abstract]

    def test_cannot_instantiate_subclass_missing_resolve(self) -> None:
        with pytest.raises(TypeError):
            _NoResolve()  # type: ignore[abstract]

    def test_complete_subclass_can_be_instantiated(self) -> None:
        resolver = _CompleteResolver()
        assert isinstance(resolver, OaResolverPort)
        assert resolver.source_id == "stub"


class TestResolveContract:
    def test_known_doi_returns_oa_location(self) -> None:
        location = _CompleteResolver().resolve("found")
        assert isinstance(location, OaLocation)
        assert location.url == "https://example.org/x"

    def test_unknown_doi_returns_none(self) -> None:
        assert _CompleteResolver().resolve("not-found") is None
