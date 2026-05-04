#!/usr/bin/env python3
"""
search_google_scholar_serpapi.py — Google Scholar via SerpApi.

Google Scholar é o meta-índice mais abrangente da web acadêmica (~400M+ registros),
mas o Google **proíbe acesso programático** em seu ToS. Bibliotecas como `scholarly`
violam ToS e são bloqueadas regularmente.

Caminho legal: **SerpApi** (https://serpapi.com/) é serviço comercial de scraping
que **paga pelo direito** de fazer queries ao Google Scholar e oferece API REST
estável. Como o usuário paga pela chave SerpApi, o serviço assume responsabilidade
legal/técnica do scraping. **Único caminho legal conhecido para Google Scholar
programático.**

Acesso legal:
- KEY: SerpApi key (paga: ~$50/mo Hobby plan = 5k queries/mês; ~$150/mo Production).
  Variável: `SERPAPI_KEY`.
- PROXY: não aplicável (SerpApi é o "proxy" comercial-legal).
- FALLBACK_MD: para usuários sem chave SerpApi, gera lista de buscas que poderiam
  ser feitas manualmente em https://scholar.google.com.

Endpoint: https://serpapi.com/search?engine=google_scholar&q=...&api_key=...
Documentação: https://serpapi.com/google-scholar-api

Aviso de honestidade: dependência de serviço pago de terceiros. Para SR rigorosa
sem orçamento para SerpApi, recomenda-se usar adapters Tier 1 (CORE, OpenAlex,
DOAJ) que cobrem grande parte do que Google Scholar indexa, com identificadores
estáveis.
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


SERPAPI_API = "https://serpapi.com/search"


class GoogleScholarSerpApiAdapter(PaywallAdapter):
    SOURCE_NAME = "google_scholar"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "SERPAPI_KEY"

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        results_all: list[FetchedItem] = []
        # SerpApi GS retorna ~10 results/page; iteramos com `start` pagination
        page_start = 0
        max_pages = (max_results + 9) // 10  # arredonda para cima
        total_count = None

        for page in range(max_pages):
            params = {
                "engine": "google_scholar",
                "q": query,
                "api_key": api_key,
                "start": page_start,
                "num": 10,
            }
            if year_start:
                params["as_ylo"] = year_start
            if year_end:
                params["as_yhi"] = year_end

            url = f"{SERPAPI_API}?{urllib.parse.urlencode(params)}"
            if throttle > 0:
                time.sleep(throttle)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                            "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                err_msg = f"HTTP {exc.code}: SerpApi ({exc.reason})"
                if exc.code == 401:
                    err_msg += ". Verifique se SERPAPI_KEY é válida."
                elif exc.code == 429:
                    err_msg += ". Quota SerpApi excedida — upgrade do plano necessário."
                if results_all:
                    break  # tinha resultados parciais; aborta paginação mas retorna
                return AdapterResult(
                    source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                    method="KEY_HTTPERROR", query=query, error=err_msg,
                )
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                if results_all:
                    break
                return AdapterResult(
                    source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                    method="KEY_ERROR", query=query, error=str(exc),
                )

            organic = data.get("organic_results", []) or []
            if total_count is None:
                total_count = (data.get("search_information") or {}).get("total_results")

            for org in organic:
                if len(results_all) >= max_results:
                    break
                pub_info = org.get("publication_info") or {}
                summary = pub_info.get("summary", "")
                # Heurística: extrair ano do summary
                year_pub = None
                import re
                m = re.search(r"\b(19\d{2}|20\d{2})\b", summary)
                if m:
                    try:
                        year_pub = int(m.group(1))
                    except ValueError:
                        pass
                authors = []
                if pub_info.get("authors"):
                    authors = [a.get("name", "") for a in pub_info["authors"]]
                # tentar extrair venue do summary
                venue = None
                if " - " in summary:
                    parts = summary.split(" - ")
                    if len(parts) >= 2:
                        venue = parts[1].strip()

                resources = org.get("resources", []) or []
                pdf_url = next((r.get("link") for r in resources
                                if r.get("file_format") == "PDF"), None)

                results_all.append(FetchedItem(
                    title=org.get("title", ""),
                    authors=authors,
                    year=year_pub,
                    doi=None,  # GS não fornece DOI estruturado
                    venue=venue,
                    language="en",
                    is_oa=bool(pdf_url),
                    url=org.get("link"),
                    url_for_pdf=pdf_url,
                    abstract=(org.get("snippet") or "")[:500],
                ))

            if len(organic) < 10 or len(results_all) >= max_results:
                break
            page_start += 10

        # Filtro local Camada 1
        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(results_all)
        log = lf.to_log_camada1(len(results_all), len(kept))

        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REAL", query=query,
            year_start=year_start, year_end=year_end,
            total_results=total_count or len(kept),
            results=[it.to_dict() for it in kept],
            log_camada1=log,
            note=("Google Scholar via SerpApi. Para SR rigorosa, lembre-se que GS não fornece "
                  "DOIs estruturados; cruzar resultados com Crossref/OpenAlex via título "
                  "para obter DOI quando disponível."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Comprehensive review: digital health interventions",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "venue": "JMIR Public Health and Surveillance",
                 "language": "en", "is_oa": True,
                 "url": "https://scholar.google.com/scholar?q=mock001",
                 "url_for_pdf": "https://example.org/mock001.pdf",
                 "abstract": "[mock] Background. Methods. Results. Discussion."},
                {"title": "[mock] Bibliometric analysis of mHealth literature",
                 "authors": ["Mock, C."], "year": 2024,
                 "venue": "Scientometrics",
                 "language": "en", "is_oa": False,
                 "url": "https://scholar.google.com/scholar?q=mock002",
                 "abstract": "[mock] We analyze..."},
            ],
        )


_cli = make_cli(GoogleScholarSerpApiAdapter,
                "Google Scholar via SerpApi (Tier 2; chave paga; cascata).")

if __name__ == "__main__":
    sys.exit(_cli())
