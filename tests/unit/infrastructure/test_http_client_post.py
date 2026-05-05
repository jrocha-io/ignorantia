"""Unit tests for :meth:`HttpClient.post`.

POST is structurally identical to GET except for the request method and
the request body. The retry/throttle/User-Agent invariants tested in
``test_http_client.py`` are exercised again here for the POST path so
that any future refactor that breaks symmetry surfaces immediately.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from urllib.error import HTTPError, URLError

import pytest

from ignorantia.infrastructure.http_client import HttpClient


class _FakeResponse:
    def __init__(self, body: bytes = b"ok") -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Recorder:
    def __init__(self, *responses: object) -> None:
        self._scripted: list[object] = list(responses)
        self.calls: list[tuple[str, str, bytes | None, Mapping[str, str], float]] = []

    def __call__(self, request: object, timeout: float) -> _FakeResponse:
        from urllib.request import Request

        assert isinstance(request, Request)
        self.calls.append(
            (
                request.full_url,
                request.get_method(),
                request.data if isinstance(request.data, bytes) else None,
                dict(request.headers),
                timeout,
            )
        )
        outcome = self._scripted.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, _FakeResponse)
        return outcome


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _build(
    *responses: object,
    user_agent: str = "ignorantia-test/1.0",
    timeout_s: float = 30.0,
    throttle_s: float = 0.0,
    max_retries: int = 2,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
) -> tuple[HttpClient, _Recorder, list[float]]:
    rec = _Recorder(*responses)
    sleeps: list[float] = []
    return (
        HttpClient(
            user_agent=user_agent,
            timeout_s=timeout_s,
            throttle_s=throttle_s,
            max_retries=max_retries,
            opener=rec,
            clock=clock or _FakeClock(),
            sleep=sleep or sleeps.append,
        ),
        rec,
        sleeps,
    )


class TestRequestShape:
    def test_method_is_post(self) -> None:
        client, rec, _ = _build(_FakeResponse())
        client.post("https://example.org/x", data=b"{}")
        _, method, _, _, _ = rec.calls[0]
        assert method == "POST"

    def test_body_is_passed_through(self) -> None:
        client, rec, _ = _build(_FakeResponse())
        client.post("https://example.org/x", data=b'{"q":"test"}')
        _, _, body, _, _ = rec.calls[0]
        assert body == b'{"q":"test"}'

    def test_response_body_is_returned(self) -> None:
        client, _, _ = _build(_FakeResponse(b"hello"))
        assert client.post("https://example.org/x", data=b"{}") == b"hello"

    def test_caller_headers_are_merged(self) -> None:
        client, rec, _ = _build(_FakeResponse())
        client.post(
            "https://example.org/x",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        _, _, _, headers, _ = rec.calls[0]
        assert headers.get("Content-type") == "application/json"

    def test_user_agent_is_set(self) -> None:
        client, rec, _ = _build(_FakeResponse(), user_agent="ignorantia-test/1.0")
        client.post("https://example.org/x", data=b"{}")
        _, _, _, headers, _ = rec.calls[0]
        assert headers.get("User-agent") == "ignorantia-test/1.0"

    def test_caller_cannot_override_user_agent(self) -> None:
        client, rec, _ = _build(_FakeResponse(), user_agent="ignorantia-test/1.0")
        client.post(
            "https://example.org/x",
            data=b"{}",
            headers={"User-Agent": "evil-bot/9000"},
        )
        _, _, _, headers, _ = rec.calls[0]
        assert headers.get("User-agent") == "ignorantia-test/1.0"

    def test_timeout_is_passed_to_opener(self) -> None:
        client, rec, _ = _build(_FakeResponse(), timeout_s=15.0)
        client.post("https://example.org/x", data=b"{}")
        _, _, _, _, timeout = rec.calls[0]
        assert timeout == 15.0


class TestUrlValidation:
    def test_rejects_non_http_scheme(self) -> None:
        client, _, _ = _build(_FakeResponse())
        with pytest.raises(ValueError, match="http"):
            client.post("file:///etc/passwd", data=b"{}")

    def test_rejects_empty_url(self) -> None:
        client, _, _ = _build(_FakeResponse())
        with pytest.raises(ValueError):
            client.post("", data=b"{}")


class TestRetryOnTransientErrors:
    def _http_error(self, status: int) -> HTTPError:
        return HTTPError("https://x/", status, "boom", hdrs=None, fp=None)  # type: ignore[arg-type]

    def test_5xx_triggers_retry_then_succeeds(self) -> None:
        client, rec, sleeps = _build(self._http_error(503), _FakeResponse(b"ok"), max_retries=2)
        body = client.post("https://example.org/x", data=b"{}")
        assert body == b"ok"
        assert len(rec.calls) == 2
        assert sleeps == [1.0]

    def test_429_triggers_retry(self) -> None:
        client, rec, _ = _build(self._http_error(429), _FakeResponse(b"ok"), max_retries=2)
        client.post("https://example.org/x", data=b"{}")
        assert len(rec.calls) == 2

    def test_404_does_not_retry(self) -> None:
        err = self._http_error(404)
        client, rec, _ = _build(err, max_retries=3)
        with pytest.raises(HTTPError):
            client.post("https://example.org/x", data=b"{}")
        assert len(rec.calls) == 1

    def test_url_error_triggers_retry(self) -> None:
        client, rec, _ = _build(URLError("dns failed"), _FakeResponse(b"ok"), max_retries=2)
        client.post("https://example.org/x", data=b"{}")
        assert len(rec.calls) == 2


class TestThrottle:
    def test_post_respects_throttle_with_get(self) -> None:
        clock = _FakeClock(start=0.0)
        client, _, sleeps = _build(
            _FakeResponse(),
            _FakeResponse(),
            throttle_s=2.0,
            clock=clock,
        )
        client.get("https://example.org/a")
        clock.now = 0.5
        client.post("https://example.org/b", data=b"{}")
        assert sleeps == [pytest.approx(1.5)]
