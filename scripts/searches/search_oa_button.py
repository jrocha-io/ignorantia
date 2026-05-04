#!/usr/bin/env python3
"""
search_oa_button.py — Tier 0 OA locator via Open Access Button (OAB).

Complemento ao Unpaywall: cobertura ligeiramente diferente (mais ênfase em
preprints e green OA), e fallback "request a copy from the author" quando não
há versão OA disponível.

API: https://api.openaccessbutton.org/find?id=<doi>
- Free, sem chave de API documentada para uso individual
- Mantida pela Open Access Button (oa.works), org sem fins lucrativos
- ATENÇÃO: a API tem histórico de instabilidade; tratamos como best-effort
  complementar ao Unpaywall, nunca substituto.

Política da `ignorantia`:
- Tier 0 secundário, chamado APÓS Unpaywall.
- Se Unpaywall já achou OA legítimo, OAB não é consultado (economia de chamadas).
- Se Unpaywall falhou ou retornou closed, OAB pode achar via repositório institucional.
- Se NEM OAB acha, retorna `request_url` para solicitação ao autor (caminho legítimo).

Uso programático:
    from search_oa_button import resolve_doi
    rec = resolve_doi("10.1186/s13643-016-0384-4")
    if rec.is_oa:
        print(rec.oa_url)
    elif rec.request_url:
        print(f"Solicitar ao autor: {rec.request_url}")

Uso CLI:
    python search_oa_button.py --doi 10.1186/s13643-016-0384-4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

OAB_BASE_URL = "https://api.openaccessbutton.org/find"

DEFAULT_THROTTLE_SECONDS = 0.5
DEFAULT_TIMEOUT = 15.0


@dataclass
class OABRecord:
    doi: str
    is_oa: bool = False
    oa_url: str | None = None
    request_url: str | None = None  # URL para solicitar cópia ao autor
    title: str | None = None
    error: str | None = None
    method: str = "OAB_REAL"


def _mock_record(doi: str) -> OABRecord:
    """Fixture determinística — alguns DOIs canônicos da literatura SLR."""
    fixtures = {
        "10.1186/s13643-016-0384-4": OABRecord(
            doi=doi, is_oa=True,
            oa_url="https://systematicreviewsjournal.biomedcentral.com/articles/10.1186/s13643-016-0384-4",
            title="Rayyan—a web and mobile app for systematic reviews",
            method="OAB_MOCK",
        ),
        "10.0000/closed-fixture": OABRecord(
            doi=doi, is_oa=False,
            request_url="https://oa.works/request/10.0000/closed-fixture",
            method="OAB_MOCK",
        ),
    }
    return fixtures.get(doi, OABRecord(
        doi=doi, is_oa=False,
        request_url=f"https://oa.works/request/{doi}",
        method="OAB_MOCK_DEFAULT",
    ))


def resolve_doi(doi: str, mock: bool = False,
                throttle: float = DEFAULT_THROTTLE_SECONDS,
                timeout: float = DEFAULT_TIMEOUT) -> OABRecord:
    """Resolve DOI contra OAB. Best-effort — API pode estar instável."""
    doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    if not doi or "/" not in doi:
        return OABRecord(doi=doi, error="invalid DOI format")

    if mock:
        return _mock_record(doi)

    try:
        import requests
    except ImportError:
        return OABRecord(doi=doi,
                         error="requests package not available",
                         method="OAB_REAL_UNAVAILABLE")

    if throttle > 0:
        time.sleep(throttle)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        resp = requests.get(OAB_BASE_URL, params={"id": doi}, headers=headers, timeout=timeout)
        if resp.status_code == 404:
            # OAB retorna 404 quando não encontra OA — mas oferece request URL
            return OABRecord(doi=doi, is_oa=False,
                             request_url=f"https://oa.works/request/{doi}",
                             method="OAB_REAL_NOT_FOUND")
        resp.raise_for_status()
        data = resp.json()
        # Schema OAB: {url, metadata: {title, ...}} se OA, ou {message: ..., requested: ...} se não
        oa_url = data.get("url") or (data.get("data") or {}).get("url")
        if oa_url:
            metadata = data.get("metadata") or (data.get("data") or {}).get("metadata") or {}
            return OABRecord(
                doi=doi, is_oa=True, oa_url=oa_url,
                title=metadata.get("title"),
                method="OAB_REAL",
            )
        return OABRecord(
            doi=doi, is_oa=False,
            request_url=f"https://oa.works/request/{doi}",
            method="OAB_REAL_NO_OA",
        )
    except requests.HTTPError as exc:
        return OABRecord(doi=doi, error=f"HTTPError: {exc}",
                         method="OAB_REAL_HTTPERROR")
    except requests.RequestException as exc:
        return OABRecord(doi=doi, error=f"RequestException: {exc}",
                         method="OAB_REAL_NETERROR")
    except (ValueError, KeyError) as exc:
        return OABRecord(doi=doi, error=f"parse error: {exc}",
                         method="OAB_REAL_PARSEERROR")


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Tier 0 OA locator (Open Access Button).")
    parser.add_argument("--doi", required=True)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--out", help="Output JSON (default: stdout).")
    args = parser.parse_args()
    rec = resolve_doi(args.doi, mock=args.mock)
    out = json.dumps(asdict(rec), indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"[oab] {'OA found' if rec.is_oa else 'no OA'} → {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
