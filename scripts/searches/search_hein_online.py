#!/usr/bin/env python3
"""
search_hein_online.py — HeinOnline (William S. Hein & Co.) full.

HeinOnline é a base canônica de literatura jurídica e histórica em direito.
~200M páginas: revistas jurídicas, tratados, decisões, documentos governamentais.
Para SR jurídica com banca rigorosa (notadamente em programas de pós-graduação
em Direito), HeinOnline é frequentemente cobrada.

Acesso legal:
- KEY: **HeinOnline não tem API pública.** Acesso programático apenas via
  HeinOnline Direct para clientes institucionais com licença ativa.
- PROXY: caminho padrão — IES com HeinOnline via proxy.
- FALLBACK_MD: predominante para usuários sem afiliação institucional jurídica.

Esta v2.15.0 implementa stub honesto. Para SR jurídica estrita, o caminho
funcional é (a) PROXY com biblioteca da IES, ou (b) FALLBACK_MD listando o que
precisa ser obtido via HeinOnline manualmente.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _adapter_base import (
    PaywallAdapter, AdapterResult, make_cli,
)


class HeinOnlineAdapter(PaywallAdapter):
    SOURCE_NAME = "hein_online"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "HEIN_API_KEY"  # nominal; HeinOnline não tem API pública

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_NOT_AVAILABLE", query=query,
            error=("HeinOnline não tem API pública. Acesso programático apenas via "
                   "HeinOnline Direct (clientes institucionais com licença ativa). "
                   "Para SR jurídica, recomenda-se PROXY institucional ou FALLBACK_MD."),
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("HeinOnline via proxy é HTML; parser TODO. Recomenda-se exportar "
                  "manualmente do HeinOnline Discovery em formato RIS/CSV e fornecer "
                  "à skill via mecanismo de import manual. Para programas de pós-graduação "
                  "em Direito, banca espera ver HeinOnline citada — gerar FALLBACK_MD "
                  "com lista cruzada via Crossref/OpenAlex (publishers jurídicos: "
                  "American Bar Foundation, JSTOR Law)."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Constitutional law review article (HeinOnline)",
                 "authors": ["Mock, A."], "year": 2023,
                 "venue": "Yale Law Journal",
                 "language": "en", "is_oa": False,
                 "publication_type": "law-review-article"},
                {"title": "[mock] Digital privacy and constitutional rights (HeinOnline)",
                 "authors": ["Mock, B."], "year": 2024,
                 "venue": "Harvard Law Review",
                 "language": "en", "is_oa": False,
                 "publication_type": "law-review-article"},
            ],
        )


_cli = make_cli(HeinOnlineAdapter,
                "HeinOnline adapter (Tier 2; sem API; PROXY institucional + FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
