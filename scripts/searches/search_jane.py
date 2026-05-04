#!/usr/bin/env python3
"""
search_jane.py — JANE (Journal/Author Name Estimator).

JANE não é base de busca — é **classificador de venue para submissão**. Recebe
título + abstract e retorna ranking de journals candidatos baseado em similaridade
(MEDLINE-trained model). Útil para Fase 8 do skill (sugestão de 3-5 venues).

Endpoint público: https://jane.biosemantics.org/suggestions.php
Sem API REST oficial — usa POST form com texto. Esta v2.11.0 implementa estratégia
best-effort + modo mock.

NÃO entra em TIER1_RUNNERS — é utilitário de Fase 8, não de busca de literatura.
Adapter declara explicitamente.
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

API = "https://jane.biosemantics.org/suggestions.php"

DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


def _mock(text: str) -> dict:
    return {
        "source": "jane", "source_tier": "venue_classifier",
        "method": "JANE_MOCK",
        "text_length": len(text),
        "n_journal_suggestions": 3,
        "results": [
            {"venue": "Journal of Medical Internet Research",
             "score": 0.87, "ranking": 1,
             "venue_url": "https://www.jmir.org/", "venue_issn": "1438-8871",
             "estimated_jcr_quartile": "Q1", "is_oa": True},
            {"venue": "Patient Education and Counseling",
             "score": 0.74, "ranking": 2,
             "venue_url": "https://www.journals.elsevier.com/patient-education-and-counseling",
             "venue_issn": "0738-3991",
             "estimated_jcr_quartile": "Q1", "is_oa": False},
            {"venue": "BMC Health Services Research",
             "score": 0.69, "ranking": 3,
             "venue_url": "https://bmchealthservres.biomedcentral.com/",
             "venue_issn": "1472-6963",
             "estimated_jcr_quartile": "Q2", "is_oa": True},
        ],
    }


def _real(text: str, max_suggestions: int, throttle: float, timeout: float) -> dict:
    data = urllib.parse.urlencode({
        "text": text,
        "languageCode": "en",
        "typeOfDocument": "Editorials",
    }).encode("utf-8")
    if throttle > 0:
        time.sleep(throttle)
    try:
        req = urllib.request.Request(
            API,
            data=data,
            headers={"User-Agent": USER_AGENT,
                     "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {
            "source": "jane", "source_tier": "venue_classifier",
            "method": "JANE_REAL_PARTIAL",
            "text_length": len(text), "raw_size_bytes": len(raw),
            "results": [],
            "note": ("JANE retornou HTML; parser detalhado é TODO. "
                     "Endpoint público sem API REST estruturada. Para integração robusta, "
                     "considere implementar parser específico para a tabela de suggestions "
                     "da página de resultados."),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"source": "jane", "source_tier": "venue_classifier",
                "method": "JANE_REAL_ERROR",
                "error": str(exc), "results": []}


def suggest_venues(text: str, max_suggestions: int = 10, mock: bool = False,
                   throttle: float = DEFAULT_THROTTLE,
                   timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Sugere venues para submissão dado um título + abstract.

    Args:
        text: combinação de título + abstract do paper.
    """
    if mock:
        return _mock(text)
    return _real(text, max_suggestions, throttle, timeout)


def _cli() -> int:
    p = argparse.ArgumentParser(description="JANE venue classifier (Phase 8 utility).")
    p.add_argument("--text", required=True,
                   help="Título + abstract do paper para classificação.")
    p.add_argument("--max-suggestions", type=int, default=10)
    p.add_argument("--mock", action="store_true"); p.add_argument("--output", required=True)
    args = p.parse_args()
    r = suggest_venues(args.text, args.max_suggestions, mock=args.mock)
    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    n = r.get("n_journal_suggestions", len(r.get("results", [])))
    print(f"[jane] {n} sugestões de venue → {args.output}")
    return cli_exit_with_error_message(r, "jane")


if __name__ == "__main__":
    sys.exit(_cli())
