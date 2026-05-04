#!/usr/bin/env python3
"""
attest_phase_transition.py — Atestação humana de transição entre fases.

Implementa o mecanismo descrito em references/semver-policy.md:
- Transição 0.x.y → 1.0.0 (ghostwriter → honrada)
- Transição 1.x.y → 2.0.0 (honrada → social)

Uso:
    python attest_phase_transition.py --from-version 0.3.0 --to-phase honored
    python attest_phase_transition.py --from-version 1.2.0 --to-phase social

A atestação é por boa-fé. O skill apresenta o checklist e o autor humano
confirma cada item. Sem confirmação de itens críticos, não há transição.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CHECKLIST_GHOSTWRITER_TO_HONORED = [
    {
        "id": "G2H-01",
        "text": "Eu li integralmente cada paper que entrou no corpus final",
        "critical": True,
    },
    {
        "id": "G2H-02",
        "text": "Eu apliquei o instrumento de quality appraisal a cada estudo, não a IA",
        "critical": True,
    },
    {
        "id": "G2H-03",
        "text": "Eu reescrevi substancialmente a síntese narrativa com voz própria",
        "critical": True,
    },
    {
        "id": "G2H-04",
        "text": "Eu escrevi a discussão com argumentação minha",
        "critical": True,
    },
    {
        "id": "G2H-05",
        "text": "Eu defini os critérios de inclusão e exclusão (não a IA)",
        "critical": True,
    },
    {
        "id": "G2H-06",
        "text": "Eu identifiquei limitações honestamente",
        "critical": False,
    },
    {
        "id": "G2H-07",
        "text": "As recomendações finais são meu juízo profissional",
        "critical": True,
    },
    {
        "id": "G2H-08",
        "text": "Eu compreendo cada referência citada e como ela suporta o argumento",
        "critical": False,
    },
    {
        "id": "G2H-09",
        "text": "A declaração de uso de IA reflete fielmente o uso (não maquiada)",
        "critical": True,
    },
    {
        "id": "G2H-10",
        "text": "Eu verifiquei pessoalmente os matches do detector de plágio (camada 1)",
        "critical": False,
    },
]


CHECKLIST_HONORED_TO_SOCIAL = [
    {
        "id": "H2S-01",
        "text": "Dois revisores humanos foram identificados e nomeados",
        "critical": True,
    },
    {
        "id": "H2S-02",
        "text": "Cada revisor fez triagem independente e quality appraisal independente",
        "critical": True,
    },
    {
        "id": "H2S-03",
        "text": "Cohen's kappa foi calculado e está em arquivo kappa-calculation.csv",
        "critical": True,
    },
    {
        "id": "H2S-04",
        "text": "Discordâncias foram resolvidas e documentadas",
        "critical": True,
    },
    {
        "id": "H2S-05",
        "text": "Versão final reflete os ajustes pós-revisão dupla",
        "critical": True,
    },
]


def confirm_checklist_interactive(checklist: list[dict]) -> dict:
    """Pergunta cada item ao usuário no terminal, retorna dict de respostas."""
    print()
    print("=" * 70)
    print("CHECKLIST DE ATESTAÇÃO")
    print("=" * 70)
    print()
    print("Para cada item, responda Y (sim, cumprido) ou N (não cumprido).")
    print("Itens marcados com (CRÍTICO) bloqueiam a transição se não cumpridos.")
    print()

    responses = {}
    for item in checklist:
        marker = " (CRÍTICO)" if item["critical"] else ""
        print(f"[{item['id']}]{marker} {item['text']}")
        while True:
            resp = input("  Cumprido? (Y/N): ").strip().lower()
            if resp in ("y", "yes", "s", "sim"):
                responses[item["id"]] = True
                break
            elif resp in ("n", "no", "não", "nao"):
                responses[item["id"]] = False
                break
            else:
                print("  Resposta inválida. Use Y ou N.")
    return responses


def confirm_checklist_from_file(checklist: list[dict], answers_file: Path) -> dict:
    """Para uso não-interativo: lê respostas de arquivo JSON."""
    if not answers_file.exists():
        print(f"Erro: arquivo de respostas não encontrado: {answers_file}", file=sys.stderr)
        sys.exit(1)
    raw = json.loads(answers_file.read_text(encoding="utf-8"))
    return {item["id"]: bool(raw.get(item["id"], False)) for item in checklist}


def evaluate_attestation(checklist: list[dict], responses: dict) -> tuple[bool, list[str]]:
    """Decide se a atestação passa e lista itens críticos não-cumpridos."""
    critical_failed = []
    for item in checklist:
        if item["critical"] and not responses.get(item["id"], False):
            critical_failed.append(f"[{item['id']}] {item['text']}")
    return (len(critical_failed) == 0), critical_failed


def increment_version_to_phase(from_version: str, target_phase: str) -> str:
    """Calcula a próxima versão, dada a fase-alvo."""
    parts = from_version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Versão inválida: {from_version}")
    if target_phase == "honored":
        return "1.0.0"
    elif target_phase == "social":
        return "2.0.0"
    else:
        raise ValueError(f"Fase-alvo desconhecida: {target_phase}")


def main():
    parser = argparse.ArgumentParser(
        description="Atestação humana de transição de fase (ghostwriter→honored ou honored→social)."
    )
    parser.add_argument("--from-version", required=True,
                        help="Versão atual, e.g. 0.3.0")
    parser.add_argument("--to-phase", required=True, choices=["honored", "social"],
                        help="Fase-alvo: honored (1.0.0) ou social (2.0.0)")
    parser.add_argument("--author", default="",
                        help="Nome do autor humano que está atestando")
    parser.add_argument("--answers-file", type=Path,
                        help="JSON com respostas (alternativa a interativo)")
    parser.add_argument("--out", type=Path,
                        help="JSON de saída com resultado da atestação")
    args = parser.parse_args()

    # Validar consistência de from-version e to-phase
    if args.to_phase == "honored" and not args.from_version.startswith("0."):
        print("Erro: transição para 'honored' requer versão 0.x.y atual.", file=sys.stderr)
        sys.exit(1)
    if args.to_phase == "social" and not args.from_version.startswith("1."):
        print("Erro: transição para 'social' requer versão 1.x.y atual.", file=sys.stderr)
        sys.exit(1)

    if args.to_phase == "honored":
        checklist = CHECKLIST_GHOSTWRITER_TO_HONORED
    else:
        checklist = CHECKLIST_HONORED_TO_SOCIAL

    # Coletar respostas
    if args.answers_file:
        responses = confirm_checklist_from_file(checklist, args.answers_file)
    else:
        responses = confirm_checklist_interactive(checklist)

    # Avaliar
    passed, critical_failed = evaluate_attestation(checklist, responses)

    print()
    print("=" * 70)
    print("RESULTADO DA ATESTAÇÃO")
    print("=" * 70)
    if passed:
        new_version = increment_version_to_phase(args.from_version, args.to_phase)
        print(f"✅ Atestação passa. Transição autorizada:")
        print(f"   {args.from_version}  →  {new_version}  ({args.to_phase})")
    else:
        print(f"❌ Atestação NÃO passa. Itens críticos não-cumpridos:")
        for item in critical_failed:
            print(f"   - {item}")
        print()
        print(f"Pacote permanece em {args.from_version} (fase ghostwriter ou honrada).")
        new_version = args.from_version

    # Saída
    result = {
        "from_version": args.from_version,
        "to_phase": args.to_phase,
        "new_version": new_version,
        "author": args.author,
        "attested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": passed,
        "critical_failed": critical_failed,
        "responses": responses,
    }
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nResultado salvo em {args.out}")

    sys.exit(0 if passed else 2)


if __name__ == "__main__":
    main()
