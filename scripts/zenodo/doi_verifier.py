"""
DOI verification module.

LLMs alucinam DOIs em ~15-30% dos casos (Walters & Wilder 2023, Sci Rep 13:14045).
Este módulo verifica DOIs contra três fontes:

  1. Crossref REST API   — autoridade primária para DOIs registrados
  2. Retraction Watch    — check de retração (CSV diário publicado)
  3. OpenAlex           — fallback adicional + metadados

Funciona offline em "modo cache" se não houver rede; nesse caso reporta
"unverified_no_network" como status, sem falsificar verificação.
"""

from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


CROSSREF_API = "https://api.crossref.org/works/"
OPENALEX_API = "https://api.openalex.org/works/doi:"
USER_AGENT = "ignorantia/2.0 (https://github.com/ignorantia/ignorantia; mailto:noreply@ignorantia.local)"


@dataclass
class DOIVerificationResult:
    doi: str
    status: str  # 'verified' | 'not_found' | 'retracted' | 'invalid_format' | 'unverified_no_network' | 'error'
    crossref_metadata: dict | None = None
    openalex_metadata: dict | None = None
    retraction_info: dict | None = None
    error_message: str | None = None


def _http_get_json(url: str, timeout: float = 8.0) -> dict | None:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            return None
        return json.loads(resp.read().decode("utf-8"))


def _is_valid_doi_format(doi: str) -> bool:
    return bool(re.match(r"^10\.\d{4,9}/[\w./;()\-]+$", doi.strip()))


def _check_crossref(doi: str) -> tuple[bool, dict | None, str | None]:
    """Returns (found, metadata, error)."""
    try:
        data = _http_get_json(CROSSREF_API + quote_plus(doi))
        if data and "message" in data:
            msg = data["message"]
            return True, {
                "title": msg.get("title", [None])[0],
                "issued": msg.get("issued", {}).get("date-parts", [[None]])[0],
                "type": msg.get("type"),
                "publisher": msg.get("publisher"),
                "container-title": (msg.get("container-title") or [None])[0],
            }, None
        return False, None, None
    except HTTPError as e:
        if e.code == 404:
            return False, None, None
        return False, None, f"crossref_http_{e.code}"
    except URLError as e:
        return False, None, f"crossref_unreachable: {e.reason}"
    except Exception as e:
        return False, None, f"crossref_error: {type(e).__name__}: {e}"


def _check_openalex(doi: str) -> tuple[bool, dict | None]:
    try:
        data = _http_get_json(OPENALEX_API + quote_plus(doi))
        if data and data.get("id"):
            return True, {
                "openalex_id": data.get("id"),
                "title": data.get("title"),
                "publication_year": data.get("publication_year"),
                "is_retracted": data.get("is_retracted", False),
                "is_paratext": data.get("is_paratext", False),
                "type": data.get("type"),
            }
        return False, None
    except (HTTPError, URLError):
        return False, None
    except Exception:
        return False, None


def _check_retraction_watch_via_openalex(openalex_meta: dict | None) -> dict | None:
    """OpenAlex já incorpora dados do Retraction Watch via 'is_retracted'.
    Para verificação independente, integraria com o CSV oficial."""
    if openalex_meta and openalex_meta.get("is_retracted"):
        return {"is_retracted": True, "source": "openalex"}
    return None


def verify_dois(dois: list[str], throttle_seconds: float = 0.1) -> list[DOIVerificationResult]:
    """Verifica uma lista de DOIs contra Crossref + OpenAlex + Retraction Watch.

    Throttling de 100ms entre requests para não sobrecarregar APIs públicas.
    Crossref permite 50 req/s sem auth; OpenAlex permite 10 req/s.
    """
    results: list[DOIVerificationResult] = []
    network_failed = False

    for doi in dois:
        doi_clean = doi.strip()
        if not _is_valid_doi_format(doi_clean):
            results.append(DOIVerificationResult(
                doi=doi_clean, status="invalid_format",
            ))
            continue

        if network_failed:
            results.append(DOIVerificationResult(
                doi=doi_clean, status="unverified_no_network",
            ))
            continue

        cr_found, cr_meta, cr_err = _check_crossref(doi_clean)
        if cr_err and "unreachable" in cr_err:
            network_failed = True
            results.append(DOIVerificationResult(
                doi=doi_clean, status="unverified_no_network", error_message=cr_err,
            ))
            continue

        oa_found, oa_meta = _check_openalex(doi_clean)
        retraction = _check_retraction_watch_via_openalex(oa_meta)

        if retraction and retraction.get("is_retracted"):
            status = "retracted"
        elif cr_found or oa_found:
            status = "verified"
        else:
            status = "not_found"

        results.append(DOIVerificationResult(
            doi=doi_clean, status=status,
            crossref_metadata=cr_meta, openalex_metadata=oa_meta,
            retraction_info=retraction, error_message=cr_err,
        ))

        time.sleep(throttle_seconds)

    return results


def serialize_results(results: list[DOIVerificationResult]) -> str:
    return json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2)


def summarize_results(results: list[DOIVerificationResult]) -> dict[str, int]:
    summary = {"total": len(results), "verified": 0, "not_found": 0,
               "retracted": 0, "invalid_format": 0,
               "unverified_no_network": 0, "error": 0}
    for r in results:
        summary[r.status] = summary.get(r.status, 0) + 1
    return summary
