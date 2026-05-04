#!/usr/bin/env python3
"""
search_clinicaltrials_gov.py — Registro oficial NIH de ensaios clínicos.

ClinicalTrials.gov é o registro principal de ensaios clínicos do NIH/NLM. ~470k
estudos cadastrados. **PRISMA-2020 item 6 cita o registro de ensaios como obrigatório**
para identificar estudos em andamento e detectar viés de publicação (estudos
registrados mas não publicados).

API: https://clinicaltrials.gov/data-api (REST v2 em produção).
Endpoint: GET /api/v2/studies?query.term=...&pageSize=...
Sem chave; rate limit responsável.

Para SR e meta-análise de saúde, este registro é **complementar à busca em journals**:
- Identifica ensaios em curso (não publicados ainda) → seção "ongoing studies".
- Detecta viés de publicação (registrados, completados, sem publicação após N anos).
- Provê dados primários quando disponíveis (após 2017 — FDAAA mandate).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _adapter_base import cli_exit_with_error_message
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

API = "https://clinicaltrials.gov/api/v2/studies"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": "clinicaltrials_gov", "source_tier": "tier1",
        "method": "CTGOV_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": "[mock] RCT: digital literacy intervention for older adults",
                "nct_id": "NCT00000001",
                "year_start": 2022, "year_completion": 2024,
                "status": "Completed",
                "phase": "N/A",
                "study_type": "Interventional",
                "enrollment": 240,
                "sponsor": "[mock] University Hospital",
                "country": "BR",
                "url": "https://clinicaltrials.gov/study/NCT00000001",
                "has_results": True,
                "language": "en",
            },
            {
                "title": "[mock] mHealth literacy training trial",
                "nct_id": "NCT00000002",
                "year_start": 2023, "year_completion": 2025,
                "status": "Recruiting",
                "phase": "N/A",
                "study_type": "Interventional",
                "enrollment": 180,
                "sponsor": "[mock] Federal University",
                "country": "BR",
                "url": "https://clinicaltrials.gov/study/NCT00000002",
                "has_results": False,
                "language": "en",
            },
        ],
    }


def _real(query: str, year_start: int, year_end: int, max_results: int,
          throttle: float, timeout: float) -> dict:
    # CT.gov v2 API; sintaxe específica
    params = {
        "query.term": query,
        "pageSize": min(max_results, 100),
        "format": "json",
        "fields": ("NCTId,BriefTitle,StartDate,CompletionDate,OverallStatus,Phase,"
                   "StudyType,EnrollmentCount,LeadSponsorName,LocationCountry,"
                   "HasResults"),
    }
    if year_start and year_end:
        # Filter por StartDate (campo da API CT.gov)
        params["filter.advanced"] = (
            f"AREA[StartDate]RANGE[{year_start}-01-01,{year_end}-12-31]"
        )
    url = f"{API}?{urllib.parse.urlencode(params)}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for study in (data.get("studies") or [])[:max_results]:
            ps = study.get("protocolSection", {}) or {}
            ident = ps.get("identificationModule", {}) or {}
            status = ps.get("statusModule", {}) or {}
            design = ps.get("designModule", {}) or {}
            sponsor = ps.get("sponsorCollaboratorsModule", {}) or {}
            contacts = ps.get("contactsLocationsModule", {}) or {}

            start_date = (status.get("startDateStruct") or {}).get("date", "")
            completion_date = (status.get("completionDateStruct") or {}).get("date", "")
            year_s = None
            year_c = None
            if start_date:
                try:
                    year_s = int(start_date[:4])
                except ValueError:
                    pass
            if completion_date:
                try:
                    year_c = int(completion_date[:4])
                except ValueError:
                    pass
            phases = design.get("phases", [])
            phase = phases[0] if phases else None
            countries = []
            for loc in (contacts.get("locations") or []):
                c = loc.get("country")
                if c and c not in countries:
                    countries.append(c)
            results.append({
                "title": ident.get("briefTitle"),
                "nct_id": ident.get("nctId"),
                "year_start": year_s,
                "year_completion": year_c,
                "status": status.get("overallStatus"),
                "phase": phase,
                "study_type": design.get("studyType"),
                "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
                "sponsor": (sponsor.get("leadSponsor") or {}).get("name"),
                "country": countries[0] if countries else None,
                "all_countries": countries,
                "url": f"https://clinicaltrials.gov/study/{ident.get('nctId', '')}",
                "has_results": (study.get("hasResults") or False),
                "language": "en",
            })
        total = data.get("totalCount", len(results))
        return {
            "source": "clinicaltrials_gov", "source_tier": "tier1",
            "method": "CTGOV_REAL",
            "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
            "total_results": total,
            "results": results,
        }
    except urllib.error.HTTPError as exc:
        return {"source": "clinicaltrials_gov", "source_tier": "tier1",
                "method": "CTGOV_REAL_HTTPERROR",
                "error": f"HTTP {exc.code}: {exc.reason}", "query": query, "results": []}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"source": "clinicaltrials_gov", "source_tier": "tier1",
                "method": "CTGOV_REAL_ERROR", "error": str(exc), "query": query, "results": []}


def search(query: str, year_start: int | None = None, year_end: int | None = None,
           max_results: int = 100, mock: bool = False,
           throttle: float = DEFAULT_THROTTLE, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if mock:
        return _mock(query, year_start or 0, year_end or 0)
    return _real(query, year_start or 0, year_end or 0, max_results, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="ClinicalTrials.gov adapter (Tier 1; PRISMA-2020 item 6).")
    p.add_argument("--query", required=True)
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.query, args.year_start, args.year_end, args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[clinicaltrials_gov] {n} resultados → {args.output}")
    return cli_exit_with_error_message(r, "clinicaltrials_gov")


if __name__ == "__main__":
    sys.exit(_cli())
