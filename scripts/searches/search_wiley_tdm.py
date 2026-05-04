#!/usr/bin/env python3
"""
search_wiley_tdm.py — Wiley Online Library Text & Data Mining (TDM) API.

Wiley publica >1,600 journals, com forte presença em saúde, ciências sociais,
educação e ciências naturais. Cobertura ~9M artigos.

Acesso legal:
- KEY: Wiley TDM API key. Obtida via assinatura institucional + aceitação do
  TDM agreement. **Não há chave gratuita pública**; chave só via instituição
  com licença Wiley + aplicação formal a Wiley TDM (https://onlinelibrary.wiley.com/library-info/resources/text-and-datamining).
- PROXY: usuários em IES com Wiley + acesso a TDM endpoint via institucional.
- FALLBACK_MD: predominante para usuários sem afiliação institucional Wiley.

Endpoint TDM: https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}
Search endpoint não-público; TDM API é primariamente para download de full-text
DADO um DOI conhecido. Para busca, recomenda-se usar Crossref/OpenAlex e filtrar
por publisher=Wiley, depois usar TDM para baixar full-text.

Esta é a estratégia implementada: KEY mode usa Crossref para busca + Wiley TDM
para indicar que full-text está disponível com a chave.
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
WILEY_TDM_BASE = "https://api.wiley.com/onlinelibrary/tdm/v1/articles"


class WileyTDMAdapter(PaywallAdapter):
    SOURCE_NAME = "wiley_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "WILEY_TDM_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        """Estratégia: usa Crossref para descobrir DOIs Wiley e indica TDM-ready."""
        # Filter Crossref por publisher Wiley
        params = {
            "query": query,
            "filter": "member:311",  # Crossref member ID 311 = Wiley
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
                error=f"HTTP {exc.code} on Crossref filter Wiley ({exc.reason})",
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
            tdm_url = f"{WILEY_TDM_BASE}/{r.get('DOI')}" if r.get("DOI") else None
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
                is_oa=False,  # Wiley = predominantemente paywall
                url=r.get("URL"),
                url_for_pdf=tdm_url,  # TDM endpoint para baixar com chave
                publication_type=r.get("type"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))
        log["note_tdm"] = (f"DOIs Wiley descobertos via Crossref. Para baixar full-text, "
                           f"use Wiley TDM API com chave {self.KEY_ENV_VAR}: "
                           f"GET {WILEY_TDM_BASE}/{{doi}} com Wiley-TDM-Client-Token.")

        total = (data.get("message") or {}).get("total-results", len(kept))
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REAL", query=query,
            year_start=year_start, year_end=year_end,
            total_results=total,
            results=[it.to_dict() for it in kept],
            log_camada1=log,
            note=("Adapter Wiley descobre DOIs via Crossref filter (member:311=Wiley); "
                  "full-text TDM exige chave WILEY_TDM_KEY + TDM agreement institucional."),
        )

    def _proxy_search(self, query, year_start, year_end, max_results,
                      proxy_host, throttle, timeout):
        # Wiley via proxy institucional retorna HTML autenticado; parser não-implementado.
        # Retornamos None para que a cascata caia em FALLBACK_MD com lista cruzada via
        # Crossref filter member:311=Wiley. KEY mode (Crossref-based) é o caminho
        # principal para Wiley nesta implementação.
        return None  # cascata cai em FALLBACK_MD; lista cruzada via Crossref

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Nursing intervention review (Wiley)",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.1111/wiley-mock-001",
                 "issn": "1365-2648",
                 "venue": "Journal of Advanced Nursing",
                 "language": "en", "is_oa": False,
                 "url": "https://onlinelibrary.wiley.com/doi/10.1111/wiley-mock-001",
                 "url_for_pdf": f"{WILEY_TDM_BASE}/10.1111/wiley-mock-001",
                 "publication_type": "journal-article"},
                {"title": "[mock] Educational psychology meta-analysis (Wiley)",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.1111/wiley-mock-002",
                 "issn": "0007-0998",
                 "venue": "British Journal of Educational Psychology",
                 "language": "en", "is_oa": False,
                 "publication_type": "journal-article"},
            ],
        )


_cli = make_cli(WileyTDMAdapter,
                "Wiley full adapter via TDM (Tier 2; descoberta via Crossref + TDM key).")

if __name__ == "__main__":
    sys.exit(_cli())
