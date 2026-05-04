#!/usr/bin/env python3
"""
snowballing_backward.py — Snowballing backward obrigatório (Wohlin 2014).

Conforme Decisão 23 (v2.9.0): snowballing backward DEVE ser conduzido a partir dos
estudos seed identificados na Fase 5 (extração). O método de Wohlin (2014) define:

    "Backward snowballing means using the reference list of a paper to identify
    new papers to be included."   — Wohlin (2014), EASE'14, §2.1

Este módulo:
1. Recebe lista de DOIs seed (estudos centrais já incluídos).
2. Para cada DOI, recupera referências citadas via Crossref (ou OpenAlex como fallback).
3. Deduplica contra o corpus já incluído.
4. Retorna lista de candidatos novos para triagem (com mesmo critério de inclusão/exclusão).
5. Marca origem como "backward_snowballing" no manifest.

Os candidatos retornam ao pipeline de screening (Fase 4) automaticamente — não há
"snowballing optional" porque o critério antigo "(Polimento) Snowballing não conduzido"
foi removido da rubrica e elevado a obrigação (Decisão 23, registrado em v2.9.0).
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
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION}"

CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


@dataclass
class SnowballingResult:
    """Resultado consolidado do snowballing backward sobre um corpus seed."""
    seed_dois: list[str] = field(default_factory=list)
    n_seeds: int = 0
    n_references_found: int = 0
    n_unique_candidates: int = 0
    n_already_in_corpus: int = 0
    candidates: list[dict] = field(default_factory=list)
    errors_per_seed: dict[str, str] = field(default_factory=dict)


def _fetch_references_crossref(doi: str, throttle: float, timeout: float,
                                contact_email: str | None) -> tuple[list[dict], str | None]:
    """Recupera referências citadas via Crossref API."""
    headers = {"User-Agent": USER_AGENT}
    if contact_email:
        headers["User-Agent"] = f"{USER_AGENT} (mailto:{contact_email})"
    url = f"{CROSSREF_API}/{urllib.parse.quote(doi, safe='/:')}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data.get("message", {})
        refs = msg.get("reference", []) or []
        out = []
        for r in refs:
            ref_doi = r.get("DOI")
            out.append({
                "doi": ref_doi.lower().strip() if ref_doi else None,
                "title": (r.get("article-title") or r.get("volume-title") or
                          r.get("unstructured", "")[:200]),
                "year": r.get("year"),
                "venue": r.get("journal-title") or r.get("series-title"),
                "authors": [r.get("author")] if r.get("author") else [],
                "raw": r,
            })
        return out, None
    except urllib.error.HTTPError as exc:
        return [], f"Crossref HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return [], f"Crossref error: {exc}"


def _fetch_references_openalex(doi: str, throttle: float, timeout: float) -> tuple[list[dict], str | None]:
    """Fallback: recupera referências via OpenAlex (referenced_works)."""
    headers = {"User-Agent": USER_AGENT}
    url = f"{OPENALEX_API}/https://doi.org/{doi}"
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ref_works = data.get("referenced_works", []) or []
        # OpenAlex retorna IDs de work; cada um precisaria de fetch individual.
        # Para v2.9.0 retornamos só IDs; resolução completa é TODO ou reutiliza
        # search_unpaywall/Crossref na próxima passada do pipeline.
        out = [{"openalex_id": w_id, "doi": None, "title": None,
                "year": None, "raw": {"referenced_via_openalex": True}}
               for w_id in ref_works]
        return out, None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return [], f"OpenAlex error: {exc}"


def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return d if "/" in d else None


def snowball_backward(seed_dois: list[str],
                      already_included_dois: list[str] | None = None,
                      contact_email: str | None = None,
                      mock: bool = False,
                      throttle: float = DEFAULT_THROTTLE,
                      timeout: float = DEFAULT_TIMEOUT) -> SnowballingResult:
    """Executa snowballing backward sobre lista de seeds.

    Args:
        seed_dois: lista de DOIs dos estudos seed (Wohlin 2014).
        already_included_dois: DOIs já no corpus para deduplicação.
        contact_email: email de contato para Crossref polite pool.
        mock: se True, retorna fixture determinística para CI.

    Returns:
        SnowballingResult com candidatos novos, marcados para retornar ao screening.
    """
    result = SnowballingResult()
    seed_dois_norm = [_normalize_doi(d) for d in seed_dois if _normalize_doi(d)]
    result.seed_dois = seed_dois_norm
    result.n_seeds = len(seed_dois_norm)
    already = set(_normalize_doi(d) or "" for d in (already_included_dois or []))
    already.update(seed_dois_norm)  # seeds não devem virar candidatos a si próprios

    if mock:
        result.candidates = [
            {"doi": "10.0000/snowball-mock-ref-001",
             "title": "[mock] Foundational reference cited by seeds",
             "year": 2018, "from_seed": seed_dois_norm[0] if seed_dois_norm else "?",
             "origin": "backward_snowballing"},
            {"doi": "10.0000/snowball-mock-ref-002",
             "title": "[mock] Cross-cited reference from multiple seeds",
             "year": 2019, "from_seed": "multiple", "origin": "backward_snowballing"},
        ]
        result.n_references_found = 5
        result.n_unique_candidates = 2
        result.n_already_in_corpus = 3
        return result

    seen: dict[str, dict] = {}
    for seed in seed_dois_norm:
        refs, error = _fetch_references_crossref(seed, throttle, timeout, contact_email)
        if error and not refs:
            # Fallback OpenAlex
            refs_fb, error_fb = _fetch_references_openalex(seed, throttle, timeout)
            if refs_fb:
                refs = refs_fb
                error = None
            else:
                error = f"{error}; fallback {error_fb}"
        if error:
            result.errors_per_seed[seed] = error
            continue
        result.n_references_found += len(refs)
        for ref in refs:
            doi = _normalize_doi(ref.get("doi"))
            if not doi:
                continue
            if doi in already:
                result.n_already_in_corpus += 1
                continue
            if doi in seen:
                continue
            seen[doi] = {
                "doi": doi,
                "title": ref.get("title"),
                "year": ref.get("year"),
                "venue": ref.get("venue"),
                "authors": ref.get("authors", []),
                "from_seed": seed,
                "origin": "backward_snowballing",
            }
    result.candidates = list(seen.values())
    result.n_unique_candidates = len(result.candidates)
    return result


def _cli() -> int:
    p = argparse.ArgumentParser(description="Backward snowballing (Wohlin 2014) — obrigatório (Decisão 23).")
    p.add_argument("--seeds-file", required=True,
                   help="Arquivo com 1 DOI por linha (DOIs dos estudos seed).")
    p.add_argument("--corpus-file", default=None,
                   help="Arquivo com DOIs já no corpus (para deduplicação).")
    p.add_argument("--contact-email", default=None)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    seeds = [ln.strip() for ln in Path(args.seeds_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    corpus = []
    if args.corpus_file and Path(args.corpus_file).exists():
        corpus = [ln.strip() for ln in Path(args.corpus_file).read_text(encoding="utf-8").splitlines() if ln.strip()]

    result = snowball_backward(seeds, corpus, contact_email=args.contact_email, mock=args.mock)
    payload = {
        "schema_version": "1.0.0",
        "method": "WOHLIN_2014_BACKWARD",
        "n_seeds": result.n_seeds,
        "n_references_found": result.n_references_found,
        "n_unique_candidates": result.n_unique_candidates,
        "n_already_in_corpus": result.n_already_in_corpus,
        "candidates": result.candidates,
        "errors_per_seed": result.errors_per_seed,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[snowballing_backward] {result.n_seeds} seeds → "
          f"{result.n_unique_candidates} candidatos novos (de {result.n_references_found} refs encontradas; "
          f"{result.n_already_in_corpus} já no corpus) → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
