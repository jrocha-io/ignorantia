#!/usr/bin/env python3
"""
search_psycinfo_full.py — APA PsycInfo via APA PsycNET API ou EBSCOhost.

PsycInfo (American Psychological Association) é a base canônica de psicologia,
~5M registros desde 1887. Para SR estrita em psicologia ou psiquiatria, é
obrigatória.

Acesso legal:
- KEY: APA PsycNET API. Disponível para developers via parceria com EBSCOhost
  (que hospeda PsycInfo). Variável: `APA_API_KEY` ou `EBSCO_API_KEY` (são
  efetivamente o mesmo gateway).
- PROXY: maioria das IES com PsycInfo via EBSCO proxy.
- FALLBACK_MD: predominante; PsycInfo é raramente acessível sem afiliação.

Endpoint EBSCO: https://eds-api.ebscohost.com/edsapi/rest/Search

Nota de honestidade: A API EBSCO é primariamente para integração de bibliotecas
universitárias com seus discovery services. Acesso direct para individual
researchers é incomum. Maioria dos usuários da skill cairá em FALLBACK_MD.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _adapter_base import (
    PaywallAdapter, AdapterResult, FetchedItem, LocalFilter, make_cli,
    USER_AGENT, DEFAULT_THROTTLE, DEFAULT_TIMEOUT,
)


EBSCO_API = "https://eds-api.ebscohost.com/edsapi/rest/Search"


class PsycInfoFullAdapter(PaywallAdapter):
    SOURCE_NAME = "psycinfo_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "APA_API_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # EBSCO/APA require Bearer token; estrutura POST com auth headers
        # Esta é implementação best-effort; EBSCO API exige fluxo de autenticação
        # de 2 etapas (UIDAuthService + Search) que requer cliente institucional.
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REQUIRES_INSTITUTIONAL_AUTH", query=query,
            error=("APA PsycInfo via EBSCO API requer fluxo de autenticação institucional "
                   "(UIDAuthService + SessionAuth). API key sozinha é insuficiente sem "
                   "credencial institucional EBSCO ativa. Recomenda-se PROXY mode."),
            note=("Para usuários acadêmicos: APA Direct (https://www.apa.org/pubs/databases/psycinfo) "
                  "oferece acesso individual com subscrição APA. Para SR rigorosa em psicologia, "
                  "considere também search_pepsic.py (Periódicos em Psicologia BR) e "
                  "search_osf_preprints.py com provider=psyarxiv (PsyArXiv)."),
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("EBSCO Discovery via proxy institucional (web/HTML) é o caminho mais "
                  "comum para PsycInfo. Parser detalhado é TODO. Recomenda-se exportar "
                  "manualmente do EBSCO Discovery em formato RIS/CSV e fornecer à skill."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Cognitive behavioral therapy: meta-analysis (PsycInfo)",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.1037/psycinfo-mock-001",
                 "issn": "0033-2909",
                 "venue": "Psychological Bulletin",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
                {"title": "[mock] Educational psychology review (APA)",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.1037/psycinfo-mock-002",
                 "issn": "0022-0663",
                 "venue": "Journal of Educational Psychology",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
            ],
        )


_cli = make_cli(PsycInfoFullAdapter,
                "PsycInfo full adapter (Tier 2; EBSCO/APA; predominância FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
