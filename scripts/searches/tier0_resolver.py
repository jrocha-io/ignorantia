#!/usr/bin/env python3
"""
tier0_resolver.py — Resolvedor unificado Tier 0 da `ignorantia` v2.6.0.

Recebe DOIs de qualquer Tier 1-3 e resolve para a melhor URL OA legítima
disponível, em ordem de prioridade:

    1. Unpaywall          (cobertura ampla, golden+hybrid+green OA, ~50M artigos)
    2. Open Access Button (best-effort complementar; preprints + green OA)
    3. CAFe / institucional (placeholder; requer credenciais do usuário)
    4. Solicitação ao autor (URL gerada para uso manual; não-automatizada)

Decisão arquitetural v2.6.0 (Decisão 17):
- Plataformas em disputa judicial (com litígios em curso por publishers como Elsevier,
  Wiley, ACS, Springer Nature) NÃO estão integradas ao pipeline automatizado. A não-integração
  é arquitetural: o `ignorantia` não toma posição em disputas judiciais ativas e não decide pelo
  usuário como obter material de acesso fechado. Decisão sobre como resolver o gap é do usuário.
- Unpaywall + OAB cobrem o problema operacional (acesso a paywalled durante triagem PRISMA)
  via fontes OA legítimas: golden OA, hybrid OA, green OA (preprints depositados pelos próprios
  autores em arXiv, bioRxiv, repos institucionais).
- Para artigos genuinamente fechados, a ferramenta gera link de solicitação ao autor
  (caminho legítimo padrão da comunidade acadêmica há décadas).

Uso programático:
    from tier0_resolver import resolve_doi_with_tier0
    rec = resolve_doi_with_tier0("10.1186/s13643-016-0384-4", email="contact@project")
    if rec.has_legitimate_oa:
        print(rec.best_url)

Uso CLI:
    python tier0_resolver.py --dois-file dois.txt --email contact@example.org \\
                              --out enriched.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Imports locais (sem ajustar sys.path; CLI assume rodar de scripts/searches/ ou via -m)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import search_unpaywall  # noqa: E402
import search_oa_button  # noqa: E402


@dataclass
class Tier0Record:
    """Resultado consolidado da resolução Tier 0 para um DOI."""
    doi: str
    has_legitimate_oa: bool = False
    best_url: str | None = None
    best_url_pdf: str | None = None
    best_source: str | None = None  # unpaywall | oa_button | cafe | author_request
    oa_status: str | None = None     # gold | hybrid | green | bronze | closed
    license: str | None = None
    version: str | None = None        # publishedVersion | acceptedVersion | submittedVersion
    title: str | None = None
    journal_name: str | None = None
    publisher: str | None = None
    year: int | None = None
    request_url_for_author: str | None = None
    sources_tried: list[str] = field(default_factory=list)
    errors_per_source: dict[str, str] = field(default_factory=dict)


def resolve_doi_with_tier0(doi: str, email: str | None = None, mock: bool = False,
                            try_oa_button_fallback: bool = True) -> Tier0Record:
    """Resolve DOI tentando Tier 0 em ordem de prioridade."""
    rec = Tier0Record(doi=doi)

    # 1) Unpaywall (sempre tentado primeiro)
    rec.sources_tried.append("unpaywall")
    up = search_unpaywall.resolve_doi(doi, email=email or "", mock=mock)
    if up.error and "404" not in (up.method or ""):
        rec.errors_per_source["unpaywall"] = up.error
    if up.is_oa and up.best_oa_url:
        rec.has_legitimate_oa = True
        rec.best_url = up.best_oa_url
        rec.best_url_pdf = up.best_oa_url_pdf
        rec.best_source = "unpaywall"
        rec.oa_status = up.oa_status
        rec.license = up.best_oa_license
        rec.version = up.best_oa_version
        rec.title = up.title
        rec.journal_name = up.journal_name
        rec.publisher = up.publisher
        rec.year = up.year
        return rec

    # Capturar metadados se Unpaywall conhece o DOI mesmo sem OA
    if up.title:
        rec.title = up.title
    if up.journal_name:
        rec.journal_name = up.journal_name
    if up.publisher:
        rec.publisher = up.publisher
    if up.year:
        rec.year = up.year
    if up.oa_status:
        rec.oa_status = up.oa_status

    # 2) Open Access Button (best-effort, opcional)
    if try_oa_button_fallback:
        rec.sources_tried.append("oa_button")
        oab = search_oa_button.resolve_doi(doi, mock=mock)
        if oab.error:
            rec.errors_per_source["oa_button"] = oab.error
        if oab.is_oa and oab.oa_url:
            rec.has_legitimate_oa = True
            rec.best_url = oab.oa_url
            rec.best_source = "oa_button"
            rec.oa_status = rec.oa_status or "green"
            if oab.title and not rec.title:
                rec.title = oab.title
            return rec
        if oab.request_url:
            rec.request_url_for_author = oab.request_url

    # 3) CAFe / institucional — placeholder.
    # Implementação futura requer credenciais do usuário (CAFe da RNP no Brasil
    # intermedia acesso a Capes Periódicos legalmente). Por enquanto, apenas
    # documentamos a opção no journal de execução do skill.
    rec.sources_tried.append("cafe_institutional_placeholder")

    # 4) Fallback final: link de solicitação ao autor
    if not rec.request_url_for_author:
        rec.request_url_for_author = f"https://oa.works/request/{doi}"
        rec.best_source = "author_request"

    return rec


def resolve_dois_with_tier0(dois: list[str], email: str | None = None,
                             mock: bool = False) -> list[Tier0Record]:
    return [resolve_doi_with_tier0(d, email=email, mock=mock) for d in dois]


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Tier 0 unified resolver — Unpaywall + OAB + author request fallback.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--doi", help="DOI único.")
    src.add_argument("--dois-file", help="Arquivo com 1 DOI por linha.")
    parser.add_argument("--email", help="Email para Unpaywall (obrigatório fora de --mock).")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--out", help="Output JSON (default stdout).")
    parser.add_argument("--no-oab-fallback", action="store_true",
                        help="Desliga fallback Open Access Button (só Unpaywall).")
    args = parser.parse_args()

    if not args.mock and not args.email:
        print("[tier0] erro: --email obrigatório fora de --mock", file=sys.stderr)
        return 2

    if args.doi:
        dois = [args.doi]
    else:
        p = Path(args.dois_file)
        if not p.exists():
            print(f"[tier0] arquivo não encontrado: {p}", file=sys.stderr)
            return 2
        dois = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    records = []
    for d in dois:
        records.append(resolve_doi_with_tier0(
            d, email=args.email or "mock@example.org",
            mock=args.mock,
            try_oa_button_fallback=not args.no_oab_fallback,
        ))

    payload = {
        "schema_version": "1.0.0",
        "tier": 0,
        "n_dois": len(records),
        "n_oa_found": sum(1 for r in records if r.has_legitimate_oa),
        "n_author_request_only": sum(1 for r in records
                                      if not r.has_legitimate_oa and r.request_url_for_author),
        "records": [asdict(r) for r in records],
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[tier0] {payload['n_oa_found']}/{payload['n_dois']} legítimo OA, "
              f"{payload['n_author_request_only']} author-request → {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
