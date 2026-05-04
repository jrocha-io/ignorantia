#!/usr/bin/env python3
"""
search_jstor_full.py — JSTOR via Data for Research (DfR) ou JSTOR Constellate.

JSTOR full (não OA) tem ~12M itens em humanidades, ciências sociais. Para SR em
humanidades com banca rigorosa, é frequentemente exigida.

Acesso legal:
- KEY: JSTOR Data for Research (DfR) via aplicação acadêmica em
  https://about.jstor.org/whats-in-jstor/text-mining-support/.
  Aprovação manual; para projetos específicos. Variável: `JSTOR_DFR_KEY`.
- PROXY: usuários em IES com JSTOR via proxy.
- FALLBACK_MD: predominante para usuários sem aprovação DfR.

Esta v2.14.0 implementa stub honesto: DfR exige aprovação project-by-project,
e nenhuma chave individual padrão funciona. PROXY institucional é o caminho
real; ou JSTOR Open Content (subset OA) já implementado em search_jstor_oa.py
para o que é gratuito.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _adapter_base import (
    PaywallAdapter, AdapterResult, make_cli,
)


class JSTORFullAdapter(PaywallAdapter):
    SOURCE_NAME = "jstor_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "JSTOR_DFR_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REQUIRES_PROJECT_APPROVAL", query=query,
            error=("JSTOR Data for Research (DfR) requer aprovação project-by-project. "
                   "Não há API individual standard. Para SR em humanidades, recomenda-se "
                   "(a) search_jstor_oa.py para subset OA gratuito; (b) PROXY institucional; "
                   "(c) FALLBACK_MD com lista cruzada via Crossref filter publisher=JSTOR."),
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note="JSTOR via proxy é HTML; parser TODO. Recomenda-se search_jstor_oa.py + FALLBACK_MD.",
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Sociological theory: comprehensive review (JSTOR)",
                 "authors": ["Mock, A."], "year": 2018,
                 "doi": "10.2307/jstor-mock-001",
                 "venue": "American Journal of Sociology",
                 "language": "en", "is_oa": False,
                 "publication_type": "article"},
                {"title": "[mock] Historiography of science: monograph (JSTOR)",
                 "authors": ["Mock, B."], "year": 2020,
                 "doi": "10.2307/jstor-mock-002",
                 "venue": "JSTOR Books",
                 "language": "en", "is_oa": False,
                 "publication_type": "book"},
            ],
        )


_cli = make_cli(JSTORFullAdapter,
                "JSTOR full adapter (Tier 2; DfR exige aprovação; predominância FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
