"""``HttpClient`` — the *single* egress point for every search adapter.

In v2.x there were ~62 sites of ``urllib.request.urlopen`` scattered
across adapters, each with its own (often missing) headers, timeout and
retry handling. v3 consolidates them into this client so cross-cutting
concerns (rate limiting, polite-pool User-Agent, exponential back-off)
are implemented exactly once.

The client is stdlib-only — no third-party HTTP library is pulled in.
Time-dependent behaviour (throttle, retry sleep) is parametrised so
tests can run deterministically.
"""

from __future__ import annotations

import time
import urllib.request
from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError, URLError

_RETRYABLE_HTTP_STATUSES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})


class _Response(Protocol):
    """Minimal context-managed response shape used by :class:`HttpClient`."""

    def read(self) -> bytes:
        """Return the response body."""

    def __enter__(self) -> _Response:
        """Return ``self`` so ``with opener(...) as r`` works."""

    def __exit__(self, *exc: object) -> None:
        """Close the underlying connection."""


@runtime_checkable
class _OpenerLike(Protocol):
    """The minimal subset of :func:`urllib.request.urlopen` we depend on."""

    def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
        """Open ``request`` and return a context-managed response."""


class HttpClient:
    """Centralised HTTP client used by every search adapter.

    Args:
        user_agent: The mandatory User-Agent string. Adapters cannot
            override it from a request to prevent accidental impersonation.
        timeout_s: Per-request timeout in seconds.
        throttle_s: Minimum time between two consecutive requests on this
            client. ``0`` disables throttling.
        max_retries: How many times to retry on transient failures
            (5xx HTTP statuses, 429, network errors).
        opener: The function used to perform the underlying HTTP call.
            Tests inject a fake; production uses
            :func:`urllib.request.urlopen`.
        clock: Monotonic clock used to schedule throttle waits. Defaults
            to :func:`time.monotonic`.
        sleep: Sleep function used for throttle and retry back-off.
            Defaults to :func:`time.sleep`.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_s: float = 30.0,
        throttle_s: float = 0.0,
        max_retries: int = 3,
        opener: _OpenerLike | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Build the client; see class docstring for argument semantics."""
        if not user_agent:
            raise ValueError("user_agent must be a non-empty string")
        self._user_agent = user_agent
        self._timeout_s = timeout_s
        self._throttle_s = throttle_s
        self._max_retries = max_retries
        self._opener: _OpenerLike = opener or _default_opener
        self._clock: Callable[[], float] = clock or time.monotonic
        self._sleep: Callable[[float], None] = sleep or time.sleep
        self._last_request_at: float | None = None

    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes:
        """GET ``url`` and return the response body as bytes.

        Args:
            url: Absolute ``http://`` or ``https://`` URL.
            headers: Optional headers to merge with ``User-Agent``. The
                client always wins on ``User-Agent`` to prevent override.

        Raises:
            ValueError: if ``url`` is empty or uses a non-HTTP scheme.
            urllib.error.HTTPError: on a non-retryable HTTP error or
                after retries are exhausted.
            urllib.error.URLError: when network errors persist after
                retries.
        """
        _validate_http_url(url)
        request = self._build_request(url, headers)
        self._wait_for_throttle()
        return self._do_with_retry(request)

    def _build_request(self, url: str, headers: Mapping[str, str] | None) -> urllib.request.Request:
        merged: dict[str, str] = dict(headers or {})
        merged["User-Agent"] = self._user_agent
        # Scheme is validated by ``_validate_http_url`` upstream of every
        # caller, so ``Request`` only ever sees ``http(s)://`` URLs.
        return urllib.request.Request(url, headers=merged)  # noqa: S310

    def _wait_for_throttle(self) -> None:
        if self._throttle_s <= 0 or self._last_request_at is None:
            return
        elapsed = self._clock() - self._last_request_at
        remaining = self._throttle_s - elapsed
        if remaining > 0:
            self._sleep(remaining)

    def _do_with_retry(self, request: urllib.request.Request) -> bytes:
        last_error: BaseException | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with self._opener(request, timeout=self._timeout_s) as response:
                    body = response.read()
                self._last_request_at = self._clock()
                return body
            except HTTPError as exc:
                if exc.code not in _RETRYABLE_HTTP_STATUSES:
                    raise
                last_error = exc
            except URLError as exc:
                last_error = exc
            if attempt < self._max_retries:
                self._sleep(_backoff_seconds(attempt))
        if last_error is None:
            raise RuntimeError("retry loop exited without success or error")
        raise last_error


def _backoff_seconds(attempt: int) -> float:
    """Return exponential back-off in seconds for a zero-indexed attempt."""
    return float(2**attempt)


def _validate_http_url(url: str) -> None:
    if not url:
        raise ValueError("url must be a non-empty string")
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"url must use http or https scheme: {url!r}")


def _default_opener(
    request: urllib.request.Request, timeout: float
) -> _Response:  # pragma: no cover — exercised by integration code
    response: _Response = urllib.request.urlopen(request, timeout=timeout)  # noqa: S310
    return response
