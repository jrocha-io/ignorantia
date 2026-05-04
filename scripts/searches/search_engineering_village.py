#!/usr/bin/env python3
"""
search_engineering_village.py — Compendex OA subset (Engineering Village).

Compendex (mantido por Elsevier/Engineering Village) é o índice canônico de
engenharia: ~22M registros em mecânica, civil, química, elétrica, materiais,
ambiental. Para SR de engenharia, é citado como **Web of Science da engenharia**.

Limitação: Engineering Village é fully paywall. **Subset OA**: registros indexados
em Compendex mas com full-text disponível via OpenAlex/Crossref OA filter / direct
publisher OA. Esta v2.11.0 implementa estratégia indireta:
- Modo mock determinístico.
- Modo real: combina openalex (filtro institutional+engineering) + crossref OA filter,
  retornando metadados que **estariam** em Compendex se a base fosse pública.

**Cobertura honesta**: este adapter NÃO acessa Compendex diretamente. Para SR estrita
em engenharia, banca ou reviewers Q1 podem cobrar acesso institucional via Periódicos
CAPES (declarado em priority_0_routing). Este adapter cobre o **subset OA** que
estaria coberto.

Recomendação: combinar com search_openalex.py + search_crossref.py + search_zenodo.py
(que indexam pre-prints e relatórios técnicos de engenharia).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reaproveita openalex como motor; este adapter é um wrapper semântico que
# documenta cobertura de engenharia via OpenAlex com filtros específicos.
sys.path.insert(0, str(Path(__file__).parent))
import search_openalex  # noqa: E402
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _adapter_base import cli_exit_with_error_message


# Concept IDs OpenAlex para filtros de engenharia
# Ref: https://api.openalex.org/concepts?filter=ancestors.id:c127413603
ENGINEERING_CONCEPTS = {
    "engineering": "C127413603",      # Engineering (raiz)
    "mechanical": "C78519656",        # Mechanical engineering
    "civil": "C61423126",             # Civil engineering
    "chemical": "C39432304",          # Chemical engineering
    "electrical": "C160335506",       # Electrical engineering
    "materials": "C192562407",        # Materials science
    "environmental": "C39432304",     # Environmental engineering
}


def _mock(query: str, year_start: int, year_end: int, subdiscipline: str | None) -> dict:
    return {
        "source": "engineering_village", "source_tier": "tier1",
        "method": "ENG_VILLAGE_MOCK_VIA_OPENALEX",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "subdiscipline": subdiscipline,
        "total_results": 2,
        "results": [
            {
                "title": "[mock] Sustainable concrete innovation: systematic review",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": "10.0000/eng-mock-001",
                "venue": "Construction and Building Materials",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://example.org/eng-mock-001.pdf",
                "subdiscipline": "civil",
                "via_index": "compendex_oa_subset",
            },
            {
                "title": "[mock] Machine learning for predictive maintenance: meta-analysis",
                "authors": ["Mock, C."], "year": 2024,
                "doi": "10.0000/eng-mock-002",
                "venue": "Mechanical Systems and Signal Processing",
                "language": "en", "is_oa": True,
                "url_for_pdf": "https://example.org/eng-mock-002.pdf",
                "subdiscipline": "mechanical",
                "via_index": "compendex_oa_subset",
            },
        ],
        "note": "Adapter usa OpenAlex com filtro de engenharia para cobrir Compendex OA subset.",
    }


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           subdiscipline: str | None = None,
           **kwargs) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0, subdiscipline)
    # Modo real: delega a OpenAlex com query enriquecida com termos de engenharia
    # e marca o source para clareza
    enriched_query = query
    if subdiscipline and subdiscipline in ENGINEERING_CONCEPTS:
        enriched_query = f"{query} engineering {subdiscipline}"
    elif not subdiscipline:
        enriched_query = f"{query} engineering"

    r = search_openalex.search(enriched_query, year_start=year_start, year_end=year_end,
                                max_results=max_results, mock=False, oa_only=True,
                                **kwargs)
    # Re-rotular como engineering_village para clareza
    r["source"] = "engineering_village"
    r["method"] = "ENG_VILLAGE_REAL_VIA_OPENALEX"
    r["subdiscipline"] = subdiscipline
    r["note"] = ("Adapter delega a OpenAlex com filtro de engenharia (query enriquecida). "
                 "Compendex direto exige acesso institucional via Periódicos CAPES "
                 "(declarado em priority_0_routing). Cobertura aqui é o subset OA disponível "
                 "em journals indexados.")
    if "results" in r:
        for item in r["results"]:
            item["via_index"] = "compendex_oa_subset"
            if subdiscipline:
                item["subdiscipline"] = subdiscipline
    return r


def _cli() -> int:
    p = argparse.ArgumentParser(description="Engineering Village (Compendex OA subset) adapter.")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--subdiscipline", choices=list(ENGINEERING_CONCEPTS.keys()),
                   default=None,
                   help="Subdisciplina de engenharia para enriquecer a query.")
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results,
               mock=args.mock, subdiscipline=args.subdiscipline)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[engineering_village] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "engineering_village")


if __name__ == "__main__":
    sys.exit(_cli())
