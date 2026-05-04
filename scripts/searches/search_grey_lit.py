#!/usr/bin/env python3
"""
search_grey_lit.py — Agregador de literatura cinza (relatórios governamentais e
de organismos internacionais).

Para Realist Review, White Paper, e Position Paper, literatura cinza é fonte
substantiva: relatórios UNESCO, OECD, World Bank, IPEA, INEP, NIST, OMS. Hoje a
skill cita esses recursos via web_fetch+web_search ad hoc. Este adapter padroniza:

- Captura metadados estruturados (título, ano, idioma, organização, tipo de relatório).
- Tenta extrair DOI quando disponível.
- Documenta a fonte de origem claramente para traceability.

Estratégia: cada fonte tem endpoint distinto. Adapter implementa "modo provedor"
selecionável via --provider. Os providers iniciais são:

- `world_bank`: Open Knowledge Repository (OAI-PMH + REST)
- `unesco`: UNESDOC (busca via API REST limitada + OAI-PMH)
- `oecd`: OECD iLibrary (busca pública HTML; metadados parciais)
- `ipea`: IPEA publicações (HTML scraping mínimo)
- `inep`: INEP publicações (HTML scraping mínimo)
- `nist`: NIST Pubs (REST API + OAI-PMH)
- `who`: WHO IRIS (DSpace REST)

Para cada provider, modo mock retorna fixture; modo real faz best-effort com
declaração honesta quando parser detalhado é TODO.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"


DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


PROVIDERS = {
    "world_bank": {
        "name": "World Bank Open Knowledge Repository",
        "endpoint": "https://openknowledge.worldbank.org/rest/search",
        "country": "international",
        "lang_default": "en",
    },
    "unesco": {
        "name": "UNESDOC (UNESCO Digital Library)",
        "endpoint": "https://unesdoc.unesco.org/search",
        "country": "international",
        "lang_default": "en",
    },
    "oecd": {
        "name": "OECD iLibrary",
        "endpoint": "https://www.oecd-ilibrary.org/search",
        "country": "international",
        "lang_default": "en",
    },
    "ipea": {
        "name": "IPEA — Instituto de Pesquisa Econômica Aplicada",
        "endpoint": "https://www.ipea.gov.br/portal/index.php?option=com_content&view=article&id=publicacoes&Itemid=80",
        "country": "BR",
        "lang_default": "pt",
    },
    "inep": {
        "name": "INEP — Instituto Nacional de Estudos e Pesquisas Educacionais",
        "endpoint": "https://www.gov.br/inep/pt-br/centrais-de-conteudo/publicacoes",
        "country": "BR",
        "lang_default": "pt",
    },
    "nist": {
        "name": "NIST Publications",
        "endpoint": "https://www.nist.gov/publications/search",
        "country": "US",
        "lang_default": "en",
    },
    "who": {
        "name": "WHO IRIS — Institutional Repository for Information Sharing",
        "endpoint": "https://iris.who.int/rest/search",
        "country": "international",
        "lang_default": "en",
    },
}


def _mock(provider: str, query: str, year_start: int, year_end: int) -> dict:
    pcfg = PROVIDERS[provider]
    return {
        "source": f"grey_lit/{provider}", "source_tier": "tier1",
        "method": f"GREY_LIT_{provider.upper()}_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "provider": provider,
        "provider_name": pcfg["name"],
        "total_results": 2,
        "results": [
            {
                "title": f"[mock] Digital literacy and aging: a {pcfg['name']} report",
                "authors": [f"{pcfg['name']}"], "year": 2023,
                "venue": pcfg["name"],
                "language": pcfg["lang_default"],
                "country": pcfg["country"],
                "is_oa": True,
                "url_for_pdf": f"{pcfg['endpoint']}/MOCK001.pdf",
                "report_type": "policy_report",
                "doi": None,
            },
            {
                "title": f"[mock] Educational technology in low-income contexts ({pcfg['name']})",
                "authors": [f"{pcfg['name']}"], "year": 2024,
                "venue": pcfg["name"],
                "language": pcfg["lang_default"],
                "country": pcfg["country"],
                "is_oa": True,
                "url_for_pdf": f"{pcfg['endpoint']}/MOCK002.pdf",
                "report_type": "technical_report",
                "doi": None,
            },
        ],
    }


def _real(provider: str, query: str, year_start: int, year_end: int,
          max_results: int, throttle: float, timeout: float) -> dict:
    pcfg = PROVIDERS[provider]
    # Tentativa best-effort GET para o endpoint do provider; parser detalhado é TODO
    # para a maioria, exceto World Bank e WHO que têm DSpace REST estruturado.
    if provider == "world_bank":
        params = {"query": query, "expand": "metadata", "limit": max_results}
        url = f"{pcfg['endpoint']}?{urllib.parse.urlencode(params)}"
    elif provider == "who":
        params = {"query": query, "expand": "metadata", "limit": max_results}
        url = f"{pcfg['endpoint']}?{urllib.parse.urlencode(params)}"
    else:
        params = {"q": query}
        url = f"{pcfg['endpoint']}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json,text/html"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # Para DSpace-based (World Bank, WHO), tenta parser
        if provider in ("world_bank", "who"):
            try:
                items = json.loads(raw.decode("utf-8"))
                if isinstance(items, list):
                    results = []
                    for item in items[:max_results]:
                        md = {m.get("key"): m.get("value")
                              for m in (item.get("metadata") or [])}
                        results.append({
                            "title": md.get("dc.title"),
                            "authors": [md.get("dc.contributor.author")] if md.get("dc.contributor.author") else [],
                            "year": (md.get("dc.date.issued") or "")[:4] or None,
                            "venue": pcfg["name"],
                            "language": md.get("dc.language.iso") or pcfg["lang_default"],
                            "country": pcfg["country"],
                            "is_oa": True,
                            "url_for_pdf": f"{pcfg['endpoint'].rsplit('/', 1)[0]}/handle/{item.get('handle', '')}",
                            "report_type": md.get("dc.type") or "report",
                            "doi": md.get("dc.identifier.doi"),
                        })
                    # Filtrar por janela temporal
                    if year_start and year_end:
                        results = [r for r in results
                                   if r["year"] and year_start <= int(r["year"]) <= year_end]
                    return {
                        "source": f"grey_lit/{provider}", "source_tier": "tier1",
                        "method": f"GREY_LIT_{provider.upper()}_REAL_PARTIAL",
                        "query": query, "year_start": year_start, "year_end": year_end,
                        "provider": provider,
                        "total_results": len(results),
                        "results": results,
                    }
            except (json.JSONDecodeError, ValueError):
                pass
        # Fallback parcial
        return {
            "source": f"grey_lit/{provider}", "source_tier": "tier1",
            "method": f"GREY_LIT_{provider.upper()}_REAL_PARTIAL",
            "query": query, "provider": provider,
            "url_consulted": url, "raw_size_bytes": len(raw), "results": [],
            "note": (f"{pcfg['name']} retornou conteúdo não-JSON; parser detalhado é TODO. "
                     f"Para uso programático estruturado, considere OAI-PMH quando disponível "
                     f"({pcfg['endpoint'].rsplit('/', 1)[0]}/oai)."),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": f"grey_lit/{provider}", "source_tier": "tier1",
                "method": f"GREY_LIT_{provider.upper()}_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(provider: str, query: str, year_start: int | None = None,
           year_end: int | None = None, max_results: int = 100,
           mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if provider not in PROVIDERS:
        raise ValueError(f"provider inválido: {provider!r}; use um de {list(PROVIDERS.keys())}")
    if mock:
        return _mock(provider, query, year_start or 0, year_end or 0)
    return _real(provider, query, year_start or 0, year_end or 0, max_results,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Grey literature adapter (multi-provider).")
    p.add_argument("--query", required=True)
    p.add_argument("--provider", default="unesco", choices=list(PROVIDERS.keys()),
                   help="Provider de literatura cinza. Default: unesco. Para outras (world_bank, oecd, ipea, inep, nist, who), passe explicitamente.")
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.provider, args.query, args.year_start, args.year_end,
               args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[grey_lit/{args.provider}] {n} resultados → {args.output}")
    if r.get("error"):
        # A7 (v2.20.0, auditoria #2): imprime erro em stderr para o orquestrador
        # mostrar mensagem útil em [warn], em vez de mensagem vazia.
        print(f"[grey_lit/{args.provider}] error: {r.get('error')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
