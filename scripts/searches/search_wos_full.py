#!/usr/bin/env python3
"""
search_wos_full.py — Clarivate Web of Science Starter API.

Web of Science (Clarivate) é a outra grande base bibliográfica comercial junto com
Scopus. ~95M registros com Journal Citation Reports (JCR), Impact Factor, e Times
Cited tracking. Reviewers de Q1 e bancas de doutorado frequentemente cobram WoS.

Acesso legal:
- KEY: Clarivate Web of Science Starter API (~10k req/mês gratuito).
  https://developer.clarivate.com/apis/woslite — Starter mais limitado; Extended
  requer subscription paga.
- PROXY: usuários em IES com WoS via proxy.
- FALLBACK_MD.

Endpoint: https://wos-api.clarivate.com/api/wos-starter/v1/documents
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


WOS_STARTER_API = "https://wos-api.clarivate.com/api/wos-starter/v1/documents"


class WoSFullAdapter(PaywallAdapter):
    SOURCE_NAME = "wos_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "CLARIVATE_API_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # WoS query syntax: TS=(...) é Topic search
        wos_query = f"TS=({query})"
        if year_start and year_end:
            wos_query += f" AND PY={year_start}-{year_end}"
        params = {
            "db": "WOS",
            "q": wos_query,
            "limit": min(max_results, 50),  # Starter limita 50/req
            "page": 1,
        }
        url = f"{WOS_STARTER_API}?{urllib.parse.urlencode(params)}"
        headers = {
            "User-Agent": USER_AGENT,
            "X-ApiKey": api_key,
            "Accept": "application/json",
        }
        if throttle > 0:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_msg = f"HTTP {exc.code}: WoS Starter API ({exc.reason})"
            if exc.code == 401:
                err_msg += ". Verifique se CLARIVATE_API_KEY está válida."
            elif exc.code == 429:
                err_msg += ". Quota mensal Starter excedida (~10k req/mês)."
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_HTTPERROR", query=query, error=err_msg,
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
            )

        hits = data.get("hits", []) or []
        items: list[FetchedItem] = []
        for h in hits[:max_results]:
            names = (h.get("names") or {}).get("authors", []) or []
            authors = [a.get("displayName", "") for a in names][:10]
            year_pub = (h.get("source") or {}).get("publishYear")
            issn = next((i.get("value") for i in (h.get("identifiers") or [])
                         if i.get("type") == "issn"), None)
            doi = next((i.get("value") for i in (h.get("identifiers") or [])
                        if i.get("type") == "doi"), None)
            items.append(FetchedItem(
                title=(h.get("title") or {}).get("value") or "",
                authors=authors,
                year=year_pub,
                doi=doi,
                issn=issn,
                venue=(h.get("source") or {}).get("sourceTitle"),
                language="en",
                is_oa=False,  # WoS metadados; OA varia
                url=f"https://www.webofscience.com/wos/woscc/full-record/{h.get('uid')}"
                    if h.get("uid") else None,
                publication_type=h.get("documentTypes", [None])[0]
                                 if isinstance(h.get("documentTypes"), list) else h.get("documentTypes"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))

        total = (data.get("metadata") or {}).get("total", len(kept))
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
            note=("WoS via proxy retorna HTML; preferir KEY mode com chave Starter (gratuita "
                  "~10k req/mês): https://developer.clarivate.com/apis/woslite"),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] WoS-indexed review of digital interventions",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.0000/wos-mock-001",
                 "issn": "0140-6736",
                 "venue": "The Lancet",
                 "language": "en", "is_oa": False,
                 "url": "https://www.webofscience.com/wos/woscc/full-record/WOS:MOCK001",
                 "publication_type": "Article"},
                {"title": "[mock] Bibliometric analysis of digital health (WoS)",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.0000/wos-mock-002",
                 "issn": "1751-1577",
                 "venue": "Journal of Informetrics",
                 "language": "en", "is_oa": False,
                 "publication_type": "Article"},
            ],
        )


_cli = make_cli(WoSFullAdapter, "Web of Science Starter adapter (Tier 2; Clarivate API).")

if __name__ == "__main__":
    sys.exit(_cli())
