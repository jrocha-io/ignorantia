#!/usr/bin/env python3
"""
search_ssrn_full.py — SSRN (Social Science Research Network) full.

SSRN (Elsevier) é o maior repositório de preprints/working papers em ciências sociais,
direito, economia, finanças, contabilidade. ~1.2M papers. Para SR em ciências sociais,
direito, business, é frequentemente cobrado.

Acesso legal:
- KEY: **SSRN não tem API REST pública robusta.** Sem chave de busca textual.
- PROXY: SSRN é parcialmente OA gratuito; mas busca programática ainda exige scraping
  (vedado por DD-6) ou login que SSRN limita.
- FALLBACK_MD: caminho dominante.

Estratégia: descobrir DOIs SSRN via OpenAlex (filter publisher) e gerar fallback `.md`.
Para usuários com login SSRN ativo, full-text é gratuito mas precisa download manual.
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


OPENALEX_API = "https://api.openalex.org/works"


class SSRNFullAdapter(PaywallAdapter):
    SOURCE_NAME = "ssrn_full"
    SOURCE_TIER = "tier2"
    KEY_ENV_VAR = "SSRN_API_KEY"  # nominal; SSRN não tem chave pública

    def _key_search(self, query, year_start, year_end, max_results,
                    api_key, throttle, timeout):
        # Estratégia: OpenAlex filter por host_venue.publisher=Social Science Electronic Publishing
        # SSRN identifier no OpenAlex: S4306400573 (Social Science Research Network)
        params = {
            "search": query,
            "filter": "primary_location.source.id:S4306400573",  # SSRN
            "per-page": min(max_results, 100),
        }
        if year_start and year_end:
            params["filter"] += f",from_publication_date:{year_start}-01-01,to_publication_date:{year_end}-12-31"
        url = f"{OPENALEX_API}?{urllib.parse.urlencode(params)}"
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
                error=f"HTTP {exc.code} on OpenAlex SSRN filter ({exc.reason})",
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return AdapterResult(
                source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
                method="KEY_ERROR", query=query, error=str(exc),
            )

        records = data.get("results", []) or []
        items: list[FetchedItem] = []
        for r in records[:max_results]:
            authorships = r.get("authorships", []) or []
            authors = [(a.get("author") or {}).get("display_name", "")
                       for a in authorships][:10]
            items.append(FetchedItem(
                title=r.get("title", ""),
                authors=authors,
                year=r.get("publication_year"),
                doi=r.get("doi", "").replace("https://doi.org/", "") if r.get("doi") else None,
                venue=(r.get("primary_location") or {}).get("source", {}).get("display_name"),
                language=r.get("language", "en"),
                is_oa=(r.get("open_access") or {}).get("is_oa", False),
                url=r.get("doi") or r.get("id"),
                url_for_pdf=(r.get("primary_location") or {}).get("pdf_url"),
                publication_type=r.get("type"),
            ))

        lf = LocalFilter(year_start, year_end)
        kept = lf.apply(items)
        log = lf.to_log_camada1(len(items), len(kept))

        total = (data.get("meta") or {}).get("count", len(kept))
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="KEY_REAL", query=query,
            year_start=year_start, year_end=year_end,
            total_results=total,
            results=[it.to_dict() for it in kept],
            log_camada1=log,
            note=("SSRN não tem API REST pública. Adapter descobre metadados via OpenAlex "
                  "(source SSRN); full-text gratuito via download manual no SSRN com "
                  "login (criar conta gratuita)."),
        )

    def _mock(self, query, year_start, year_end):
        return AdapterResult(
            source=self.SOURCE_NAME, source_tier=self.SOURCE_TIER,
            method="MOCK", query=query,
            year_start=year_start, year_end=year_end,
            total_results=2,
            results=[
                {"title": "[mock] Working paper on financial market regulation (SSRN)",
                 "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                 "doi": "10.2139/ssrn.MOCK001",
                 "venue": "SSRN Working Paper Series",
                 "language": "en", "is_oa": True,
                 "url": "https://ssrn.com/abstract=MOCK001",
                 "publication_type": "preprint"},
                {"title": "[mock] Legal analysis of digital privacy (SSRN)",
                 "authors": ["Mock, C."], "year": 2024,
                 "doi": "10.2139/ssrn.MOCK002",
                 "venue": "SSRN Working Paper Series",
                 "language": "en", "is_oa": True,
                 "url": "https://ssrn.com/abstract=MOCK002",
                 "publication_type": "preprint"},
            ],
        )


_cli = make_cli(SSRNFullAdapter,
                "SSRN full adapter (Tier 2; descoberta via OpenAlex; full-text via download manual).")

if __name__ == "__main__":
    sys.exit(_cli())
