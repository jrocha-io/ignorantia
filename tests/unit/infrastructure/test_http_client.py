"""Unit tests for the centralised :class:`HttpClient`.

The HttpClient is the single egress point for every adapter — replacing
the 62 sites of ``urllib.request.urlopen`` from v2. Tests use a fake
opener and a fake clock so behaviour is deterministic.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from urllib.error import HTTPError, URLError

import pytest

from ignorantia.infrastructure.http_client import HttpClient


class _FakeResponse:
    def __init__(self, body: bytes = b"ok", status: int = 200) -> None:
        self.body = body
        self.status = status

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Recorder:
    """Captures every opener invocation and serves a scripted sequence."""

    def __init__(self, *responses: object) -> None:
        self._scripted: list[object] = list(responses)
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def __call__(self, request: object, timeout: float) -> _FakeResponse:
        from urllib.request import Request

        assert isinstance(request, Request)
        self.calls.append((request.full_url, dict(request.headers), timeout))
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


class TestUrlValidation:
    def test_rejects_non_http_scheme(self) -> None:
        client, _, _ = _build(_FakeResponse())
        with pytest.raises(ValueError, match="http"):
            client.get("file:///etc/passwd")

    def test_rejects_empty_url(self) -> None:
        client, _, _ = _build(_FakeResponse())
        with pytest.raises(ValueError):
            client.get("")

    def test_accepts_https(self) -> None:
        client, _, _ = _build(_FakeResponse(b"hi"))
        assert client.get("https://example.org/x") == b"hi"

    def test_accepts_http(self) -> None:
        client, _, _ = _build(_FakeResponse(b"hi"))
        assert client.get("http://example.org/x") == b"hi"


class TestHeadersAndTimeout:
    def test_user_agent_header_is_sent(self) -> None:
        client, rec, _ = _build(_FakeResponse(), user_agent="ignorantia-test/1.0")
        client.get("https://example.org/x")
        _, headers, _ = rec.calls[0]
        assert headers.get("User-agent") == "ignorantia-test/1.0"

    def test_caller_headers_are_merged(self) -> None:
        client, rec, _ = _build(_FakeResponse())
        client.get("https://example.org/x", headers={"Accept": "application/xml"})
        _, headers, _ = rec.calls[0]
        assert headers.get("Accept") == "application/xml"

    def test_caller_cannot_override_user_agent(self) -> None:
        client, rec, _ = _build(_FakeResponse(), user_agent="ignorantia-test/1.0")
        client.get("https://example.org/x", headers={"User-Agent": "evil-bot/9000"})
        _, headers, _ = rec.calls[0]
        assert headers.get("User-agent") == "ignorantia-test/1.0"

    def test_timeout_is_passed_to_opener(self) -> None:
        client, rec, _ = _build(_FakeResponse(), timeout_s=12.0)
        client.get("https://example.org/x")
        _, _, timeout = rec.calls[0]
        assert timeout == 12.0


class TestRetryOnTransientErrors:
    def _http_error(self, status: int) -> HTTPError:
        from urllib.error import HTTPError

        return HTTPError("https://x/", status, "boom", hdrs=None, fp=None)  # type: ignore[arg-type]

    def test_5xx_triggers_retry_then_succeeds(self) -> None:
        client, rec, sleeps = _build(
            self._http_error(503),
            _FakeResponse(b"ok"),
            max_retries=2,
        )
        body = client.get("https://example.org/x")
        assert body == b"ok"
        assert len(rec.calls) == 2
        assert sleeps == [1.0]

    def test_429_triggers_retry(self) -> None:
        client, rec, _ = _build(
            self._http_error(429),
            _FakeResponse(b"ok"),
            max_retries=2,
        )
        client.get("https://example.org/x")
        assert len(rec.calls) == 2

    def test_404_does_not_retry(self) -> None:
        err = self._http_error(404)
        client, rec, _ = _build(err, max_retries=3)
        with pytest.raises(HTTPError):
            client.get("https://example.org/x")
        assert len(rec.calls) == 1

    def test_url_error_triggers_retry(self) -> None:
        client, rec, _ = _build(
            URLError("dns failed"),
            _FakeResponse(b"ok"),
            max_retries=2,
        )
        client.get("https://example.org/x")
        assert len(rec.calls) == 2

    def test_exhausting_retries_raises_last_error(self) -> None:
        err = self._http_error(503)
        client, rec, sleeps = _build(err, err, err, max_retries=2)
        with pytest.raises(HTTPError):
            client.get("https://example.org/x")
        assert len(rec.calls) == 3
        assert sleeps == [1.0, 2.0]


class TestThrottle:
    def test_first_request_does_not_sleep(self) -> None:
        client, _, sleeps = _build(_FakeResponse(), throttle_s=2.0)
        client.get("https://example.org/x")
        assert sleeps == []

    def test_second_request_waits_remaining_throttle(self) -> None:
        clock = _FakeClock(start=0.0)
        client, _, sleeps = _build(
            _FakeResponse(),
            _FakeResponse(),
            throttle_s=2.0,
            clock=clock,
        )
        client.get("https://example.org/a")
        clock.now = 0.5
        client.get("https://example.org/b")
        assert sleeps == [pytest.approx(1.5)]

    def test_no_sleep_when_throttle_already_elapsed(self) -> None:
        clock = _FakeClock(start=0.0)
        client, _, sleeps = _build(
            _FakeResponse(),
            _FakeResponse(),
            throttle_s=2.0,
            clock=clock,
        )
        client.get("https://example.org/a")
        clock.now = 5.0
        client.get("https://example.org/b")
        assert sleeps == []
