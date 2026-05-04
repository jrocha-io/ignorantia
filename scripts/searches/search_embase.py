#!/usr/bin/env python3
"""
search_embase.py — Embase via Elsevier Embase API.

Embase é a base biomédica complementar à PubMed, com cobertura mais europeia/global,
~32M registros, indexação Emtree (vocabulário próprio). Para SR de saúde rigorosa,
PubMed + Cochrane CENTRAL + Embase formam o tripé canônico expandido recomendado
pelo Cochrane Handbook 6.4.

Acesso legal:
- KEY: chave Elsevier API + license para Embase (separada de Scopus/ScienceDirect).
  Embase API tem custo associado mesmo para academic use. Variável: `ELSEVIER_EMBASE_KEY`.
- PROXY: usuários em IES com assinatura institucional Embase.
- FALLBACK_MD: para a maioria dos usuários (Embase é caro mesmo academicamente).

Endpoint: https://api.elsevier.com/embase/article
Documentação: https://dev.elsevier.com/embase_api.html

Nota de honestidade declarativa: Embase é a base mais difícil de acessar
programaticamente entre as Elsevier. Maioria dos usuários cairá em FALLBACK_MD.
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


EMBASE_API = "https://api.elsevier.com/embase/article"


class EmbaseAdapter(PaywallAdapter):
    SOURCE_NAME = "embase"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "ELSEVIER_EMBASE_KEY"  # chave separada do Scopus/SD

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # Embase API usa Emtree query syntax
        emtree_query = query
        if year_start and year_end:
            emtree_query = f"({query}) AND [{year_start}-{year_end}]/py"
        params = {"query": emtree_query, "count": min(max_results, 25)}
        url = f"{EMBASE_API}?{urllib.parse.urlencode(params)}"
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
            err_msg = f"HTTP {exc.code}: Embase API ({exc.reason})"
            if exc.code == 401:
                err_msg += ". Embase API requer chave com licença ativa específica para Embase " \
                           "(separada da Scopus/ScienceDirect). Verifique sua subscription."
            elif exc.code == 429:
                err_msg += ". Quota Embase excedida — Embase tem limite mais restrito."
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_HTTPERROR", query=query, error=err_msg,
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
            )

        # Embase retorna formato distinto; parser best-effort
        entries = (data.get("results") or {}).get("article", []) or []
        items: list[FetchedItem] = []
        for e in entries[:max_results]:
            items.append(FetchedItem(
                title=(e.get("titleAndAuthor") or {}).get("title") or "",
                authors=[a.get("name", "") for a in (e.get("authors") or [])][:10],
                year=e.get("publicationYear"),
                doi=e.get("doi"),
                issn=(e.get("source") or {}).get("issn"),
                venue=(e.get("source") or {}).get("title"),
                language=e.get("language", "en"),
                is_oa=False,  # Embase = paywall por definição
                publication_type=e.get("publicationType"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))

        total = data.get("totalCount", len(kept))
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
        # Embase via Embase.com com OvidSP proxy é frequente em IES
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="PROXY_NOT_IMPLEMENTED", query=query,
            note=("Acesso a Embase via proxy institucional (Ovid/Embase.com) retorna HTML "
                  "que exige parser específico. Em SRs rigorosas de saúde, considere "
                  "exportar resultados manualmente do Ovid em formato RIS/CSV e fornecer "
                  "à skill via search_orchestrator com flag --import-manual."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] European cohort study on digital health adoption",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.0000/embase-mock-001",
                 "issn": "0306-3674",
                 "venue": "British Journal of Sports Medicine",
                 "language": "en", "is_oa": False,
                 "publication_type": "Article in Press"},
                {"title": "[mock] Pharmacovigilance analysis: digital reporting tools",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.0000/embase-mock-002",
                 "issn": "0114-5916",
                 "venue": "Drug Safety",
                 "language": "en", "is_oa": False,
                 "publication_type": "Article"},
            ],
        )


_cli = make_cli(EmbaseAdapter,
                "Embase adapter (Tier 2; Elsevier Embase API; predominância de FALLBACK_MD).")

if __name__ == "__main__":
    sys.exit(_cli())
