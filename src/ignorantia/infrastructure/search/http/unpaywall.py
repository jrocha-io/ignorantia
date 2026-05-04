"""``UnpaywallResolver`` — tier-0 OA resolver via the Unpaywall API.

Unpaywall maps a DOI to the best legitimate OA copy known to OurResearch
(publisher OA, hybrid, green/repository, ...). The API is free but
requires an email for polite-pool identification.

Migrated from v2 ``search_unpaywall.py``; the v2 module imported
``requests``, which v3 replaces with the stdlib-only :class:`HttpClient`.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.error import HTTPError
from urllib.parse import urlencode

from ignorantia.domain.search.entities import OaLocation
from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort
from ignorantia.infrastructure.http_client import HttpClient


class UnpaywallResolver(OaResolverPort):
    """Adapter for Unpaywall's ``api.unpaywall.org/v2/{doi}`` endpoint."""

    source_id = "unpaywall"

    _API_BASE: ClassVar[str] = "https://api.unpaywall.org/v2"

    def __init__(self, http: HttpClient, *, email: str) -> None:
        """Wire the resolver and pin the polite-pool email."""
        if not email or "@" not in email:
            raise ValueError("email must include '@'; required by Unpaywall")
        self._http = http
        self._email = email

    def resolve(self, doi: str) -> OaLocation | None:
        """Look up ``doi`` and return its best OA location, if any."""
        bare = _strip_doi_url_prefix(doi).strip()
        if "/" not in bare or not bare.startswith("10."):
            raise ValueError(f"Invalid doi format: {doi!r}")
        url = f"{self._API_BASE}/{bare}?{urlencode({'email': self._email})}"
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
    if not payload.get("is_oa"):
        return None
    best = payload.get("best_oa_location")
    if not isinstance(best, dict):
        return None
    return OaLocation(
        url=_str_or_none(best.get("url")),
        url_for_pdf=_str_or_none(best.get("url_for_pdf")),
        host_type=_str_or_none(best.get("host_type")),
        license=_str_or_none(best.get("license")),
        version=_str_or_none(best.get("version")),
        oa_status=_str_or_none(payload.get("oa_status")),
        resolver=resolver_id,
    )


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
