"""Unit tests for :class:`OaResolverFactory`."""

from __future__ import annotations

import pytest

from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.search.http.oa_button import OaButtonResolver
from ignorantia.infrastructure.search.http.unpaywall import UnpaywallResolver
from ignorantia.infrastructure.search.oa_resolver_factory import OaResolverFactory


def _http() -> HttpClient:
    return HttpClient(user_agent="ignorantia-test/1.0")


class TestOaButtonAlwaysAvailable:
    def test_creates_oa_button_resolver(self) -> None:
        factory = OaResolverFactory(_http())
        resolver = factory.create("oa_button")
        assert isinstance(resolver, OaButtonResolver)

    def test_oa_button_listed_in_known_sources(self) -> None:
        assert "oa_button" in OaResolverFactory(_http()).known_sources()


class TestUnpaywallRequiresEmail:
    def test_create_unpaywall_without_email_raises(self) -> None:
        factory = OaResolverFactory(_http())
        with pytest.raises(KeyError):
            factory.create("unpaywall")

    def test_create_unpaywall_with_email(self) -> None:
        factory = OaResolverFactory(_http(), unpaywall_email="alice@example.org")
        resolver = factory.create("unpaywall")
        assert isinstance(resolver, UnpaywallResolver)

    def test_unpaywall_in_known_sources_only_when_email_set(self) -> None:
        without = OaResolverFactory(_http()).known_sources()
        with_email = OaResolverFactory(_http(), unpaywall_email="x@y.z").known_sources()
        assert "unpaywall" not in without
        assert "unpaywall" in with_email


class TestUnknownResolver:
    def test_unknown_source_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="not registered"):
            OaResolverFactory(_http()).create("nonexistent")
