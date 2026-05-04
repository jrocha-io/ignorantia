#!/usr/bin/env python3
"""
search_acm_full.py — ACM Digital Library full.

ACM Digital Library tem ~1M artigos em CS, com proceedings de SIGCHI, SIGGRAPH,
SIGMOD, SIGSOFT, etc. Para SR de CS com banca rigorosa, é frequentemente cobrada.

Acesso legal:
- KEY: **ACM não tem API pública gratuita.** ACM oferece OpenTOC API parcial
  para metadados de table-of-contents, e ACM SIGCHI Open Source Initiative,
  mas nenhuma busca textual programática ampla.
- PROXY: usuários em IES com ACM via proxy.
- FALLBACK_MD: caminho dominante.

Estratégia: descobrir DOIs ACM via Crossref filter (member 320 = ACM), e gerar
fallback `.md` para usuários sem proxy. Para usuários com chave OpenTOC (raro),
estende cobertura com índice de TOCs.
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


CROSSREF_API = "https://api.crossref.org/works"


class ACMFullAdapter(PaywallAdapter):
    SOURCE_NAME = "acm_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "ACM_OPENTOC_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # Estratégia: Crossref filter member:320 (ACM)
        params = {
            "query": query,
            "filter": "member:320",  # ACM
            "rows": min(max_results, 100),
        }
        if year_start and year_end:
            params["filter"] += f",from-pub-date:{year_start},until-pub-date:{year_end}"
        url = f"{CROSSREF_API}?{urllib.parse.urlencode(params)}"
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
                error=f"HTTP {exc.code} on Crossref filter ACM ({exc.reason})",
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
            )

        records = (data.get("message") or {}).get("items", []) or []
        items: list[FetchedItem] = []
        for r in records[:max_results]:
            year_pub = None
            issued = (r.get("issued") or {}).get("date-parts", [])
            if issued and issued[0]:
                year_pub = issued[0][0]
            authors = [f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
                       for a in (r.get("author") or [])][:10]
            items.append(FetchedItem(
                title=(r.get("title") or [""])[0],
                authors=authors,
                year=year_pub,
                doi=r.get("DOI"),
                issn=(r.get("ISSN") or [None])[0],
                venue=(r.get("container-title") or [None])[0],
                language=r.get("language", "en"),
                is_oa=False,
                url=r.get("URL"),
                publication_type=r.get("type"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))
        log["note"] = "DOIs ACM descobertos via Crossref. Full-text exige login institucional."

        total = (data.get("message") or {}).get("total-results", len(kept))
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REAL", query=query,
            year_start=year_start, year_end=year_end,
            total_results=total,
            results=[it.to_dict() for it in kept],
            log_camada1=log,
            note=("ACM não tem API pública gratuita. Adapter descobre metadados via Crossref "
                  "filter (member:320=ACM); full-text exige login institucional ACM ou DL."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] CHI 2023 paper on accessibility (ACM)",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.1145/acm-mock-001",
                 "venue": "CHI '23 Proceedings",
                 "language": "en", "is_oa": False,
                 "publication_type": "proceedings-article"},
                {"title": "[mock] ACM TOSEM survey on testing (2024)",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.1145/acm-mock-002",
                 "issn": "1049-331X",
                 "venue": "ACM Transactions on Software Engineering and Methodology",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
            ],
        )


_cli = make_cli(ACMFullAdapter,
                "ACM Digital Library full adapter (Tier 2; descoberta via Crossref).")

if __name__ == "__main__":
    sys.exit(_cli())
