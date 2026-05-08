"""``OaButtonResolver`` — tier-0 OA resolver via the OA.Works ``find`` API.

Migrated from v2 ``search_oa_button.py``. The OA Button API is best-effort
(its uptime has historically been spotty); the resolver simply returns
``None`` whenever the API cannot locate an OA copy or replies 404.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.error import HTTPError
from urllib.parse import urlencode

from ignorantia.domain.search.entities import OaLocation
from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort
from ignorantia.infrastructure.http_client import HttpClient


class OaButtonResolver(OaResolverPort):
    """Adapter for OA.Works's ``api.openaccessbutton.org/find`` endpoint."""

    source_id = "oa_button"

    _API_URL: ClassVar[str] = "https://api.openaccessbutton.org/find"

    def __init__(self, http: HttpClient) -> None:
        """Wire the resolver to the shared HTTP client."""
        self._http = http

    def resolve(self, doi: str) -> OaLocation | None:
        """Look up ``doi`` and return an OA location if available."""
        bare = _strip_doi_url_prefix(doi).strip()
        if "/" not in bare or not bare.startswith("10."):
            raise ValueError(f"Invalid doi format: {doi!r}")
        url = f"{self._API_URL}?{urlencode({'id': bare})}"
        try:
            body = self._http.get(url)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise
        return _parse(body, self.source_id)


def _strip_doi_url_prefix(value: str) -> str:
    for prefix in ("https://doi.org/", "http://doi.org/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _parse(body: bytes, resolver_id: str) -> OaLocation | None:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    oa_url = _str_or_none(payload.get("url")) or _str_or_none(_nested_url(payload))
    if not oa_url:
        return None
    return OaLocation(url=oa_url, url_for_pdf=oa_url, resolver=resolver_id)


def _nested_url(payload: dict[str, Any]) -> object:
    data = payload.get("data")
    if isinstance(data, dict):
        return data.get("url")
    return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
