#!/usr/bin/env python3
"""
ignorantia.assessor.main — Orquestrador do pipeline de avaliação v2.0 (dois eixos).

Fluxo:
    1. Carrega artefatos do pacote
    2. Camada 1 de plágio (interna ao corpus)
    3. Executa eliminatórios (E1-E15)
    4. Aplica rubrica nos DOIS eixos:
       - Conteúdo (escala 0.0-10.0)
       - Forma (escala E/D/C/B/A/A+)
    5. Gera JSON consolidado

Uso:
    python -m assessor.main \\
        --package-dir /path/to/package \\
        --content manuscript-content.json \\
        --extraction extraction.csv \\
        --qa quality-appraisal.csv \\
        --searches searches.json \\
        --html manuscript.html \\
        --version 1.0.0 \\
        --topic-slug bnce-gamificacao \\
        --area-slug educacao \\
        --area "Educação" \\
        --lang pt-BR \\
        --out avaliacao.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .eliminators import run_all_eliminators, EliminatorReport
from .rubric import assess_all, RubricReport
from .plagiarism import detect_plagiarism_layer1, render_plagiarism_summary
from .temperature import compute_temperature, render_temperature_summary
from .venues import evaluate_all_venues, render_venues_summary
from .audit import run_audit, summarize_audit
from .sprint_badge import compute_sprint_badge_from_assessment, serialize_badge, detect_minimal_package
from .helpers import load_json, load_csv, file_text, detect_lang_is_ptbr


def get_phase(version: str) -> str:
    """Retorna 'ghostwriter' | 'honored' | 'social'."""
    if version.startswith("0."):
        return "ghostwriter"
    elif version.startswith("1."):
        return "honored"
    elif version.startswith("2."):
        return "social"
    return "unknown"


def get_zone(elim_report: EliminatorReport) -> str:
    """Retorna a zona visualmente diferenciada:
    - 'fraud_or_invalid'  → vermelho (E1-E10 falharam)
    - 'invalid_content'   → laranja (E12-E15 falharam mas E1-E10 passaram)
    - 'incomplete'        → azul (E11 falhou apenas)
    - 'ok'                → verde (nenhum eliminatório bloqueante)
    """
    if elim_report.has_fraud_or_invalid:
        return "fraud_or_invalid"
    if elim_report.has_invalid_content:
        return "invalid_content"
    if elim_report.is_incomplete:
        return "incomplete"
    return "ok"


def map_content_score_to_venue(score: float, is_ptbr: bool, phase: str) -> str:
    """Mapeia nota de Conteúdo → veículo recomendado, considerando a fase."""
    if phase == "ghostwriter":
        return ("Fase ghostwriter (0.x.y) — não submetível em qualquer venue. "
                "Autor humano precisa honrar a participação para transição → 1.0.0."
                if is_ptbr else
                "Ghostwriter phase — not submittable. Human author must honor participation.")
    if score >= 9.5:
        return ("Qualis A1 (Educ@, SciELO BR top); pronto para internacionalizar a Q1"
                if is_ptbr else
                "Top elite venue: Nature flagship, Lancet, Cell, IEEE Trans Q1, ACM Trans Q1, AAAS")
    if score >= 8.5:
        return ("Qualis A2 ou A3" if is_ptbr else "Q1-Q2 international")
    if score >= 7.5:
        return "Qualis A4 ou B1" if is_ptbr else "Q2-Q3 international"
    if score >= 6.5:
        return "Qualis B2-B3" if is_ptbr else "Q3-Q4 international"
    if score >= 5.0:
        return "Qualis B4-B5" if is_ptbr else "OA generalists"
    return ("NÃO submeter — revisar e gerar nova versão"
            if is_ptbr else "DO NOT submit — revise and generate new version")


def build_assessment_data(
    *,
    args: argparse.Namespace,
    content: dict,
    html_content: str,
    elim_report: EliminatorReport,
    rubric_report: RubricReport | None,
    plagiarism_summary: dict,
) -> dict:
    """Constrói dict serializável com toda informação para renderização."""
    is_ptbr = detect_lang_is_ptbr(content)
    phase = get_phase(args.version)
    zone = get_zone(elim_report)

    # Aplicar zonas de zero
    if elim_report.has_fraud_or_invalid:
        # E1-E10 falharam → Conteúdo 0.0 e Forma E
        content_score = 0.0
        form_score = 0.0
        form_letter = "E"
        form_dimensions = []
        content_dimensions = []
    elif elim_report.has_invalid_content:
        # E12-E15 falharam → Conteúdo 0.0 mas Forma pode ser >E
        content_score = 0.0
        if rubric_report:
            form_score = rubric_report.form_report.final_score
            form_letter = rubric_report.form_report.final_letter
            form_dimensions = serialize_dimensions(rubric_report.form_report.dimensions)
            content_dimensions = serialize_dimensions(rubric_report.content_report.dimensions)
        else:
            form_score = 0.0
            form_letter = "E"
            form_dimensions = []
            content_dimensions = []
    else:
        # OK ou apenas E11 (incompleto) — notas reais
        if rubric_report:
            content_score = rubric_report.content_report.final_score
            form_score = rubric_report.form_report.final_score
            form_letter = rubric_report.form_report.final_letter
            form_dimensions = serialize_dimensions(rubric_report.form_report.dimensions)
            content_dimensions = serialize_dimensions(rubric_report.content_report.dimensions)
        else:
            content_score = 0.0
            form_score = 0.0
            form_letter = "E"
            form_dimensions = []
            content_dimensions = []

    data = {
        "meta": {
            "skill_version": "ignorantia 2.0.0-alpha24",
            "package_version": args.version,
            "phase": phase,
            "package_name": f"ignorantia-{args.area_slug}-{args.topic_slug}-v{args.version}",
            "lang": "pt-BR" if is_ptbr else "en",
            "area": args.area or "",
            "assessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "zone": zone,
        },
        "content_axis": {
            "scale": "numeric",
            "score": content_score,
            "max": 10.0,
            "raw_total": rubric_report.content_report.raw_total if rubric_report else 0.0,
            "bonus": rubric_report.content_report.bonus_points if rubric_report else 0.0,
            "bonus_applied": rubric_report.content_report.bonus_applied if rubric_report else [],
            "dimensions": content_dimensions,
            "recommended_venue_tier": map_content_score_to_venue(content_score, is_ptbr, phase),
            "is_zero_blocked": elim_report.has_fraud_or_invalid or elim_report.has_invalid_content,
        },
        "form_axis": {
            "scale": "alphabetic",
            "letter": form_letter,
            "score_internal": form_score,  # 0.0-10.0 interno
            "max_internal": 10.0,
            "letter_meaning": {
                "A+": "Forma exemplar; pronto para venue de elite",
                "A": "Forma boa; aceitável em qualquer venue",
                "B": "Forma adequada; pequenos ajustes",
                "C": "Forma marginal; ajustes necessários",
                "D": "Forma deficiente; revisão estrutural",
                "E": "Forma inadequada; refazer artefatos",
            }.get(form_letter, ""),
            "dimensions": form_dimensions,
        },
        "eliminators": {
            "all": [
                {
                    "code": r.code,
                    "name": r.name,
                    "failed": r.failed,
                    "severity": r.severity,
                    "detail": r.detail,
                }
                for r in elim_report.results
            ],
            "has_fraud_or_invalid": elim_report.has_fraud_or_invalid,
            "has_invalid_content": elim_report.has_invalid_content,
            "is_incomplete": elim_report.is_incomplete,
        },
        "notes": {
            "critical": rubric_report.content_report.all_critical_notes() + rubric_report.form_report.all_critical_notes() if rubric_report else [],
            "important": rubric_report.content_report.all_important_notes() + rubric_report.form_report.all_important_notes() if rubric_report else [],
            "polish": rubric_report.content_report.all_polish_notes() + rubric_report.form_report.all_polish_notes() if rubric_report else [],
        },
        "plagiarism": plagiarism_summary,
        # audit injetado depois de detectar minimal
    }

    # Detectar pacote mínimo ANTES da auditoria, para rebaixar A7 quando aplicável
    force_minimal_arg = (True if args.minimal_package == "yes"
                         else False if args.minimal_package == "no"
                         else None)
    if force_minimal_arg is not None:
        is_minimal_for_audit = force_minimal_arg
    else:
        # Detector heurístico v0 — só usa content.json
        is_minimal_for_audit, _signals = detect_minimal_package({}, content)

    # Auditoria com flag minimal_package
    data["audit"] = summarize_audit(
        run_audit(content, is_minimal_package=is_minimal_for_audit)
    )

    # Sprint Badge depende do dict completo, computar após audit
    data["sprint_badge"] = serialize_badge(
        compute_sprint_badge_from_assessment(
            data, args.version,
            content=content,
            force_minimal=force_minimal_arg,
        )
    )

    # Documentar detecção (mesma chamada que sprint_badge usa internamente)
    is_minimal, signals = detect_minimal_package(data, content)
    if is_minimal or args.minimal_package == "yes":
        data["minimal_package_detected"] = {
            "is_minimal": True,
            "auto_detected": is_minimal,
            "force_mode": args.minimal_package,
            "signals": signals,
        }
    return data


def serialize_dimensions(dimensions) -> list[dict]:
    """Converte lista de DimensionResult para JSON-serializável."""
    return [
        {
            "code": d.code,
            "name": d.name,
            "weight": d.weight,
            "axis": d.axis,
            "points_obtained": d.points_obtained,
            "percentage": d.percentage,
            "criteria": [
                {
                    "label": c.label,
                    "description": c.description,
                    "points_obtained": c.points_obtained,
                    "points_max": c.points_max,
                    "passed": c.points_obtained >= c.points_max * 0.99,
                    "partial": 0 < c.points_obtained < c.points_max * 0.99,
                }
                for c in d.criteria
            ],
        }
        for d in dimensions
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Avaliação automática do pacote ignorantia (dois eixos)."
    )
    # Self-test (não requer outros args)
    parser.add_argument("--self-test", action="store_true",
                        help="Roda bateria de regressão dos 4 cenários canônicos "
                             "(test-cases/scenarios/) e termina com código 0 ou 1.")

    parser.add_argument("--package-dir", type=Path)
    parser.add_argument("--content", type=Path)
    parser.add_argument("--extraction", type=Path)
    parser.add_argument("--qa", type=Path)
    parser.add_argument("--searches", default=None, type=Path)
    parser.add_argument("--html", default=None, type=Path)
    parser.add_argument("--version")
    parser.add_argument("--topic-slug")
    parser.add_argument("--area-slug", default="area")
    parser.add_argument("--area", default="")
    parser.add_argument("--lang", default="pt-BR")
    parser.add_argument("--is-se-cs", action="store_true")
    parser.add_argument("--is-health", action="store_true")
    parser.add_argument("--venues-catalog", default=None, type=Path,
                        help="JSON com catálogo de venues; default: references/venues-catalog.json")
    parser.add_argument("--minimal-package", choices=["auto", "yes", "no"], default="auto",
                        help="Modo de pacote mínimo (apenas metadata sem texto integral). "
                             "'auto' = detecção heurística (default); 'yes' = forçar; 'no' = forçar desativado.")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    # Self-test: dispara antes de validar outros argumentos
    if args.self_test:
        from .self_test import run_self_test_suite
        sys.exit(run_self_test_suite(verbose=True))

    # Validar argumentos obrigatórios para modo normal
    required_for_run = ["package_dir", "content", "extraction", "qa", "version",
                        "topic_slug", "out"]
    missing = [name for name in required_for_run if getattr(args, name) is None]
    if missing:
        parser.error(f"Argumentos obrigatórios ausentes: {', '.join('--' + m.replace('_','-') for m in missing)}")

    content = load_json(args.content) or {}
    html_content = file_text(args.html) if args.html else ""
    searches = load_json(args.searches) if args.searches else None
    extraction_rows = load_csv(args.extraction)

    # Phase 0: Plágio camada 1
    plagiarism_report = detect_plagiarism_layer1(html_content, extraction_rows)
    plagiarism_summary = render_plagiarism_summary(
        plagiarism_report, is_ptbr=detect_lang_is_ptbr(content)
    )

    # Phase 1: Eliminadores
    elim_report = run_all_eliminators(
        package_dir=args.package_dir,
        content=content,
        html_content=html_content,
        qa_path=args.qa,
        searches=searches,
        version=args.version,
        plagiarism_report=plagiarism_summary,
    )

    # Phase 2: Rubrica (sempre roda; aplicação das zonas é em build_assessment_data)
    rubric_report = assess_all(
        package_dir=args.package_dir,
        content=content,
        html_content=html_content,
        extraction_path=args.extraction,
        qa_path=args.qa,
        searches=searches,
        version=args.version,
        is_se_cs=args.is_se_cs,
        is_health=args.is_health,
    )

    # Phase 2.5: Temperatura (4 critérios T1-T4)
    # NOTA: temperatura só é calculada/exibida quando o trabalho passa eliminatórios
    # de fraude/invalidez (E1-E10) e de conteúdo (E12-E15). Caso contrário, exibir
    # temperatura seria enganoso — o trabalho falhou em critério eliminatório e
    # qualquer cumprimento de outros critérios é cosmético.
    if elim_report.has_fraud_or_invalid or elim_report.has_invalid_content:
        temperature_summary = {
            "value": None,
            "scale": "0.0 to 1.0",
            "suppressed": True,
            "suppressed_reason": (
                "Trabalho falhou em eliminatório E1-E10 (fraude/invalidez) ou "
                "E12-E15 (invalidez de conteúdo). Temperatura suprimida para evitar "
                "leitura enganosa: cumprimento mecânico de critérios editoriais não "
                "compensa falha em problematização, diálogo, ou autenticidade."
            ),
            "tooltip_explanation": (
                "Temperatura suprimida. Trabalho precisa primeiro passar nos "
                "eliminatórios antes que a avaliação editorial faça sentido."
            ),
        }
    else:
        temperature_report = compute_temperature(
            package_dir=args.package_dir,
            content=content,
            extraction_path=args.extraction,
            plagiarism_summary=plagiarism_summary,
            area=args.area or "",
        )
        temperature_summary = render_temperature_summary(temperature_report)

    # Phase 3: Build dict
    data = build_assessment_data(
        args=args, content=content, html_content=html_content,
        elim_report=elim_report, rubric_report=rubric_report,
        plagiarism_summary=plagiarism_summary,
    )
    data["temperature"] = temperature_summary

    # Phase 4: Avaliação por venue (Rodada E2)
    catalog_path = args.venues_catalog
    if catalog_path is None:
        # Procurar default relativo ao script (sem hardcoded paths)
        script_dir = Path(__file__).parent.parent
        candidates = [
            script_dir.parent / "references" / "venues-catalog.json",  # padrão skill
            script_dir / "references" / "venues-catalog.json",         # alt: scripts/references
            Path.cwd() / "references" / "venues-catalog.json",         # cwd
        ]
        # Permitir override via variável de ambiente
        import os
        env_path = os.environ.get("IGNORANTIA_VENUES_CATALOG")
        if env_path:
            candidates.insert(0, Path(env_path))
        for c in candidates:
            if c.exists():
                catalog_path = c
                break

    if catalog_path and catalog_path.exists():
        # Determinar fase para o módulo venues
        phase = "ghostwriter" if args.version.startswith("0.") else \
                "honored" if args.version.startswith("1.") else \
                "social" if args.version.startswith("2.") else "honored"
        venues_report = evaluate_all_venues(
            package_dir=args.package_dir,
            content=content,
            extraction_path=args.extraction,
            catalog_path=catalog_path,
            phase=phase,
            area=args.area or "",
        )
        data["venues_evaluation"] = render_venues_summary(venues_report)
    else:
        data["venues_evaluation"] = {
            "n_ready": 0, "n_near": 0, "n_far": 0, "n_inadequate": 0,
            "phase_blocked": False,
            "phase_message": "Catálogo de venues não encontrado.",
            "checks": [],
        }

    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"  Conteúdo:    {data['content_axis']['score']}/10.0")
    print(f"  Forma:       {data['form_axis']['letter']} (interno: {data['form_axis']['score_internal']:.2f}/10)")
    if data['temperature'].get('suppressed'):
        print(f"  🌡️ Temperatura: SUPRIMIDA (zona {data['meta']['zone']})")
    else:
        print(f"  🌡️ Temperatura: {data['temperature']['value']:.3f} "
              f"(C7 {'ATIVO' if data['temperature']['c7_available'] else 'AUSENTE'})")
    print(f"  Zona:        {data['meta']['zone']}")
    print(f"  Fase:        {data['meta']['phase']}")
    ve = data.get('venues_evaluation', {})
    print(f"  Venues:      🔵 {ve.get('n_excellent', 0)} · 🟢 {ve.get('n_ready', 0)} · "
          f"🟡 {ve.get('n_near', 0)} · 🟠 {ve.get('n_far', 0)} · 🔴 {ve.get('n_inadequate', 0)}")


if __name__ == "__main__":
    main()
