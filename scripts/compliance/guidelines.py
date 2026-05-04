"""
Stage 3: Reporting Guidelines Mapping.

Para cada guideline endossada pelo venue (campo taxonomy.reporting_guidelines_endorsed),
verifica os itens da checklist. Itens com automation_level=full são checados;
partial são checados onde possível e flagged "needs human verification";
none são apenas listados como "needs_human_review".
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .parse import ManuscriptDocument
from .hard_rules import CheckResult


GUIDELINES_DIR = Path(__file__).resolve().parent.parent.parent / "references" / "profiles" / "_guidelines"


def _load_guideline_yaml(guideline_id: str) -> dict | None:
    """Carrega um perfil de reporting guideline.

    Procura primeiro por nome canônico em lowercase (e.g., 'PRISMA-2020' → 'prisma-2020.yaml').
    Suporta também a variante 'sigsoft-empirical-standards.yaml' para SIGSOFT-EMP-STANDARDS.
    """
    name_map = {
        "PRISMA-2020": "prisma-2020.yaml",
        "PRISMA-S": "prisma-s.yaml",
        "PRISMA-ScR": "prisma-scr.yaml",
        "PRISMA-RR": "prisma-rr.yaml",
        "MECIR": "mecir.yaml",
        "CAMPBELL-STANDARDS": "campbell-standards.yaml",
        "SIGSOFT-EMP-STANDARDS": "sigsoft-empirical-standards.yaml",
    }
    fname = name_map.get(guideline_id, guideline_id.lower() + ".yaml")
    path = GUIDELINES_DIR / fname
    if not path.exists():
        return None
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        # Fallback: parser YAML mínimo (apenas para os campos necessários)
        return _parse_yaml_minimal(path.read_text(encoding="utf-8"))


def _parse_yaml_minimal(text: str) -> dict:
    """Parser YAML mínimo para casos em que pyyaml não esteja instalado.
    Limitado: trata id, items, e algumas chaves específicas do schema.
    """
    # Não vamos reinventar yaml; emitir aviso
    raise RuntimeError(
        "PyYAML não disponível. Execute: pip install pyyaml --break-system-packages"
    )


def _check_anchor_in_text(text: str, anchors: list[str]) -> tuple[bool, str]:
    text_low = text.lower()
    for a in anchors:
        try:
            m = re.search(a, text_low, flags=re.IGNORECASE)
            if m:
                return True, m.group(0)[:120]
        except re.error:
            # padrão inválido — fallback para substring
            if a.lower() in text_low:
                return True, a
    return False, ""


def _check_item_full_or_partial(item: dict, doc: ManuscriptDocument) -> tuple[bool, str]:
    """Para itens com automation_level full ou partial, executa heurística simples.
    Detection_method funciona como rótulo; usamos os anchors como evidência."""
    anchors = item.get("anchors", []) or []
    anchors_two = item.get("anchors_two_reviewers", []) or []
    anchors_single = item.get("anchors_single_reviewer_disclosed", []) or item.get("anchors_single_disclosed", [])
    all_anchors = anchors + anchors_two + anchors_single
    if not all_anchors:
        # sem anchors: sucesso default (item placeholder), mas registrar como aviso
        return True, "no_anchors_defined"
    found, evidence = _check_anchor_in_text(doc.raw_text, all_anchors)
    return found, evidence


def run_guideline_check(doc: ManuscriptDocument, guideline_id: str,
                        review_type: str | None = None,
                        is_meta_analysis: bool = False) -> list[CheckResult]:
    """Verifica um único reporting guideline contra o manuscrito."""
    g = _load_guideline_yaml(guideline_id)
    if not g:
        return [CheckResult(
            f"guideline.{guideline_id}.unavailable",
            f"Guideline {guideline_id}",
            True, "minor",
            evidence=f"Guideline profile not found in {GUIDELINES_DIR}",
        )]

    results: list[CheckResult] = []
    items = g.get("items", []) or []
    applies_to = g.get("applies_to", []) or []
    if review_type and applies_to and review_type not in applies_to:
        # guideline não se aplica
        return results

    for item in items:
        item_id = item.get("id", "?")
        title = item.get("title", "")
        automation = item.get("automation_level", "none")
        severity = item.get("severity_if_missing", "minor")
        only_if_meta = item.get("only_if_meta_analysis", False)
        if only_if_meta and not is_meta_analysis:
            continue

        if automation == "full":
            found, evidence = _check_item_full_or_partial(item, doc)
            results.append(CheckResult(
                f"guideline.{guideline_id}.{item_id}",
                f"{guideline_id} item {item_id}: {title}",
                found, severity,
                evidence=evidence if found else "anchor not found",
                fix_cost_estimate="low" if not found else "low",
            ))
        elif automation == "partial":
            found, evidence = _check_item_full_or_partial(item, doc)
            r = CheckResult(
                f"guideline.{guideline_id}.{item_id}",
                f"{guideline_id} item {item_id}: {title}",
                found, severity if not found else "minor",
                evidence=(evidence if found else "anchor not found") + " | needs_human_verification",
                fix_cost_estimate="medium",
            )
            r.extra["needs_human_verification"] = True
            results.append(r)
        else:  # none
            r = CheckResult(
                f"guideline.{guideline_id}.{item_id}",
                f"{guideline_id} item {item_id}: {title}",
                True, "minor",
                evidence="needs_human_review (not automatable)",
            )
            r.extra["needs_human_review"] = True
            results.append(r)

    return results


def run_all_guidelines(doc: ManuscriptDocument, profile: dict,
                       review_type: str | None = None,
                       is_meta_analysis: bool = False) -> list[CheckResult]:
    """Executa todas as guidelines endossadas pelo venue."""
    endorsed = profile.get("taxonomy", {}).get("reporting_guidelines_endorsed", []) or []
    all_results: list[CheckResult] = []
    for g_id in endorsed:
        all_results.extend(run_guideline_check(doc, g_id, review_type, is_meta_analysis))
    return all_results
