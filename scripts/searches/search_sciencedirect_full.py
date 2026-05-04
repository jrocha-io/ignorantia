#!/usr/bin/env python3
"""
search_sciencedirect_full.py — ScienceDirect via Elsevier API.

ScienceDirect (Elsevier) é a plataforma de full-text de >2,500 journals científicos
do Elsevier. ~16M artigos. Para SR de saúde, ciências naturais e engenharia, busca
em ScienceDirect é frequentemente exigida por reviewers Q1.

Acesso legal:
- KEY: chave Elsevier API (https://dev.elsevier.com/), gratuita para academic.
  Usa o mesmo `ELSEVIER_API_KEY` do search_scopus_full.py.
- PROXY: usuários em rede institucional com assinatura ScienceDirect.
- FALLBACK_MD.

Endpoint: https://api.elsevier.com/content/search/sciencedirect
Documentação: https://dev.elsevier.com/sciencedirect_apis.html
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


SCIENCEDIRECT_API = "https://api.elsevier.com/content/search/sciencedirect"


class ScienceDirectFullAdapter(PaywallAdapter):
    SOURCE_NAME = "sciencedirect_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "ELSEVIER_API_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        params = {"query": query, "count": min(max_results, 25)}
        if year_start and year_end:
            # ScienceDirect usa filtro por date range com parâmetro pubDate
            params["date"] = f"{year_start}-{year_end}"
        url = f"{SCIENCEDIRECT_API}?{urllib.parse.urlencode(params)}"
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
                error=f"HTTP {exc.code}: ScienceDirect API ({exc.reason}). "
                      "Verifique permissão 'sciencedirect:search' na chave.",
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
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
                is_oa=(e.get("openaccess") == "1"),
                url=next((l.get("@href") for l in e.get("link", [])
                          if l.get("@ref") == "scidir"), None),
                publication_type=e.get("pii"),
            ))

        lf = LocalFilter(year_start, year_end)
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
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("Proxy ScienceDirect retorna HTML que exige parser específico. "
                  "Preferir KEY mode com chave Elsevier API. "
                  "Cadastro: https://dev.elsevier.com/"),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Mobile health interventions for chronic disease",
                 "authors": ["Mock, A."], "year": 2023,
                 "doi": "10.0000/sd-mock-001",
                 "issn": "0277-9536",
                 "venue": "Social Science & Medicine",
                 "language": "en", "is_oa": False,
                 "url": "https://www.sciencedirect.com/science/article/pii/MOCK001"},
                {"title": "[mock] Educational technology adoption: meta-review",
                 "authors": ["Mock, B.", "Mock, C."], "year": 2024,
                 "doi": "10.0000/sd-mock-002",
                 "issn": "0360-1315",
                 "venue": "Computers & Education",
                 "language": "en", "is_oa": True,
                 "url": "https://www.sciencedirect.com/science/article/pii/MOCK002"},
            ],
        )


_cli = make_cli(ScienceDirectFullAdapter,
                "ScienceDirect full adapter (Tier 2; Elsevier API; cascata).")

if __name__ == "__main__":
    sys.exit(_cli())
