#!/usr/bin/env python3
"""
search_proquest_full.py — ProQuest full via institucional.

ProQuest é uma das maiores agregadoras com >90 bases (ABI/Inform Global, Dissertations
& Theses Global, ERIC, etc.). Indexa ~50M registros e oferece full-text para grande
parte. ProQuest OA subset (PQDT Open) já está coberto em search_proquest_oa.py.

Acesso legal:
- KEY: **ProQuest não tem API individual gratuita.** ProQuest TDM Studio existe
  para clientes institucionais com licença + projeto aprovado.
- PROXY: caminho padrão para IES com ProQuest.
- FALLBACK_MD: predominante para usuários sem afiliação institucional.

Esta v2.15.0 implementa stub honesto. Subset OA já coberto por search_proquest_oa.py;
acesso full exige proxy institucional ou fallback `.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _adapter_base import (
    PaywallAdapter, AdapterResult, make_cli,
)


class ProQuestFullAdapter(PaywallAdapter):
    SOURCE_NAME = "proquest_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "PROQUEST_API_KEY"  # nominal

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_NOT_AVAILABLE", query=query,
            error=("ProQuest não tem API individual gratuita. ProQuest TDM Studio exige "
                   "cliente institucional + projeto aprovado. Para subset OA, use "
                   "search_proquest_oa.py (já implementado). Para full, PROXY institucional "
                   "ou FALLBACK_MD."),
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("ProQuest via proxy é HTML; parser TODO. Recomenda-se exportar manualmente "
                  "do ProQuest Discovery em formato RIS/CSV e fornecer à skill. Para "
                  "subset OA gratuito, search_proquest_oa.py cobre PQDT Open."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Doctoral dissertation: digital learning (ProQuest)",
                 "authors": ["Mock, A."], "year": 2023,
                 "venue": "ProQuest Dissertations & Theses Global",
                 "language": "en", "is_oa": False,
                 "publication_type": "dissertation"},
                {"title": "[mock] Business management: case study (ProQuest ABI/Inform)",
                 "authors": ["Mock, B."], "year": 2024,
                 "venue": "ProQuest ABI/Inform Global",
                 "language": "en", "is_oa": False,
                 "publication_type": "trade-journal"},
            ],
        )


_cli = make_cli(ProQuestFullAdapter,
                "ProQuest full adapter (Tier 2; sem API; PROXY institucional + FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
