#!/usr/bin/env python3
"""
search_springer_full.py — Springer Nature Meta API.

Springer Nature publica >2,900 journals e cobre múltiplas áreas com forte presença
em ciências naturais, medicina e CS. ~13M artigos.

Acesso legal:
- KEY: Springer Nature API Key — **GRATUITA com cadastro** em
  https://dev.springernature.com/. Limite: ~5,000 req/dia.
- PROXY: usuários em IES com SpringerLink podem acessar via proxy.
- FALLBACK_MD.

Endpoint: https://api.springernature.com/meta/v2/json
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


SPRINGER_API = "https://api.springernature.com/meta/v2/json"


class SpringerFullAdapter(PaywallAdapter):
    SOURCE_NAME = "springer_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "SPRINGER_API_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # Springer query DSL com onlinedatefrom/to para janela temporal
        params = {"q": query, "p": min(max_results, 100), "api_key": api_key}
        if year_start and year_end:
            params["q"] = f'{query} onlinedatefrom:{year_start}-01-01 onlinedateto:{year_end}-12-31'
        url = f"{SPRINGER_API}?{urllib.parse.urlencode(params)}"
        if throttle > 0:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                        "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_HTTPERROR", query=query,
                error=f"HTTP {exc.code}: Springer Nature API ({exc.reason})",
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
            )

        records = data.get("records", []) or []
        items: list[FetchedItem] = []
        for r in records[:max_results]:
            authors = [c.get("creator", "") for c in (r.get("creators") or [])][:10]
            year_pub = None
            pub_date = r.get("publicationDate", "")
            if pub_date:
                try:
                    year_pub = int(pub_date[:4])
                except ValueError:
                    pass
            url_pdf = next((u.get("value") for u in (r.get("url") or [])
                            if u.get("format") == "pdf"), None)
            items.append(FetchedItem(
                title=r.get("title", ""),
                authors=authors,
                year=year_pub,
                doi=r.get("doi"),
                issn=r.get("issn") or r.get("eIssn"),
                isbn=r.get("isbn"),
                venue=r.get("publicationName"),
                language=r.get("language", "en"),
                is_oa=(r.get("openaccess") == "true"),
                url=r.get("url", [{}])[0].get("value") if r.get("url") else None,
                url_for_pdf=url_pdf,
                abstract=(r.get("abstract") or "")[:500],
                publication_type=r.get("contentType"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))

        total = int(data.get("result", [{}])[0].get("total", len(kept)) if data.get("result") else len(kept))
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
            note=("SpringerLink via proxy retorna HTML; preferir KEY mode com chave "
                  "Springer Nature API GRATUITA: https://dev.springernature.com/"),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Springer review of digital interventions",
                 "authors": ["Mock, A."], "year": 2023,
                 "doi": "10.1007/springer-mock-001",
                 "issn": "1573-7322",
                 "venue": "Quality of Life Research",
                 "language": "en", "is_oa": True,
                 "url": "https://link.springer.com/article/10.1007/springer-mock-001",
                 "url_for_pdf": "https://link.springer.com/content/pdf/10.1007/springer-mock-001.pdf",
                 "publication_type": "Article"},
                {"title": "[mock] Computational thinking education: textbook chapter",
                 "authors": ["Mock, B.", "Mock, C."], "year": 2024,
                 "doi": "10.1007/springer-mock-002",
                 "isbn": "978-3-031-000000",
                 "venue": "Springer Educational Texts",
                 "language": "en", "is_oa": False,
                 "publication_type": "Chapter"},
            ],
        )


_cli = make_cli(SpringerFullAdapter,
                "Springer Nature full adapter (Tier 2; chave gratuita; cascata).")

if __name__ == "__main__":
    sys.exit(_cli())
