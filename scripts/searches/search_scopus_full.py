#!/usr/bin/env python3
"""
search_scopus_full.py — Scopus via Elsevier Search API.

Scopus (Elsevier) é uma das duas grandes bases bibliográficas comerciais (a outra
é Web of Science). ~80M registros, cobertura multidisciplinar com curadoria.
Reviewers Q1 frequentemente cobram busca explícita em Scopus em SR de saúde,
ciências sociais, business research.

Acesso legal:
- KEY: chave Elsevier API (https://dev.elsevier.com/), gratuita para academic use
  via cadastro institucional. Limite: ~20k req/semana por chave.
- PROXY: usuários em rede institucional com assinatura Elsevier podem usar proxy.
- FALLBACK_MD: lista cruzada com Crossref/OpenAlex filtrada por venues Elsevier.

Endpoint: https://api.elsevier.com/content/search/scopus
Documentação: https://dev.elsevier.com/sc_search_views.html
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


SCOPUS_API = "https://api.elsevier.com/content/search/scopus"


class ScopusFullAdapter(PaywallAdapter):
    SOURCE_NAME = "scopus_full"
    SOURCE_TIER = "tier2"  # Tier 2: metadados livres com chave; full-text varia
    KEY_ENV_VAR = "ELSEVIER_API_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # Scopus usa Title-Abs-Key search com filtros temporais via PUBYEAR
        scopus_query = query
        if year_start and year_end:
            scopus_query = f"({query}) AND PUBYEAR > {year_start - 1} AND PUBYEAR < {year_end + 1}"
        params = {
            "query": scopus_query,
            "count": min(max_results, 25),  # Scopus limita 25 por chamada
            "field": "dc:title,dc:creator,prism:publicationName,prism:coverDate,"
                     "prism:doi,prism:issn,subtype,citedby-count,openaccess",
        }
        url = f"{SCOPUS_API}?{urllib.parse.urlencode(params)}"
        headers = {
            "User-Agent": USER_AGENT,
            "X-ELS-APIKey": api_key,
            "Accept": "application/json",
        }
        if throttle > 0:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_HTTPERROR", query=query,
                year_start=year_start, year_end=year_end,
                error=f"HTTP {exc.code}: Scopus API ({exc.reason}). "
                      "Verifique se a chave tem permissão 'scopus:search' e quota disponível.",
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query,
                error=str(exc),
            )

        entries = (data.get("search-results") or {}).get("entry", []) or []
        items: list[FetchedItem] = []
        for e in entries[:max_results]:
            authors_raw = e.get("dc:creator", "")
            authors = [authors_raw] if isinstance(authors_raw, str) and authors_raw else []
            year_pub = None
            cover_date = e.get("prism:coverDate", "")
            if cover_date:
                try:
                    year_pub = int(cover_date[:4])
                except ValueError:
                    pass
            items.append(FetchedItem(
                title=e.get("dc:title") or "",
                authors=authors,
                year=year_pub,
                doi=e.get("prism:doi"),
                issn=e.get("prism:issn"),
                venue=e.get("prism:publicationName"),
                language="en",
                is_oa=(e.get("openaccess") == "1" or e.get("openaccess") is True),
                url=next((l.get("@href") for l in e.get("link", [])
                          if l.get("@ref") == "scopus"), None),
                publication_type=e.get("subtype"),
            ))

        # Filtro local Camada 1 (DD-10)
        lf = LocalFilter(year_start, year_end, accepted_languages=None,
                         require_doi=False)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))

        total = int((data.get("search-results") or {}).get("opensearch:totalResults", 0))
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REAL", query=query,
            year_start=year_start, year_end=year_end,
            total_results=total,
            results=[it.to_dict() for it in kept],
            log_camada1=log,
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        # Scopus via proxy: a interface web é HTML; parser detalhado é TODO.
        # Em ambientes institucionais com sciencedirect/scopus em proxy.ezproxy.uni.edu.br
        # o usuário pode preferir baixar resultados manualmente e gerar fallback .md.
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("Proxy para Scopus retorna HTML que exige parser específico não-implementado. "
                  "Preferir KEY mode com chave Elsevier API gratuita para academic use. "
                  "Cadastro: https://dev.elsevier.com/"),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Comprehensive review of digital health interventions",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.0000/scopus-mock-001",
                 "issn": "0140-6736",
                 "venue": "The Lancet",
                 "language": "en", "is_oa": False,
                 "url": "https://www.scopus.com/record/display.uri?eid=2-s2.0-MOCK001",
                 "publication_type": "ar"},
                {"title": "[mock] Bibliometric analysis of digital literacy research",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.0000/scopus-mock-002",
                 "issn": "0306-4573",
                 "venue": "Information Processing & Management",
                 "language": "en", "is_oa": True,
                 "url": "https://www.scopus.com/record/display.uri?eid=2-s2.0-MOCK002",
                 "publication_type": "ar"},
            ],
        )


# CLI
_cli = make_cli(ScopusFullAdapter,
                "Scopus full adapter (Tier 2; Elsevier API; cascata KEY→PROXY→FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
