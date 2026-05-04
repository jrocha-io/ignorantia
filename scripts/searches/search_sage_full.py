#!/usr/bin/env python3
"""
search_sage_full.py — Sage Publications full via TDM/cross-search.

Sage publica >1,000 journals em ciências sociais, humanidades, educação,
saúde. Para SR de educação (notadamente Educational Research Review, Sage),
ciências sociais (Sage Open), e enfermagem, busca em Sage é frequentemente
cobrada.

Acesso legal:
- KEY: Sage TDM API ainda em desenvolvimento (não é GA pública). Acordos TDM
  são negociados institucionalmente. Variável: `SAGE_TDM_KEY` (raro).
- PROXY: caminho normal — IES com Sage Journals via proxy SAGE.
- FALLBACK_MD: predominante.

Esta v2.14.0 implementa estratégia indireta: descobrir DOIs Sage via Crossref
(member 179 = Sage), e indicar TDM-ready. Para usuários sem TDM key + sem
proxy, fallback `.md` com instruções CAFe.
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


class SageFullAdapter(PaywallAdapter):
    SOURCE_NAME = "sage_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "SAGE_TDM_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # Estratégia: Crossref filter member:179 (Sage) para descoberta de DOIs
        params = {
            "query": query,
            "filter": "member:179",  # Sage Publications
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
                error=f"HTTP {exc.code} on Crossref filter Sage ({exc.reason})",
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
        log["note"] = ("DOIs Sage descobertos via Crossref. Para baixar full-text TDM, "
                       "negocie acordo TDM com Sage via sua biblioteca institucional.")

        total = (data.get("message") or {}).get("total-results", len(kept))
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REAL", query=query,
            year_start=year_start, year_end=year_end,
            total_results=total,
            results=[it.to_dict() for it in kept],
            log_camada1=log,
            note="Adapter Sage descobre DOIs via Crossref filter (member:179=Sage); full-text TDM exige acordo institucional.",
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Educational research methods review (Sage)",
                 "authors": ["Mock, A."], "year": 2023,
                 "doi": "10.1177/sage-mock-001",
                 "issn": "0034-6543",
                 "venue": "Review of Educational Research",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
                {"title": "[mock] Sociology of media: comprehensive review (Sage)",
                 "authors": ["Mock, B."], "year": 2024,
                 "doi": "10.1177/sage-mock-002",
                 "issn": "0163-4437",
                 "venue": "Media, Culture & Society",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
            ],
        )


_cli = make_cli(SageFullAdapter,
                "Sage full adapter (Tier 2; descoberta via Crossref + TDM negociado).")

if __name__ == "__main__":
    sys.exit(_cli())
