"""Unit tests for :class:`UnpaywallResolver`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.error import HTTPError

import pytest

from ignorantia.infrastructure.search.http.unpaywall import UnpaywallResolver


class _FakeHttpClient:
    def __init__(self, *outcomes: object) -> None:
        self._outcomes: Iterator[object] = iter(outcomes)
        self.urls: list[str] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        del headers
        self.urls.append(url)
        try:
            outcome = next(self._outcomes)
        except StopIteration:
            return b"{}"
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, bytes):
            return outcome
        raise RuntimeError(f"unexpected outcome: {outcome!r}")


def _payload(
    *,
    is_oa: bool = True,
    oa_status: str = "gold",
    best_url: str = "https://repo.example.org/x",
    best_pdf: str = "https://repo.example.org/x.pdf",
    host_type: str = "repository",
    license_id: str = "cc-by",
    version: str = "publishedVersion",
) -> bytes:
    body = {
        "is_oa": is_oa,
        "oa_status": oa_status,
        "best_oa_location": {
            "url": best_url,
            "url_for_pdf": best_pdf,
            "host_type": host_type,
            "license": license_id,
            "version": version,
        }
        if is_oa
        else None,
    }
    return json.dumps(body).encode("utf-8")


class TestConstruction:
    def test_email_required(self) -> None:
        with pytest.raises(ValueError, match="email"):
            UnpaywallResolver(_FakeHttpClient(), email="")

    def test_source_id_is_unpaywall(self) -> None:
        resolver = UnpaywallResolver(_FakeHttpClient(), email="contact@example.org")
        assert resolver.source_id == "unpaywall"


class TestResolve:
    def test_oa_record_returns_populated_location(self) -> None:
        body = _payload(
            best_url="https://repo.example.org/A",
            best_pdf="https://repo.example.org/A.pdf",
            license_id="cc-by",
            oa_status="gold",
        )
        resolver = UnpaywallResolver(_FakeHttpClient(body), email="x@y.org")
        location = resolver.resolve("10.1234/x")
        assert location is not None
        assert location.url == "https://repo.example.org/A"
        assert location.url_for_pdf == "https://repo.example.org/A.pdf"
        assert location.license == "cc-by"
        assert location.oa_status == "gold"
        assert location.resolver == "unpaywall"

    def test_closed_record_returns_none(self) -> None:
        body = json.dumps({"is_oa": False, "best_oa_location": None}).encode("utf-8")
        resolver = UnpaywallResolver(_FakeHttpClient(body), email="x@y.org")
        assert resolver.resolve("10.1234/x") is None

    def test_404_returns_none(self) -> None:
        err = HTTPError("u", 404, "not found", hdrs=None, fp=None)  # type: ignore[arg-type]
        resolver = UnpaywallResolver(_FakeHttpClient(err), email="x@y.org")
        assert resolver.resolve("10.1234/x") is None

    def test_other_http_errors_propagate(self) -> None:
        err = HTTPError("u", 500, "server error", hdrs=None, fp=None)  # type: ignore[arg-type]
        resolver = UnpaywallResolver(_FakeHttpClient(err), email="x@y.org")
        with pytest.raises(HTTPError):
            resolver.resolve("10.1234/x")

    def test_url_strips_doi_prefix_when_present(self) -> None:
        client = _FakeHttpClient(_payload())
        resolver = UnpaywallResolver(client, email="x@y.org")
        resolver.resolve("https://doi.org/10.1234/x")
        assert "10.1234/x" in client.urls[0]
        assert "https://doi.org/" not in client.urls[0].split("?", 1)[0].split("/v2/")[1]

    def test_email_appears_as_query_param(self) -> None:
        client = _FakeHttpClient(_payload())
        resolver = UnpaywallResolver(client, email="contact@example.org")
        resolver.resolve("10.1234/x")
        assert "email=contact%40example.org" in client.urls[0]

    def test_invalid_doi_format_raises(self) -> None:
        resolver = UnpaywallResolver(_FakeHttpClient(), email="x@y.org")
        with pytest.raises(ValueError, match="doi"):
            resolver.resolve("not-a-doi")
