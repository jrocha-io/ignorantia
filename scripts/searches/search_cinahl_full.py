#!/usr/bin/env python3
"""
search_cinahl_full.py — CINAHL (Cumulative Index to Nursing and Allied Health
Literature) via EBSCOhost.

CINAHL é a base canônica de enfermagem e ciências aliadas à saúde, ~6M registros.
Para SR de enfermagem com banca rigorosa, é obrigatória.

Acesso legal:
- KEY: EBSCOhost API requer credencial institucional (não há chave individual).
- PROXY: caminho normal — IES com CINAHL via proxy EBSCO.
- FALLBACK_MD: predominante para usuários sem afiliação institucional.

Esta implementação reflete a realidade: CINAHL é predominantemente fallback `.md`
para usuários da skill, com exceção de quem está logado em rede institucional
com CINAHL ativa.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _adapter_base import (
    PaywallAdapter, AdapterResult, make_cli,
)


class CINAHLFullAdapter(PaywallAdapter):
    SOURCE_NAME = "cinahl_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "EBSCO_CINAHL_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REQUIRES_INSTITUTIONAL_AUTH", query=query,
            error=("CINAHL via EBSCO API requer credencial institucional ativa "
                   "(não há chave individual). Maioria dos usuários cairá em "
                   "FALLBACK_MD. Recomenda-se PROXY mode para usuários em IES."),
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("CINAHL via EBSCO Discovery institucional é HTML; parser TODO. "
                  "Recomenda-se exportar manualmente do EBSCO Discovery e fornecer à "
                  "skill via mecanismo de import manual."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Nursing intervention review (CINAHL)",
                 "authors": ["Mock, A."], "year": 2023,
                 "doi": "10.0000/cinahl-mock-001",
                 "issn": "1365-2648",
                 "venue": "Journal of Advanced Nursing",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
                {"title": "[mock] Allied health practice patterns (CINAHL)",
                 "authors": ["Mock, B."], "year": 2024,
                 "doi": "10.0000/cinahl-mock-002",
                 "issn": "1755-7682",
                 "venue": "International Journal of Health Sciences",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
            ],
        )


_cli = make_cli(CINAHLFullAdapter,
                "CINAHL full adapter (Tier 2; EBSCO; predominância FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
