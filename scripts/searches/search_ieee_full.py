#!/usr/bin/env python3
"""
search_ieee_full.py — IEEE Xplore Search API.

IEEE Xplore é a base canônica de engenharia elétrica, eletrônica, computação,
telecomunicações. ~5.5M documentos: artigos de journal, conferências, standards,
livros, cursos.

Acesso legal:
- KEY: IEEE Xplore API key. Disponível para developers via cadastro em
  https://developer.ieee.org/. **Não-gratuita para uso comercial**; academic use
  permitido com limites mais baixos. Variável: `IEEE_API_KEY`.
- PROXY: usuários em IES com IEEE Xplore institucional via proxy.
- FALLBACK_MD: para usuários sem chave + sem proxy.

Endpoint: https://ieeexploreapi.ieee.org/api/v1/search/articles
Documentação: https://developer.ieee.org/docs
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


IEEE_API = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


class IEEEFullAdapter(PaywallAdapter):
    SOURCE_NAME = "ieee_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "IEEE_API_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        params = {
            "querytext": query,
            "max_records": min(max_results, 200),
            "format": "json",
            "apikey": api_key,
        }
        if year_start:
            params["start_year"] = year_start
        if year_end:
            params["end_year"] = year_end
        url = f"{IEEE_API}?{urllib.parse.urlencode(params)}"
        if throttle > 0:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                        "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_msg = f"HTTP {exc.code}: IEEE Xplore API ({exc.reason})"
            if exc.code == 401:
                err_msg += ". Verifique se sua chave IEEE_API_KEY tem subscription ativa."
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_HTTPERROR", query=query, error=err_msg,
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
            )

        articles = data.get("articles", []) or []
        items: list[FetchedItem] = []
        for a in articles[:max_results]:
            authors_list = (a.get("authors") or {}).get("authors", []) or []
            authors = [au.get("full_name", "") for au in authors_list][:10]
            items.append(FetchedItem(
                title=a.get("title", ""),
                authors=authors,
                year=a.get("publication_year"),
                doi=a.get("doi"),
                issn=a.get("issn") or a.get("isbn"),
                isbn=a.get("isbn"),
                venue=a.get("publication_title"),
                language="en",
                is_oa=(a.get("access_type") == "OPEN_ACCESS"),
                url=a.get("html_url"),
                url_for_pdf=a.get("pdf_url"),
                abstract=(a.get("abstract") or "")[:500],
                publication_type=a.get("content_type"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))

        total = data.get("total_records", len(kept))
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
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("IEEE Xplore via proxy retorna HTML; preferir KEY mode com chave em "
                  "https://developer.ieee.org/. Para SR de CS/eng com banca rigorosa, "
                  "considere também busca complementar via search_dblp.py (DBLP cobre "
                  "grande parte dos metadados IEEE com identificadores cruzáveis)."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Machine learning for predictive maintenance: review",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.1109/ieee-mock-001",
                 "issn": "0018-9219",
                 "venue": "Proceedings of the IEEE",
                 "language": "en", "is_oa": False,
                 "url": "https://ieeexplore.ieee.org/document/MOCK001",
                 "publication_type": "Journals"},
                {"title": "[mock] 5G network architecture: comprehensive survey",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.1109/ieee-mock-002",
                 "issn": "1553-877X",
                 "venue": "IEEE Communications Surveys & Tutorials",
                 "language": "en", "is_oa": False,
                 "publication_type": "Journals"},
            ],
        )


_cli = make_cli(IEEEFullAdapter, "IEEE Xplore full adapter (Tier 2; cascata).")

if __name__ == "__main__":
    sys.exit(_cli())
