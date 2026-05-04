"""Cliente JANE (Journal/Author Name Estimator, Erasmus MC) — categoria 1.

STATUS: SCAFFOLD. JANE não tem API REST pública estável. Acesso real requer:
1. Self-host via repo `mi-erasmusmc/JANE` (Java/PHP), com índice Lucene baseado em PubMed.
2. OU contato direto com Martijn Schuemie (autor original).

Este módulo implementa apenas mock determinístico + interface estável. Quando o self-host
estiver disponível, basta substituir _real_request() pela chamada SOAP/HTTP correspondente.

Cobertura editorial: PubMed (viés biomédico).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class JaneResult:
    venue_ranking: list[dict[str, Any]] = field(default_factory=list)
    method: str = "JANE_SCAFFOLD"
    snapshot: bool = False
    error: str | None = None


def _mock_response(title: str, abstract: str) -> JaneResult:
    """Mock baseado em padrão biomédico/clínico — viés PubMed."""
    biomed_keywords = ["health", "patient", "clinical", "medical", "nursing", "saúde",
                       "enfermagem", "medical", "disease", "treatment", "therapy"]
    text = (title + " " + abstract).lower()
    is_biomed = any(kw in text for kw in biomed_keywords)
    if is_biomed:
        ranking = [
            {"venue_name": "BMJ Open", "issn": "2044-6055", "confidence": 0.81,
             "medline_indexed": True, "doaj_indexed": True},
            {"venue_name": "PLOS ONE", "issn": "1932-6203", "confidence": 0.74,
             "medline_indexed": True, "doaj_indexed": True},
            {"venue_name": "BMC Medical Education", "issn": "1472-6920", "confidence": 0.69,
             "medline_indexed": True, "doaj_indexed": True},
            {"venue_name": "Revista Latino-Americana de Enfermagem", "issn": "1518-8345",
             "confidence": 0.61, "medline_indexed": True, "doaj_indexed": True},
        ]
    else:
        ranking = [
            {"venue_name": "PLOS ONE", "issn": "1932-6203", "confidence": 0.55,
             "medline_indexed": True, "doaj_indexed": True},
        ]
    for i, r in enumerate(ranking):
        r["rank"] = i + 1
    return JaneResult(venue_ranking=ranking, method="JANE_SCAFFOLD_MOCK")


def _real_request(title: str, abstract: str) -> JaneResult:
    """TODO: substituir por chamada SOAP/HTTP ao JANE self-host quando disponível.

    Plano de implementação:
    1. Build container Docker com `mi-erasmusmc/JANE` + índice Lucene MEDLINE.
    2. Expor JaneServer SOAP em http://localhost:8080.
    3. Substituir esta função por cliente SOAP (e.g., zeep.Client).
    """
    return JaneResult(
        method="JANE_SCAFFOLD_NOT_IMPLEMENTED",
        error="JANE self-host não implementado; rode com --mock ou aguarde implementação real.",
    )


def query(title: str, abstract: str, mock: bool = True) -> JaneResult:
    if mock:
        return _mock_response(title, abstract)
    return _real_request(title, abstract)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="JANE cliente (scaffold) para Etapa 4b.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    ms = json.loads(Path(args.input).read_text(encoding="utf-8"))
    res = query(ms.get("title", ""), ms.get("abstract", ""), mock=args.mock)
    Path(args.out).write_text(json.dumps(asdict(res), indent=2, ensure_ascii=False), encoding="utf-8")
    if res.error:
        print(f"[jane] {res.error}", file=sys.stderr)
        return 1
    print(f"[jane] {len(res.venue_ranking)} venues ranked → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
