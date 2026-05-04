"""Unit tests for :class:`OaButtonResolver`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.error import HTTPError

import pytest

from ignorantia.infrastructure.search.http.oa_button import OaButtonResolver


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


class TestMetadata:
    def test_source_id(self) -> None:
        assert OaButtonResolver(_FakeHttpClient()).source_id == "oa_button"


class TestResolve:
    def test_oa_payload_with_top_level_url(self) -> None:
        body = json.dumps({"url": "https://example.org/x.pdf"}).encode("utf-8")
        location = OaButtonResolver(_FakeHttpClient(body)).resolve("10.1234/x")
        assert location is not None
        assert location.url == "https://example.org/x.pdf"
        assert location.resolver == "oa_button"

    def test_oa_payload_with_nested_data_url(self) -> None:
        body = json.dumps({"data": {"url": "https://example.org/y.pdf"}}).encode("utf-8")
        location = OaButtonResolver(_FakeHttpClient(body)).resolve("10.1234/x")
        assert location is not None
        assert location.url == "https://example.org/y.pdf"

    def test_no_url_in_payload_returns_none(self) -> None:
        body = json.dumps({"message": "request submitted"}).encode("utf-8")
        assert OaButtonResolver(_FakeHttpClient(body)).resolve("10.1234/x") is None

    def test_404_returns_none(self) -> None:
        err = HTTPError("u", 404, "not found", hdrs=None, fp=None)  # type: ignore[arg-type]
        assert OaButtonResolver(_FakeHttpClient(err)).resolve("10.1234/x") is None

    def test_500_propagates(self) -> None:
        err = HTTPError("u", 500, "boom", hdrs=None, fp=None)  # type: ignore[arg-type]
        with pytest.raises(HTTPError):
            OaButtonResolver(_FakeHttpClient(err)).resolve("10.1234/x")

    def test_doi_url_prefix_stripped(self) -> None:
        client = _FakeHttpClient(b"{}")
        OaButtonResolver(client).resolve("https://doi.org/10.1234/x")
        assert "id=10.1234%2Fx" in client.urls[0]

    def test_invalid_doi_format_raises(self) -> None:
        with pytest.raises(ValueError, match="doi"):
            OaButtonResolver(_FakeHttpClient()).resolve("not-a-doi")
