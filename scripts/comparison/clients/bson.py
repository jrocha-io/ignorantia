"""Cliente B!SON (TIB Hannover + SLUB Dresden) — único journal recommender com API REST aberta.

Categoria 1 do mapeamento de baselines (Etapa 4b). Cobertura editorial: ~18.000 journals OA
indexados em DOAJ. Para venues não-OA dos 68 perfis YAML do `ignorantia`, B!SON é silente.

API: https://service.tib.eu/bison/api/
Docs: https://service.tib.eu/bison/api/schema/swagger
Sem chave de autenticação. Rate limit não publicado — usamos ≤1 req/s + User-Agent identificável.

Modos:
- `real`: chama API live (requer internet)
- `mock`: retorna fixture canônica (default em testes/CI)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

USER_AGENT = "ignorantia-eval/2.5.0 (https://github.com/ignorantia)"
BSON_BASE_URL = "https://service.tib.eu/bison/api"
DEFAULT_THROTTLE_SECONDS = 1.0


@dataclass
class BsonResult:
    """Resultado de uma chamada B!SON."""
    venue_ranking: list[dict[str, Any]] = field(default_factory=list)
    method: str = "BSON_REST_API"
    snapshot: bool = False
    snapshot_date: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None


def _mock_response(title: str, abstract: str, references: list[dict]) -> BsonResult:
    """Fixture determinística — usada em CI/smoke tests sem internet.

    Construção: top-5 journals OA conhecidos, com scores decrescentes coerentes.
    """
    return BsonResult(
        venue_ranking=[
            {"venue_name": "PLOS ONE", "issn": "1932-6203", "score": 0.87,
             "license": "CC-BY", "apc_usd": 1805, "plan_s_compliance": True},
            {"venue_name": "PeerJ", "issn": "2167-8359", "score": 0.74,
             "license": "CC-BY", "apc_usd": 1395, "plan_s_compliance": True},
            {"venue_name": "F1000Research", "issn": "2046-1402", "score": 0.71,
             "license": "CC-BY", "apc_usd": 1250, "plan_s_compliance": True},
            {"venue_name": "Frontiers in Education", "issn": "2504-284X", "score": 0.62,
             "license": "CC-BY", "apc_usd": 2200, "plan_s_compliance": True},
            {"venue_name": "Cogent Education", "issn": "2331-186X", "score": 0.58,
             "license": "CC-BY", "apc_usd": 1620, "plan_s_compliance": True},
        ],
        method="BSON_REST_API_MOCK",
        snapshot=False,
        raw_response={"_mock_seed": "v2.5.0", "_input_title": title[:60], "_n_refs": len(references)},
    )


def _real_request(title: str, abstract: str, references: list[dict],
                  timeout_seconds: float = 30.0) -> BsonResult:
    """Chama API B!SON live. Tolerante a falha — encapsula erros em BsonResult.error."""
    try:
        import requests  # noqa: F401  (lazy import)
    except ImportError:
        return BsonResult(error="requests package not available; install with `pip install requests`",
                          method="BSON_REST_API_REAL_UNAVAILABLE")

    import requests as _rq

    payload = {
        "title": title,
        "abstract": abstract,
        "references": [r["doi"] for r in references if "doi" in r],
    }
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    # Endpoint canonical: /recommendation/ (pode mudar; verificar Swagger antes de produção).
    url = f"{BSON_BASE_URL}/recommendation/"
    try:
        resp = _rq.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        return BsonResult(
            venue_ranking=_normalize_bson_response(data),
            method="BSON_REST_API_REAL",
            raw_response=data,
        )
    except _rq.HTTPError as exc:
        return BsonResult(error=f"BSON HTTPError: {exc}; status={resp.status_code}",
                          method="BSON_REST_API_REAL_HTTPERROR",
                          raw_response={"status_code": resp.status_code})
    except _rq.RequestException as exc:
        return BsonResult(error=f"BSON RequestException: {exc}",
                          method="BSON_REST_API_REAL_NETERROR")
    except (ValueError, KeyError) as exc:
        return BsonResult(error=f"BSON parse error: {exc}",
                          method="BSON_REST_API_REAL_PARSEERROR")


def _normalize_bson_response(data: dict) -> list[dict[str, Any]]:
    """Normaliza resposta B!SON para schema unificado venue_ranking[].

    Tolerante a mudanças de schema: tenta múltiplos field paths conhecidos.
    Se nenhum coincidir, retorna lista vazia + raw_response preservada para debug.
    """
    candidates = data.get("results") or data.get("journals") or data.get("recommendations") or []
    out = []
    for i, item in enumerate(candidates):
        if not isinstance(item, dict):
            continue
        out.append({
            "venue_name": item.get("name") or item.get("title") or item.get("journal", "?"),
            "issn": item.get("issn_l") or item.get("issn") or item.get("eissn"),
            "score": float(item.get("score", item.get("similarity", 0.0))),
            "license": item.get("license"),
            "apc_usd": item.get("apc_usd") or item.get("apc"),
            "plan_s_compliance": item.get("plan_s_compliance", False),
            "rank": i + 1,
        })
    return out


def query(title: str, abstract: str, references: list[dict] | None = None,
          mock: bool = True, throttle: float = DEFAULT_THROTTLE_SECONDS) -> BsonResult:
    """Interface pública. Default `mock=True` para segurança em CI.

    Mock retorna fixture determinística; real chama API B!SON.
    """
    references = references or []
    if mock:
        return _mock_response(title, abstract, references)
    if throttle > 0:
        time.sleep(throttle)
    return _real_request(title, abstract, references)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="B!SON cliente para Etapa 4b da `ignorantia`.")
    parser.add_argument("--input", required=True, help="Caminho para manuscript JSON (manuscript_input.schema.json).")
    parser.add_argument("--out", required=True, help="Caminho para output JSON.")
    parser.add_argument("--mock", action="store_true", help="Modo mock — usa fixture determinística (default em CI).")
    parser.add_argument("--throttle", type=float, default=DEFAULT_THROTTLE_SECONDS)
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[bson] input not found: {in_path}", file=sys.stderr)
        return 2
    ms = json.loads(in_path.read_text(encoding="utf-8"))
    title = ms.get("title", "")
    abstract = ms.get("abstract", "")
    references = ms.get("references", [])

    result = query(title=title, abstract=abstract, references=references,
                   mock=args.mock, throttle=args.throttle)
    out = asdict(result)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    if result.error:
        print(f"[bson] WARNING: {result.error}", file=sys.stderr)
        return 1
    print(f"[bson] {len(result.venue_ranking)} venues ranked → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
