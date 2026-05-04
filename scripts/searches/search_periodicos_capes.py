#!/usr/bin/env python3
"""
search_periodicos_capes.py — Adapter para Portal de Periódicos CAPES.

O Portal CAPES é o gateway federado brasileiro para acesso a bases pagas (Scopus,
Web of Science, Elsevier ScienceDirect, Springer Link, Wiley, ACM, IEEE Xplore,
Taylor & Francis, Embase, etc.) via autenticação CAFe (Comunidade Acadêmica
Federada da RNP).

Site: https://www-periodicos-capes-gov-br.ezl.periodicos.capes.gov.br/
Acesso programático: requer credenciais institucionais válidas via CAFe.

POLÍTICA da v2.9.0 (Decisão 24): este adapter NÃO armazena nem solicita credenciais.
Quando o usuário tem acesso CAFe vinculado a uma IES brasileira credenciada, ele pode
gerar busca booleana e copiar/colar manualmente no portal autenticado, ou rodar
internamente em ambiente já autenticado por proxy. O adapter, sem credenciais
fornecidas, retorna instruções claras para o usuário.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PORTAL_URL = "https://www.periodicos.capes.gov.br/"


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "periodicos_capes", "source_tier": "tier0", "method": "PERIODICOS_CAPES_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Digital literacy among older adults: systematic review",
                "authors": ["Smith, J.", "Doe, A."], "year": 2023,
                "venue": "Journal of Medical Internet Research",
                "doi": "10.0000/capes-mock-001",
                "language": "en", "is_oa": False,
                "access_via": "ScienceDirect (via Periódicos CAPES + CAFe)",
                "url": "https://www-sciencedirect.ez.periodicos.capes.gov.br/mock-001",
            },
            {
                "title": "[mock] Mobile health technologies for elderly: a meta-analysis",
                "authors": ["Wang, L."], "year": 2022,
                "venue": "The Lancet Digital Health",
                "doi": "10.0000/capes-mock-002",
                "language": "en", "is_oa": False,
                "access_via": "Elsevier (via Periódicos CAPES + CAFe)",
                "url": "https://www-thelancet.ez.periodicos.capes.gov.br/mock-002",
            },
        ],
    }


def _real_without_credentials(query: str, year_start: int, year_end: int) -> dict:
    """Sem credenciais CAFe, retornamos instruções acionáveis em vez de tentar scraping.

    Razão: o Portal CAPES requer autenticação federada SAML/Shibboleth, com sessão
    interativa. Tentar scraping headless seria frágil e potencialmente violaria ToS.
    """
    return {
        "source": "periodicos_capes",
        "source_tier": "tier0",  # prioridade 0 (Decisão 24)
        "method": "PERIODICOS_CAPES_INSTRUCTIONS",
        "query": query,
        "year_start": year_start,
        "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 0,
        "results": [],
        "user_action_required": {
            "instruction_pt_br": (
                "O Portal de Periódicos CAPES exige autenticação institucional (CAFe). "
                "O `ignorantia` gerou a string booleana acima. Acesse o portal manualmente, "
                "entre com seu login institucional, execute a busca, exporte os resultados "
                "(CSV/RIS/BibTeX) e adicione o arquivo em `<output-dir>/user_provided/`."
            ),
            "portal_url": PORTAL_URL,
            "expected_export_filename": "periodicos_capes_export.<csv|ris|bib>",
            "expected_destination": "<output-dir>/user_provided/",
            "boolean_query_to_paste": query,
            "year_filter": f"{year_start}–{year_end}" if year_start and year_end else "—",
        },
    }


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           mock: bool = False) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real_without_credentials(query, year_start or 0, year_end or 0)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Portal de Periódicos CAPES adapter (Tier 0 — prioridade).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    if r.get("user_action_required"):
        print("[periodicos_capes] AÇÃO MANUAL NECESSÁRIA — instruções gravadas em:", args.output)
    else:
        n = r.get("total_results", len(r.get("results", [])))
        print(f"[periodicos_capes] {n} resultados (mock) → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
