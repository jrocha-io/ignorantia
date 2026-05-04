#!/usr/bin/env python3
"""
search_unpaywall.py — Tier 0 OA locator via Unpaywall API.

Não é "buscador" no sentido tradicional (não aceita query keywords). É um locator:
recebe DOI(s) e retorna se há versão OA legítima e onde está depositada.

Cobertura: ~50M+ artigos OA (golden, hybrid, green/preprint). Indexa apenas o que
publishers e autores liberaram explicitamente em repositórios institucionais,
preprint servers e portais OA. Não inclui cópias não-licenciadas.

API: https://api.unpaywall.org/v2/{doi}?email=<contact>
- Free, sem chave de API
- Email obrigatório (rate limiting + identificação)
- Rate limit: 100k requests/dia/email recomendado em uso responsável
- Sem auth headers; query param `email` cumpre o papel

Política da `ignorantia`: este módulo é Tier 0 — chamado APÓS qualquer busca por
query nos Tiers 1-3 retornar DOIs. Para cada DOI, enriquece com a melhor URL OA
disponível (best_oa_location.url_for_pdf).

Uso programático:
    from search_unpaywall import resolve_doi, resolve_dois_batch
    rec = resolve_doi("10.1186/s13643-016-0384-4", email="contact@project")
    if rec.is_oa:
        print(rec.best_oa_url)

Uso CLI:
    python search_unpaywall.py --doi 10.1186/s13643-016-0384-4 --email contact@example.org
    python search_unpaywall.py --dois-file dois.txt --email contact@example.org --out enriched.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

DEFAULT_THROTTLE_SECONDS = 0.1  # 10 req/s — bem dentro do envelope responsável
DEFAULT_TIMEOUT = 15.0


@dataclass
class UnpaywallRecord:
    """Resultado normalizado do Unpaywall para um DOI."""
    doi: str
    is_oa: bool = False
    oa_status: str | None = None  # gold, hybrid, green, bronze, closed
    best_oa_url: str | None = None
    best_oa_url_pdf: str | None = None
    best_oa_host_type: str | None = None  # publisher, repository
    best_oa_license: str | None = None  # cc-by, cc-by-nc, ...
    best_oa_version: str | None = None  # publishedVersion, acceptedVersion, submittedVersion
    title: str | None = None
    journal_name: str | None = None
    journal_is_in_doaj: bool = False
    publisher: str | None = None
    year: int | None = None
    has_repository_copy: bool = False
    repository_urls: list[str] = field(default_factory=list)
    error: str | None = None
    method: str = "UNPAYWALL_REAL"


def _normalize_unpaywall_response(doi: str, data: dict) -> UnpaywallRecord:
    """Converte resposta crua da API em UnpaywallRecord."""
    if not isinstance(data, dict):
        return UnpaywallRecord(doi=doi, error=f"unexpected response type: {type(data).__name__}")

    is_oa = bool(data.get("is_oa", False))
    best = data.get("best_oa_location") or {}
    locations = data.get("oa_locations") or []
    repo_urls = [
        loc.get("url") for loc in locations
        if loc.get("host_type") == "repository" and loc.get("url")
    ]
    journal = data.get("journal_name") or ""

    return UnpaywallRecord(
        doi=doi,
        is_oa=is_oa,
        oa_status=data.get("oa_status"),
        best_oa_url=best.get("url"),
        best_oa_url_pdf=best.get("url_for_pdf"),
        best_oa_host_type=best.get("host_type"),
        best_oa_license=best.get("license"),
        best_oa_version=best.get("version"),
        title=data.get("title"),
        journal_name=journal,
        journal_is_in_doaj=bool(data.get("journal_is_in_doaj", False)),
        publisher=data.get("publisher"),
        year=data.get("year"),
        has_repository_copy=len(repo_urls) > 0,
        repository_urls=repo_urls,
        method="UNPAYWALL_REAL",
    )


def resolve_doi(doi: str, email: str, mock: bool = False,
                throttle: float = DEFAULT_THROTTLE_SECONDS,
                timeout: float = DEFAULT_TIMEOUT) -> UnpaywallRecord:
    """Resolve um DOI contra Unpaywall.

    Args:
        doi: DOI no formato 10.xxxx/yyyy (sem prefixo https://doi.org/).
        email: Email de contato — exigido pela API.
        mock: Se True, retorna fixture sintética determinística (uso em CI).
        throttle: Espera entre chamadas em segundos.
        timeout: Timeout HTTP.

    Returns:
        UnpaywallRecord normalizado. Se erro, .error preenchido e .is_oa=False.
    """
    doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    if not doi or "/" not in doi:
        return UnpaywallRecord(doi=doi, error="invalid DOI format")

    if mock:
        return _mock_record(doi)

    if not email or "@" not in email:
        return UnpaywallRecord(
            doi=doi,
            error="email obrigatório para Unpaywall API; passe --email <contato@dominio>",
            method="UNPAYWALL_REAL_NO_EMAIL",
        )

    try:
        import requests
    except ImportError:
        return UnpaywallRecord(
            doi=doi,
            error="requests package not available; install with `pip install requests`",
            method="UNPAYWALL_REAL_UNAVAILABLE",
        )

    if throttle > 0:
        time.sleep(throttle)

    url = f"{UNPAYWALL_BASE_URL}/{doi}?email={email}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 404:
            return UnpaywallRecord(doi=doi, is_oa=False,
                                   error="DOI not in Unpaywall index",
                                   method="UNPAYWALL_REAL_404")
        resp.raise_for_status()
        data = resp.json()
        return _normalize_unpaywall_response(doi, data)
    except requests.HTTPError as exc:
        return UnpaywallRecord(doi=doi,
                               error=f"HTTPError: {exc}; status={resp.status_code}",
                               method="UNPAYWALL_REAL_HTTPERROR")
    except requests.RequestException as exc:
        return UnpaywallRecord(doi=doi, error=f"RequestException: {exc}",
                               method="UNPAYWALL_REAL_NETERROR")
    except (ValueError, KeyError) as exc:
        return UnpaywallRecord(doi=doi, error=f"parse error: {exc}",
                               method="UNPAYWALL_REAL_PARSEERROR")


def _mock_record(doi: str) -> UnpaywallRecord:
    """Fixture determinística — DOIs conhecidos da literatura PRISMA-2020 e SLR tooling."""
    fixtures = {
        # Rayyan paper — Springer, fully OA
        "10.1186/s13643-016-0384-4": UnpaywallRecord(
            doi=doi, is_oa=True, oa_status="gold",
            best_oa_url="https://systematicreviewsjournal.biomedcentral.com/articles/10.1186/s13643-016-0384-4",
            best_oa_url_pdf="https://systematicreviewsjournal.biomedcentral.com/track/pdf/10.1186/s13643-016-0384-4.pdf",
            best_oa_host_type="publisher", best_oa_license="cc-by", best_oa_version="publishedVersion",
            title="Rayyan—a web and mobile app for systematic reviews",
            journal_name="Systematic Reviews", journal_is_in_doaj=True,
            publisher="Springer Science and Business Media LLC", year=2016,
            has_repository_copy=False, repository_urls=[],
            method="UNPAYWALL_MOCK",
        ),
        # PRISMA 2020 statement — BMJ, hybrid OA
        "10.1136/bmj.n71": UnpaywallRecord(
            doi=doi, is_oa=True, oa_status="hybrid",
            best_oa_url="https://www.bmj.com/content/372/bmj.n71",
            best_oa_url_pdf="https://www.bmj.com/content/372/bmj.n71.full.pdf",
            best_oa_host_type="publisher", best_oa_license="cc-by", best_oa_version="publishedVersion",
            title="The PRISMA 2020 statement: an updated guideline for reporting systematic reviews",
            journal_name="BMJ", journal_is_in_doaj=False,
            publisher="BMJ", year=2021,
            method="UNPAYWALL_MOCK",
        ),
        # Caso fechado / paywalled
        "10.0000/closed-fixture": UnpaywallRecord(
            doi=doi, is_oa=False, oa_status="closed",
            method="UNPAYWALL_MOCK",
        ),
    }
    return fixtures.get(doi, UnpaywallRecord(
        doi=doi, is_oa=True, oa_status="green",
        best_oa_url=f"https://example-repo.org/{doi}",
        best_oa_host_type="repository", best_oa_license="cc-by",
        best_oa_version="acceptedVersion",
        has_repository_copy=True, repository_urls=[f"https://example-repo.org/{doi}"],
        method="UNPAYWALL_MOCK_DEFAULT",
        error="DOI fora da fixture canônica; usando default plausível",
    ))


def resolve_dois_batch(dois: list[str], email: str, mock: bool = False,
                       throttle: float = DEFAULT_THROTTLE_SECONDS) -> list[UnpaywallRecord]:
    """Resolve lista de DOIs sequencialmente respeitando throttle."""
    return [resolve_doi(d, email=email, mock=mock, throttle=throttle) for d in dois]


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Tier 0 OA locator (Unpaywall) — enriquece DOIs com URL OA legítima.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--doi", help="DOI único.")
    src.add_argument("--dois-file", help="Arquivo de texto com 1 DOI por linha.")
    parser.add_argument("--email", help="Email de contato (exigido pela API; opcional em --mock).")
    parser.add_argument("--mock", action="store_true",
                        help="Modo mock — usa fixtures determinísticas (default em CI).")
    parser.add_argument("--throttle", type=float, default=DEFAULT_THROTTLE_SECONDS)
    parser.add_argument("--out", help="Output JSON (se omitido, imprime em stdout).")
    args = parser.parse_args()

    if not args.mock and not args.email:
        print("[unpaywall] erro: --email obrigatório quando não em --mock", file=sys.stderr)
        return 2

    if args.doi:
        dois = [args.doi]
    else:
        p = Path(args.dois_file)
        if not p.exists():
            print(f"[unpaywall] arquivo não encontrado: {p}", file=sys.stderr)
            return 2
        dois = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    records = resolve_dois_batch(dois, email=args.email or "mock@example.org",
                                  mock=args.mock, throttle=args.throttle)
    payload = {
        "schema_version": "1.0.0",
        "tier": 0,
        "method": "UNPAYWALL_REAL" if not args.mock else "UNPAYWALL_MOCK",
        "n_dois": len(records),
        "n_oa_found": sum(1 for r in records if r.is_oa),
        "records": [asdict(r) for r in records],
    }
    out_text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"[unpaywall] {payload['n_oa_found']}/{payload['n_dois']} DOIs com OA legítimo → {args.out}")
    else:
        print(out_text)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
