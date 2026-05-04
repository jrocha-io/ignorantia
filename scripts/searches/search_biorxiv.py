#!/usr/bin/env python3
"""
search_biorxiv.py — Adapter para bioRxiv e medRxiv (mesma API api.biorxiv.org).

bioRxiv: ~250k preprints em ciências da vida (Cold Spring Harbor).
medRxiv: ~70k preprints em ciências da saúde (CSH + Yale + BMJ).

Ambos compartilham `api.biorxiv.org`; o servidor é selecionado por path.

Limitação importante: a API pública oficial não tem endpoint de query textual
direta. O endpoint canônico é `/details/{server}/{interval}` retornando paginação
de papers em janela temporal — usuário filtra texto localmente. Para query textual
robusta, EuropePMC indexa preprints de ambos os servidores.

Esta v2.10.2 implementa:
- Modo mock determinístico (igual aos demais).
- Modo real best-effort: chama o endpoint /details com janela temporal e faz
  filtro textual local sobre title/abstract. Não é busca booleana plena.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
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

API = "https://api.biorxiv.org/details"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(server: str, query: str, year_start: int, year_end: int) -> dict:
    return {
        "source": server, "source_tier": "tier1", "method": f"{server.upper()}_MOCK",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": 2,
        "results": [
            {
                "title": f"[mock {server}] Digital health literacy preprint",
                "authors": ["Mock, A.", "Mock, B."], "year": 2023,
                "doi": f"10.1101/2023.{server}-mock-001",
                "venue": server,
                "language": "en", "is_oa": True,
                "url_for_pdf": f"https://www.{server}.org/content/10.1101/2023.{server}-mock-001v1.full.pdf",
                "abstract": "Mock determinístico — fixture de teste.",
                "preprint_server": server,
            },
            {
                "title": f"[mock {server}] Aging and digital tools",
                "authors": ["Mock, C."], "year": 2024,
                "doi": f"10.1101/2024.{server}-mock-002",
                "venue": server,
                "language": "en", "is_oa": True,
                "url_for_pdf": f"https://www.{server}.org/content/10.1101/2024.{server}-mock-002v1.full.pdf",
                "abstract": "Mock determinístico — fixture de teste.",
                "preprint_server": server,
            },
        ],
    }


def _real(server: str, query: str, year_start: int, year_end: int,
          max_results: int, throttle: float, timeout: float,
          max_pages: int = 5) -> dict:
    """Consulta /details/{server}/{from}/{to}/{cursor} e filtra texto localmente."""
    today = date.today().isoformat()
    from_date = f"{year_start}-01-01" if year_start else "2020-01-01"
    to_date = f"{year_end}-12-31" if year_end else today
    if to_date > today:
        to_date = today

    query_lower = query.lower()
    matches = []
    cursor = 0
    total_seen = 0
    error = None
    for page in range(max_pages):
        url = f"{API}/{server}/{from_date}/{to_date}/{cursor}"
        if throttle > 0:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                        "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error = f"HTTP {exc.code}: {exc.reason}"; break
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            error = str(exc); break

        msg = data.get("messages", [{}])[0] if data.get("messages") else {}
        collection = data.get("collection", []) or []
        if not collection:
            break

        for item in collection:
            total_seen += 1
            title = (item.get("title") or "").lower()
            abstract = (item.get("abstract") or "").lower()
            # Filtro local: query precisa aparecer em title OU abstract
            if query_lower in title or query_lower in abstract:
                authors_raw = item.get("authors", "")
                authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
                pub_date = item.get("date", "")
                year_pub = None
                if pub_date:
                    try:
                        year_pub = int(pub_date[:4])
                    except ValueError:
                        pass
                doi = item.get("doi")
                matches.append({
                    "title": item.get("title"),
                    "authors": authors,
                    "year": year_pub,
                    "doi": doi,
                    "venue": server,
                    "language": "en",
                    "is_oa": True,
                    "url_for_pdf": (f"https://www.{server}.org/content/"
                                    f"{doi}v1.full.pdf" if doi else None),
                    "abstract": (item.get("abstract") or "")[:500],
                    "preprint_server": server,
                })
                if len(matches) >= max_results:
                    break
        if len(matches) >= max_results:
            break
        # Paginação: API retorna 100 por página; cursor avança
        try:
            next_total = int(msg.get("total", 0))
        except (ValueError, TypeError):
            next_total = 0
        cursor += len(collection)
        if cursor >= next_total or len(collection) < 100:
            break

    payload = {
        "source": server, "source_tier": "tier1", "method": f"{server.upper()}_REAL",
        "query": query, "year_start": year_start, "year_end": year_end, "year_range": [year_start, year_end],
        "total_results": len(matches),
        "scanned_records": total_seen,
        "results": matches,
        "note": (f"API {server} não tem busca textual nativa; filtro 'query in "
                 f"title|abstract' aplicado localmente sobre {total_seen} registros "
                 f"da janela temporal."),
    }
    if error:
        payload["error"] = error
        payload["method"] = f"{server.upper()}_REAL_PARTIAL"
    return payload


def search(server: str, query: str, year_start: int | None = None,
           year_end: int | None = None, max_results: int = 100,
           mock: bool = False, throttle: float = DEFAULT_THROTTLE,
           timeout: float = DEFAULT_TIMEOUT) -> dict:
    if server not in ("biorxiv", "medrxiv"):
        raise ValueError(f"server inválido: {server!r}; use 'biorxiv' ou 'medrxiv'")
    if mock:
        return _mock(server, query, year_start or 0, year_end or 0)
    return _real(server, query, year_start or 0, year_end or 0, max_results,
                 throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="bioRxiv/medRxiv adapter (Tier 1).")
    p.add_argument("--query", required=True)
    p.add_argument("--server", default="biorxiv", choices=["biorxiv", "medrxiv"])
    p.add_argument("--year-start", type=int); p.add_argument("--year-end", type=int)
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = search(args.server, args.query, args.year_start, args.year_end,
               args.max_results, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("total_results", len(r.get("results", [])))
    print(f"[{args.server}] {n} resultados (de {r.get('scanned_records', '—')} escaneados) → {args.output}")
    return cli_exit_with_error_message(r, "biorxiv")


if __name__ == "__main__":
    sys.exit(_cli())
