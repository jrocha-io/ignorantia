#!/usr/bin/env python3
"""
search_catalogo_teses_capes.py — Catálogo de Teses e Dissertações da CAPES.

Catálogo oficial de teses e dissertações defendidas em programas de pós-graduação
reconhecidos pela CAPES. Diferente da BDTD (que indexa repositórios institucionais
heterogeneamente), este catálogo é o **registro oficial governamental brasileiro**.

~1.5M registros desde 1987. Banca de mestrado/doutorado brasileira frequentemente
cobra ambos (BDTD + Catálogo CAPES) — não são redundantes:
- BDTD: text full em PDF, mas cobertura depende do repositório institucional ter
  digitalizado o trabalho.
- Catálogo CAPES: registro oficial completo, mas full-text depende do programa
  enviar — disponibilidade variável.

Site: https://catalogodeteses.capes.gov.br/
**Sem API REST pública robusta**. Endpoint de busca via interface web; OAI-PMH
parcial via Plataforma Sucupira (acesso restrito).

Esta v2.11.0 implementa modo mock + busca pública parcial. Para SR estrita em PT-BR,
combinar com search_bdtd.py garante cobertura.
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
_sys.path.insert(0, str(_Path(__file__).parent))
from _adapter_base import cli_exit_with_error_message
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

API = "https://catalogodeteses.capes.gov.br/catalogo-teses/"

DEFAULT_THROTTLE = 1.5
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "catalogo_teses_capes", "source_tier": "tier1",
        "method": "CAPES_THESES_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Letramento digital de idosos: revisão sistemática (dissertação)",
                "authors": ["Mock, A."], "year": 2023,
                "advisor": "Mock, P.",
                "venue": "Programa de Pós-Graduação em Educação — UFRGS",
                "thesis_type": "dissertação_mestrado",
                "language": "pt", "country": "BR",
                "is_oa": True,
                "url_for_pdf": "https://catalogodeteses.capes.gov.br/teses/MOCK001.pdf",
                "capes_id": "MOCK001",
                "knowledge_area": "Educação",
                "institution": "UFRGS",
            },
            {
                "title": "[mock] Saúde digital de idosos: estudo transversal (tese)",
                "authors": ["Mock, B."], "year": 2024,
                "advisor": "Mock, Q.",
                "venue": "Programa de Pós-Graduação em Saúde Coletiva — UFBA",
                "thesis_type": "tese_doutorado",
                "language": "pt", "country": "BR",
                "is_oa": True,
                "url_for_pdf": "https://catalogodeteses.capes.gov.br/teses/MOCK002.pdf",
                "capes_id": "MOCK002",
                "knowledge_area": "Saúde Coletiva",
                "institution": "UFBA",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # Catálogo CAPES não tem API REST pública robusta; busca pública via JSF/AJAX.
    # Esta implementação faz best-effort GET com query parameter; resposta é HTML.
    params = {
        "p_p_id": "buscaSimplesCatalogoTeses_WAR_BuscaSimplesCatalogoTesesportlet",
        "p_p_lifecycle": "0",
        "p_p_state": "normal",
        "p_p_mode": "view",
        "_buscaSimplesCatalogoTeses_WAR_BuscaSimplesCatalogoTesesportlet_termo": query,
    }
    if year_start and year_end:
        params["_buscaSimplesCatalogoTeses_WAR_BuscaSimplesCatalogoTesesportlet_anoInicial"] = year_start
        params["_buscaSimplesCatalogoTeses_WAR_BuscaSimplesCatalogoTesesportlet_anoFinal"] = year_end
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {
            "source": "catalogo_teses_capes", "source_tier": "tier1",
            "method": "CAPES_THESES_REAL_PARTIAL",
            "query": query, "year_start": year_start, "year_end": year_end,
            "url_consulted": url, "raw_size_bytes": len(raw), "results": [],
            "note": ("Catálogo CAPES retornou HTML (Liferay/JSF); parser detalhado é TODO. "
                     "Não há API REST pública estável. Plataforma Sucupira oferece OAI-PMH "
                     "limitado para programas (acesso restrito a IES). Recomendação: combinar "
                     "com search_bdtd.py para máxima cobertura de teses BR."),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "catalogo_teses_capes", "source_tier": "tier1",
                "method": "CAPES_THESES_REAL_ERROR",
                "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Catálogo CAPES adapter (Tier 1; teses/dissertações BR).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[catalogo_teses_capes] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "catalogo_teses_capes")


if __name__ == "__main__":
    sys.exit(_cli())
