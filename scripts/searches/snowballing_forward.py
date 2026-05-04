#!/usr/bin/env python3
"""
snowballing_forward.py — Snowballing forward (citações posteriores) via OpenAlex.

Wohlin (2014) §2.2: "Forward snowballing means using a citation database to identify
new papers that cite a paper of interest." Complemento ao backward snowballing —
captura literatura mais recente que cita os seeds.

Implementação:
1. Para cada DOI seed, consulta OpenAlex `/works/{doi}/cited-by` para obter trabalhos
   que citam o seed.
2. Filtra por janela temporal (year_start, year_end).
3. Deduplica contra corpus já incluído + candidatos do backward.
4. Retorna candidatos para retornar ao screening (Fase 4).

OpenAlex é a única fonte gratuita robusta de "cited by" — Crossref tem `is-referenced-by`
mas a cobertura é menor. Sem dependências pesadas.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

OPENALEX_API = "https://api.openalex.org/works"
USER_AGENT = "ignorantia-skill/2.10.0"
DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


@dataclass
class ForwardSnowballingResult:
    seed_dois: list[str] = field(default_factory=list)
    n_seeds: int = 0
    n_citations_found: int = 0
    n_unique_candidates: int = 0
    n_already_in_corpus: int = 0
    candidates: list[dict] = field(default_factory=list)
    errors_per_seed: dict[str, str] = field(default_factory=dict)


def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return d if "/" in d else None


def _fetch_citing_works(doi: str, year_start: int | None, year_end: int | None,
                        contact_email: str | None,
                        throttle: float, timeout: float,
                        per_page: int = 100, max_pages: int = 5) -> tuple[list[dict], str | None]:
    """Recupera works que citam um DOI via OpenAlex /cited-by.

    OpenAlex usa filter `cites:W<id>` para "cited by". Para usar com DOI, primeiro
    resolvemos o DOI para OpenAlex Work ID e depois buscamos works que citam.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if contact_email:
        headers["User-Agent"] = f"{USER_AGENT} (mailto:{contact_email})"

    # 1) Resolver DOI para Work ID
    resolve_url = f"{OPENALEX_API}/https://doi.org/{doi}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(resolve_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            seed_work = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return [], f"resolve DOI error: {exc}"
    seed_id = seed_work.get("id")  # ex: "https://openalex.org/W2741809807"
    if not seed_id:
        return [], "DOI não resolvido para Work ID OpenAlex"
    work_id_short = seed_id.rstrip("/").split("/")[-1]

    # 2) Buscar works que citam o seed
    citing_works = []
    cursor = "*"
    for page_n in range(max_pages):
        params = {
            "filter": f"cites:{work_id_short}",
            "per-page": per_page,
            "cursor": cursor,
        }
        if year_start and year_end:
            params["filter"] = (params["filter"] +
                                f",publication_year:{year_start}-{year_end}")
        url = f"{OPENALEX_API}?{urllib.parse.urlencode(params)}"
        if throttle > 0:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            return citing_works, f"page {page_n} error: {exc}"
        results = data.get("results", []) or []
        for w in results:
            citing_works.append({
                "openalex_id": w.get("id"),
                "doi": _normalize_doi(w.get("doi")),
                "title": w.get("title") or w.get("display_name"),
                "year": w.get("publication_year"),
                "venue": (w.get("primary_location") or {}).get("source", {}).get("display_name"),
                "authors": [a.get("author", {}).get("display_name")
                            for a in (w.get("authorships") or [])
                            if a.get("author")][:5],
            })
        # paginação
        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not next_cursor or len(results) < per_page:
            break
        cursor = next_cursor
    return citing_works, None


def snowball_forward(seed_dois: list[str],
                     already_included_dois: list[str] | None = None,
                     year_start: int | None = None,
                     year_end: int | None = None,
                     contact_email: str | None = None,
                     mock: bool = False,
                     throttle: float = DEFAULT_THROTTLE,
                     timeout: float = DEFAULT_TIMEOUT) -> ForwardSnowballingResult:
    """Executa snowballing forward sobre lista de seeds."""
    result = ForwardSnowballingResult()
    seed_dois_norm = [_normalize_doi(d) for d in seed_dois if _normalize_doi(d)]
    result.seed_dois = seed_dois_norm
    result.n_seeds = len(seed_dois_norm)
    already = set(_normalize_doi(d) or "" for d in (already_included_dois or []))
    already.update(seed_dois_norm)

    if mock:
        result.candidates = [
            {"doi": "10.0000/snowball-fwd-mock-001",
             "title": "[mock] Recent paper that cites a seed",
             "year": 2025, "from_seed": seed_dois_norm[0] if seed_dois_norm else "?",
             "origin": "forward_snowballing"},
        ]
        result.n_citations_found = 3
        result.n_unique_candidates = 1
        result.n_already_in_corpus = 2
        return result

    seen: dict[str, dict] = {}
    for seed in seed_dois_norm:
        works, error = _fetch_citing_works(
            seed, year_start, year_end, contact_email, throttle, timeout
        )
        if error:
            result.errors_per_seed[seed] = error
        result.n_citations_found += len(works)
        for w in works:
            doi = w.get("doi")
            if not doi:
                # Sem DOI, usar OpenAlex ID como chave
                openalex_id = w.get("openalex_id")
                if not openalex_id or openalex_id in seen:
                    continue
                seen[openalex_id] = {**w, "from_seed": seed, "origin": "forward_snowballing"}
                continue
            if doi in already:
                result.n_already_in_corpus += 1
                continue
            if doi in seen:
                continue
            seen[doi] = {**w, "from_seed": seed, "origin": "forward_snowballing"}
    result.candidates = list(seen.values())
    result.n_unique_candidates = len(result.candidates)
    return result


def _cli() -> int:
    p = argparse.ArgumentParser(description="Snowballing forward (Wohlin 2014) via OpenAlex.")
    p.add_argument("--seeds-file", required=True)
    p.add_argument("--corpus-file", default=None)
    p.add_argument("--year-start", type=int, default=None)
    p.add_argument("--year-end", type=int, default=None)
    p.add_argument("--contact-email", default=None)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    seeds = [ln.strip() for ln in Path(args.seeds_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    corpus = []
    if args.corpus_file and Path(args.corpus_file).exists():
        corpus = [ln.strip() for ln in Path(args.corpus_file).read_text(encoding="utf-8").splitlines() if ln.strip()]

    result = snowball_forward(
        seeds, corpus, args.year_start, args.year_end,
        contact_email=args.contact_email, mock=args.mock,
    )
    payload = {
        "schema_version": "1.0.0",
        "method": "WOHLIN_2014_FORWARD_VIA_OPENALEX",
        "n_seeds": result.n_seeds,
        "n_citations_found": result.n_citations_found,
        "n_unique_candidates": result.n_unique_candidates,
        "n_already_in_corpus": result.n_already_in_corpus,
        "candidates": result.candidates,
        "errors_per_seed": result.errors_per_seed,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[snowballing_forward] {result.n_seeds} seeds → "
          f"{result.n_unique_candidates} candidatos novos (de {result.n_citations_found} citações; "
          f"{result.n_already_in_corpus} já no corpus) → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
