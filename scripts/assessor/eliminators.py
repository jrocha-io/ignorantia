"""
ignorantia.assessor.eliminators — Critérios eliminatórios E1-E11.

Verifica primeiro, antes de pontuar. Se qualquer um falhar:
- E1-E10 → nota = 0.0 (zona inválido/fraudulento)
- E11 → fase ghostwriter; nota numérica visível mas todos venues 🔴

A diferença é importante:
- Inválido/fraudulento = trabalho não pode ser nem rascunho de submissão.
- Incompleto/ghostwriter = pode virar submetível se o autor honrar a participação.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .helpers import (
    file_text,
    load_csv,
    load_json,
    strip_html,
    word_count,
    regex_any,
)


# v2.1: 18 valores válidos para review_type, distribuídos em três camadas hierárquicas.
# Sincronizado com references/profiles/_schema/venue_profile.schema.json.
VALID_REVIEW_TYPES_V21 = {
    # Camada Primária — você sozinho + busca autônoma OA
    "scoping_review",
    "rapid_review",
    "mapping_study",
    "integrative_review",
    "realist_review",
    # Camada Secundária — você sozinho + material fornecido
    "software_paper",
    "position_paper",
    "theoretical_essay",  # alias de position_paper
    "technical_report",
    "white_paper",
    "policy_brief",  # alias de white_paper
    # Camada Terciária — exige ≥1 humano adicional
    "systematic_review_with_2_reviewers",
    "systematic_review_strict",  # legacy alias para systematic_review_with_2_reviewers
    # Outros (legacy/v2.0, ainda aceitos no schema mas pouco usados)
    "narrative_review",
    "umbrella_review",
    "living_review",
    "meta_analysis",
    "qualitative_synthesis",
}

# Apenas dois valores no enum justificam o termo "Systematic Review" no texto sem violar E16.
SYSTEMATIC_REVIEW_VALID_VALUES = {
    "systematic_review_with_2_reviewers",
    "systematic_review_strict",
}

# v2.1: review_type → camada hierárquica.
REVIEW_TYPE_TO_LAYER = {
    "scoping_review": "primary",
    "rapid_review": "primary",
    "mapping_study": "primary",
    "integrative_review": "primary",
    "realist_review": "primary",
    "software_paper": "secondary",
    "position_paper": "secondary",
    "theoretical_essay": "secondary",
    "technical_report": "secondary",
    "white_paper": "secondary",
    "policy_brief": "secondary",
    "systematic_review_with_2_reviewers": "tertiary",
    "systematic_review_strict": "tertiary",
}


# Strings que indicam manuscrito sintético/fictício/teste
SYNTHETIC_MARKERS = [
    r"\bsmoke[\s-]test\b",
    r"\blorem ipsum\b",
    r"\bsynthetic (data|content|paper|manuscript)\b",
    r"\bfictíci[oa]s?\b",
    r"\bexemplo de teste\b",
    r"\bmanuscrito sintético\b",
    r"\bpipeline (test|validation)\b",
    r"\bthis is a test\b",
    r"\bplaceholder content\b",
    r"\bdummy (data|content|study)\b",
    r"\bteste de smoke\b",
]


# Marcadores de problematização (E12)
PROBLEMATIZATION_MARKERS = [
    r"\blacuna(s)?\b",
    r"\bgap[s]?\b",
    r"\bainda não foi\b|\byet to be\b",
    r"\bpermanece\s+em\s+aberto\b",
    r"\bnão\s+foi\s+investiga[a-z]+\b",
    r"\bnot\s+yet\s+investigat[a-z]+\b",
    r"\binvestigamos\b|\binvestigates?\b|\bwe\s+investigate\b",
    r"\bneste\s+estudo\b|\bin\s+this\s+study\b",
    r"\bobjetivo\s+(deste|do)\s+(trabalho|estudo)\b",
    r"\bRQ\s*\d|research question",
]


# Marcadores de cross-tabulação / diálogo entre autores (E13, E15)
CROSSTAB_MARKERS = [
    r"\bem contraste com\b",
    r"\bdiferentemente\b",
    r"\bpor outro lado\b",
    r"\bconvergem?\b",
    r"\bdivergem?\b",
    r"\bin contrast\b",
    r"\bdifferently\b",
    r"\bon the other hand\b",
    r"\bconverges?\b",
    r"\bdiverges?\b",
    r"\bhowever\b",
    r"\bentretanto\b",
    r"\bsimilarmente\b|\bsimilarly\b",
    r"\bdiversamente\b",
    r"\baligned with\b|\balinhad[oa]s?\s+com\b",
]


@dataclass
class EliminatorResult:
    """Resultado da verificação de um eliminatório."""
    code: str  # E1-E11
    name: str
    failed: bool
    severity: str  # "fraud" | "invalid" | "incomplete"
    detail: str = ""


@dataclass
class EliminatorReport:
    """Relatório consolidado dos 15 eliminatórios."""
    results: list[EliminatorResult] = field(default_factory=list)

    @property
    def has_fraud_or_invalid(self) -> bool:
        """E1-E10 (fraude/invalidez estrutural)."""
        return any(
            r.failed and r.severity in ("fraud", "invalid")
            and r.code in {"E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"}
            for r in self.results
        )

    @property
    def has_invalid_content(self) -> bool:
        """E12-E15 (qualidade de conteúdo abaixo do mínimo acadêmico)."""
        return any(
            r.failed and r.severity == "invalid_content"
            for r in self.results
        )

    @property
    def is_incomplete(self) -> bool:
        """E11 falhou (fase ghostwriter)."""
        return any(r.failed and r.severity == "incomplete" for r in self.results)

    @property
    def failed_codes(self) -> list[str]:
        return [r.code for r in self.results if r.failed]

    def details_for_failed(self) -> list[dict]:
        return [
            {"code": r.code, "name": r.name, "detail": r.detail, "severity": r.severity}
            for r in self.results if r.failed
        ]


def check_e1_ai_as_author(html_content: str, manuscript_authors: list[str]) -> EliminatorResult:
    """E1: IA listada como autora."""
    ia_pattern = re.compile(
        r"(?:author|autor[ae]s?)\s*[:.]?[\s\w,]{0,80}?"
        r"(claude|gpt|chatgpt|gemini|llm|copilot|llama|bard|openai|anthropic)",
        re.IGNORECASE,
    )
    failed = bool(ia_pattern.search(html_content or ""))
    # Also check structured authors list
    if manuscript_authors:
        for author in manuscript_authors:
            if isinstance(author, str) and re.search(
                r"^(claude|gpt|chatgpt|gemini|llama|copilot|bard)",
                author.strip(),
                re.IGNORECASE,
            ):
                failed = True
                break
    return EliminatorResult(
        code="E1",
        name="IA listada como autora",
        failed=failed,
        severity="invalid",
        detail=("IA possivelmente listada como autora — viola COPE, ICMJE, "
                "Portaria CNPq art. 9. Verificação manual obrigatória.")
        if failed else "OK — IA não listada como autora.",
    )


def check_e2_synthetic_manuscript(content: dict, html_content: str) -> EliminatorResult:
    """E2: Manuscrito fictício/sintético/teste."""
    # Concatenar texto principal das seções para varrer
    sections_to_check = [
        content.get("title", ""),
        content.get("subtitle", ""),
        content.get("abstract_html", ""),
        content.get("introduction_html", ""),
        content.get("synthesis_html", ""),
    ]
    full_text = " ".join(strip_html(s) for s in sections_to_check)
    failed = regex_any(full_text, SYNTHETIC_MARKERS)
    matched_marker = ""
    if failed:
        for pattern in SYNTHETIC_MARKERS:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                matched_marker = m.group(0)
                break
    return EliminatorResult(
        code="E2",
        name="Manuscrito fictício/sintético/teste",
        failed=failed,
        severity="invalid",
        detail=(f"Detectado marcador de teste/sintético: '{matched_marker}'. "
                "Trabalho não é manuscrito real.") if failed
                else "OK — sem marcadores de teste/sintético.",
    )


def check_e3_synthesis_too_short(content: dict, min_words: int = 500) -> EliminatorResult:
    """E3: Síntese < 500 palavras."""
    synthesis = content.get("synthesis_html", "")
    n = word_count(synthesis)
    failed = n < min_words
    return EliminatorResult(
        code="E3",
        name=f"Síntese < {min_words} palavras",
        failed=failed,
        severity="invalid",
        detail=(f"Síntese tem {n} palavras (mínimo: {min_words}). "
                "Sem análise substantiva.") if failed
                else f"OK — síntese tem {n} palavras (mínimo: {min_words}).",
    )


def check_e4_bibliography_too_small(content: dict, min_refs: int = 10) -> EliminatorResult:
    """E4: Bibliografia < 10 referências."""
    refs = content.get("references", [])
    n = len(refs) if isinstance(refs, list) else 0
    failed = n < min_refs
    return EliminatorResult(
        code="E4",
        name=f"Bibliografia < {min_refs} referências",
        failed=failed,
        severity="invalid",
        detail=(f"Apenas {n} referências (mínimo: {min_refs}). "
                "Sem corpus real.") if failed
                else f"OK — {n} referências (mínimo: {min_refs}).",
    )


def check_e5_prisma_flow(package_dir: Path) -> EliminatorResult:
    """E5: PRISMA flow ausente."""
    svg = package_dir / "prisma-flow.svg"
    json_data = package_dir / "prisma-flow.json"
    failed = not (svg.exists() or json_data.exists())
    return EliminatorResult(
        code="E5",
        name="PRISMA flow ausente",
        failed=failed,
        severity="invalid",
        detail="prisma-flow.svg / prisma-flow.json não encontrados no pacote."
            if failed else "OK — PRISMA flow presente.",
    )


def check_e6_qa_absent(qa_path: Path) -> EliminatorResult:
    """E6: Quality appraisal ausente."""
    rows = load_csv(qa_path)
    failed = len(rows) == 0
    return EliminatorResult(
        code="E6",
        name="Quality appraisal ausente",
        failed=failed,
        severity="invalid",
        detail="quality-appraisal.csv vazio ou ausente."
            if failed else f"OK — QA cobre {len(rows)} estudos.",
    )


def check_e7_few_databases(searches: dict | list | None, min_dbs: int = 3) -> EliminatorResult:
    """E7: < 3 bases consultadas."""
    n_dbs = 0
    if isinstance(searches, dict):
        per_db = searches.get("per_database", [])
        n_dbs = len(per_db) if isinstance(per_db, list) else 0
    elif isinstance(searches, list):
        n_dbs = len(searches)
    failed = n_dbs < min_dbs
    return EliminatorResult(
        code="E7",
        name=f"< {min_dbs} bases consultadas",
        failed=failed,
        severity="invalid",
        detail=f"Apenas {n_dbs} bases consultadas (mínimo: {min_dbs}). "
                "Cobertura insuficiente para SLR." if failed
                else f"OK — {n_dbs} bases consultadas.",
    )


def check_e8_ai_declaration(content: dict) -> EliminatorResult:
    """E8: Declaração de IA ausente."""
    ai = content.get("ai_declaration") or {}
    required_critical = ["tool", "stages", "authors_responsible"]
    missing = [f for f in required_critical if not ai.get(f)]
    failed = bool(missing)
    return EliminatorResult(
        code="E8",
        name="Declaração de IA ausente/incompleta",
        failed=failed,
        severity="invalid",
        detail=(f"Campos críticos faltando em ai_declaration: {', '.join(missing)}. "
                "Viola Portaria CNPq art. 9 e ICMJE Section II.A.4.") if failed
                else "OK — declaração de IA tem campos críticos preenchidos.",
    )


def check_e9_critical_plagiarism(plagiarism_report: dict | None) -> EliminatorResult:
    """E9: Plágio crítico detectado."""
    if not plagiarism_report:
        return EliminatorResult(
            code="E9",
            name="Plágio crítico detectado",
            failed=False,  # nem foi checado, então não falha aqui
            severity="fraud",
            detail="Detector de plágio não executado nesta versão. "
                "Camada 1 será executada na próxima rodada.",
        )
    n_critical = plagiarism_report.get("critical_matches", 0)
    failed = n_critical > 0
    return EliminatorResult(
        code="E9",
        name="Plágio crítico detectado",
        failed=failed,
        severity="fraud",
        detail=f"{n_critical} match(es) crítico(s) encontrado(s) (>15 palavras "
                "consecutivas sem aspas/atribuição). Verificar antes de submeter."
                if failed else "OK — sem plágio crítico detectado nas camadas executadas.",
    )


def check_e10_dead_dois(content: dict, dead_dois: list[str] | None = None) -> EliminatorResult:
    """E10: DOI fabricado/morto.

    dead_dois é lista de DOIs que não resolveram. Se a verificação não foi
    feita (Sprint 2), retorna não-falhado mas com detail explicativo.
    """
    if dead_dois is None:
        return EliminatorResult(
            code="E10",
            name="DOI fabricado (não-resolvível)",
            failed=False,
            severity="fraud",
            detail="Verificação de DOI vivo não executada nesta versão "
                "(implementação no Sprint 2).",
        )
    failed = len(dead_dois) > 0
    return EliminatorResult(
        code="E10",
        name="DOI fabricado (não-resolvível)",
        failed=failed,
        severity="fraud",
        detail=f"{len(dead_dois)} DOI(s) não resolveram: {', '.join(dead_dois[:5])}"
                + ("..." if len(dead_dois) > 5 else "") if failed
                else "OK — todos DOIs verificados resolveram.",
    )


def check_e11_phase_ghostwriter(version: str) -> EliminatorResult:
    """E11: Versão 0.x.y (fase ghostwriter — incompleto)."""
    failed = version.startswith("0.")
    if failed:
        detail = ("Versão 0.x.y indica fase ghostwriter — autor humano não "
                  "atestou ter cumprido as etapas que exigem juízo. "
                  "Todos os venues ficam 🔴 enquanto não houver transição para 1.x.y. "
                  "A nota numérica continua visível como POTENCIAL.")
    elif version.startswith("1."):
        detail = "OK — fase honrada (1.x.y). Autor cumpriu participação substancial."
    elif version.startswith("2."):
        detail = "OK — fase social (2.x.y). Trabalho passou por revisão dupla, kappa calculado."
    else:
        detail = f"Versão {version} fora do esquema 0/1/2.x.y."
    return EliminatorResult(
        code="E11",
        name="Fase ghostwriter (versão 0.x.y)",
        failed=failed,
        severity="incomplete",
        detail=detail,
    )


def check_e12_problematization(content: dict) -> EliminatorResult:
    """E12: Sem problematização (introdução não declara lacuna nem RQs)."""
    intro_html = content.get("introduction_html", "") or ""
    intro_text = strip_html(intro_html)
    rqs = content.get("rqs", [])

    has_problematization = regex_any(intro_text, PROBLEMATIZATION_MARKERS)
    has_rqs_in_intro = bool(re.search(r"RQ\s*\d|research question|pergunta\s+de\s+pesquisa",
                                       intro_text, re.IGNORECASE))
    has_rqs_declared = len(rqs) > 0

    failed = not (has_problematization and (has_rqs_in_intro or has_rqs_declared))

    if failed:
        missing = []
        if not has_problematization:
            missing.append("marcadores de lacuna ('lacuna', 'ainda não foi', 'permanece em aberto', 'investigamos', 'neste estudo')")
        if not (has_rqs_in_intro or has_rqs_declared):
            missing.append("RQs explícitas (RQ1, RQ2, ... ou 'pergunta de pesquisa')")
        detail = (f"Introdução não estabelece problematização. Faltam: {' E '.join(missing)}. "
                  "Trabalho acadêmico mínimo exige problematização explícita (não basta 'tema importante').")
    else:
        detail = "OK — introdução tem problematização e RQs declaradas."

    return EliminatorResult(
        code="E12",
        name="Sem problematização",
        failed=failed,
        severity="invalid_content",
        detail=detail,
    )


def check_e13_no_dialogue(content: dict) -> EliminatorResult:
    """E13: Sem diálogo entre autores (zero cross-markers em síntese substantiva)."""
    synthesis_html = content.get("synthesis_html", "") or ""
    synthesis_text = strip_html(synthesis_html)
    n_words = len(synthesis_text.split())

    # Só dispara se síntese tem volume mas zero diálogo
    if n_words < 500:
        # E3 já vai pegar o tamanho insuficiente; aqui não duplica
        return EliminatorResult(
            code="E13",
            name="Sem diálogo entre autores",
            failed=False,
            severity="invalid_content",
            detail="N/A — síntese < 500 palavras (E3 cuida).",
        )

    n_crosstab = sum(1 for p in CROSSTAB_MARKERS
                      if re.search(p, synthesis_text, re.IGNORECASE))
    failed = n_crosstab == 0

    detail = (f"Síntese de {n_words} palavras tem ZERO marcadores de cross-tabulação "
              f"('em contraste com', 'convergem', 'divergem', 'in contrast', etc.). "
              f"Trabalho acadêmico exige diálogo entre autores — não basta listar.")
    if not failed:
        detail = f"OK — {n_crosstab} marcador(es) de cross-tabulação encontrado(s)."

    return EliminatorResult(
        code="E13",
        name="Sem diálogo entre autores",
        failed=failed,
        severity="invalid_content",
        detail=detail,
    )


def check_e14_conclusion_doesnt_answer_rqs(content: dict) -> EliminatorResult:
    """E14: Conclusão não responde RQs declaradas na introdução.

    Detecção robusta: aceita RQs por número (RQ1, RQ2, ...) OU por conteúdo
    (palavras-chave da própria RQ aparecem na conclusão).
    """
    rqs = content.get("rqs", [])
    if not rqs:
        return EliminatorResult(
            code="E14",
            name="Conclusão não responde RQs",
            failed=False,
            severity="invalid_content",
            detail="N/A — sem RQs declaradas (E12 cuida).",
        )

    conclusion_html = content.get("conclusion_html", "") or ""
    conclusion_text = strip_html(conclusion_html).lower()

    # Lista de stopwords pt-BR + EN para filtrar palavras-chave significativas das RQs
    stopwords = {
        "rq", "para", "como", "quais", "que", "uma", "um", "the", "of", "is",
        "are", "in", "on", "at", "to", "and", "or", "with", "by", "from",
        "qual", "quaisquer", "do", "da", "de", "no", "na", "em", "se", "sobre",
        "este", "esta", "isso", "estes", "estas", "what", "which", "how",
    }

    n_rqs_detected = 0
    rq_details = []
    for i, rq_text in enumerate(rqs, 1):
        # Detecção por número (RQ1, RQ2, ...)
        by_number = bool(re.search(rf"\bRQ\s*{i}\b", conclusion_text, re.IGNORECASE))

        # Detecção por conteúdo: extrair palavras-chave significativas da RQ
        rq_clean = re.sub(rf"^RQ\s*{i}[:.\s]+", "", rq_text, flags=re.IGNORECASE)
        rq_words = re.findall(r"\b[\w\u00C0-\u017F'-]+\b", rq_clean.lower())
        # Manter só palavras significativas (≥4 chars e não-stopword)
        significant_words = [w for w in rq_words if len(w) >= 4 and w not in stopwords]
        # Considerar resposta se ≥2 palavras-chave significativas aparecem na conclusão
        if significant_words:
            matches = sum(1 for w in significant_words if w in conclusion_text)
            by_content = matches >= 2
        else:
            by_content = False

        detected = by_number or by_content
        if detected:
            n_rqs_detected += 1
        rq_details.append(f"RQ{i}: {'✓' if detected else '✗'}")

    failed = n_rqs_detected == 0 and len(rqs) > 0

    if failed:
        detail = (f"Conclusão não responde NENHUMA das {len(rqs)} RQs declaradas, "
                  f"nem por número (RQ1, RQ2, ...) nem por palavras-chave da RQ. "
                  f"Coerência teórico-metodológica exige que a conclusão responda "
                  f"explicitamente as perguntas iniciais. Status: " + ", ".join(rq_details))
    else:
        detail = (f"OK — conclusão responde {n_rqs_detected}/{len(rqs)} RQs "
                  f"(por número ou conteúdo). " + ", ".join(rq_details))

    return EliminatorResult(
        code="E14",
        name="Conclusão não responde RQs",
        failed=failed,
        severity="invalid_content",
        detail=detail,
    )


def check_e15_synthesis_listing(content: dict) -> EliminatorResult:
    """E15: Síntese é listagem (citações sequenciais sem cross-tabulação)."""
    synthesis_html = content.get("synthesis_html", "") or ""
    synthesis_text = strip_html(synthesis_html)
    n_words = len(synthesis_text.split())

    if n_words < 500:
        return EliminatorResult(
            code="E15",
            name="Síntese é listagem",
            failed=False,
            severity="invalid_content",
            detail="N/A — síntese < 500 palavras (E3 cuida).",
        )

    # Contar citações sequenciais: padrões como "[1] [2] [3]" ou "S01, S02, S03"
    sequential_patterns = (
        re.findall(r"\[\d+\][\s,]*\[\d+\][\s,]*\[\d+\]", synthesis_text)
        + re.findall(r"S\d{2,3}[\s,]+S\d{2,3}[\s,]+S\d{2,3}", synthesis_text)
        + re.findall(r"\(\w+,?\s*\d{4}[;\s]+\w+,?\s*\d{4}[;\s]+\w+,?\s*\d{4}", synthesis_text)
    )
    n_sequential = len(sequential_patterns)
    n_crosstab = sum(1 for p in CROSSTAB_MARKERS
                      if re.search(p, synthesis_text, re.IGNORECASE))

    # Falha se sequenciais > 5x cross-tabs (proporção pesadamente listagem)
    if n_crosstab == 0 and n_sequential >= 3:
        failed = True
    elif n_crosstab > 0 and n_sequential / max(n_crosstab, 1) > 5:
        failed = True
    else:
        failed = False

    if failed:
        detail = (f"Síntese tem {n_sequential} citações sequenciais e apenas "
                  f"{n_crosstab} cross-tabulações — predominantemente listagem. "
                  "Síntese acadêmica exige interpretação cruzada, não enumeração.")
    else:
        detail = f"OK — razão {n_sequential} sequenciais : {n_crosstab} cross-tabs aceitável."

    return EliminatorResult(
        code="E15",
        name="Síntese é listagem",
        failed=failed,
        severity="invalid_content",
        detail=detail,
    )


def check_e16_systematic_review_without_two_reviewers(content: dict, html_content: str) -> EliminatorResult:
    """E16 (NOVO em v2.0): Manuscrito declara-se 'Systematic Review' sem evidência de 2 revisores humanos.

    PRISMA-2020 itens 8 e 9 + MECIR R36+R52 + ACM SIGSOFT ESS-6 exigem dois revisores
    independentes em screening e extraction. Sem isso, não pode ser chamado de
    'Systematic Review' — deve ser scoping/rapid/mapping conforme apropriado.

    Política v2.0:
      - Manuscritos NOVOS (com `review_type` declarado no metadado) são auditados rigorosamente.
      - Manuscritos LEGACY (sem `review_type` declarado, pré-v2.0) recebem warning mas não bloqueio,
        pois a Decisão 1 ainda não estava em vigor quando foram produzidos.

    Verificação para manuscritos novos:
      1. metadado declara review_type = systematic_review_with_2_reviewers?
      2. Se sim: há evidência de 2 revisores humanos com kappa documentado?
      3. Se metadado declara outro tipo (scoping/rapid/mapping) mas título/texto contém "systematic review" → bloqueante.
    """
    text = strip_html(html_content) if html_content else ""
    title = content.get("title", "") or ""
    full_text = f"{title}\n{text}"
    full_low = full_text.lower()

    # review_type explícito no metadado (Decisão 1 da v2.0; expandido em v2.1)
    review_type_meta = (
        content.get("review_type")
        or (content.get("metadata", {}) or {}).get("review_type")
        or ""
    )

    # v2.1: validar que review_type, se declarado, está no enum válido.
    if review_type_meta and review_type_meta not in VALID_REVIEW_TYPES_V21:
        return EliminatorResult(
            code="E16",
            name="review_type inválido no metadado",
            failed=True,
            severity="invalid_content",
            detail=(
                f"Metadado declara review_type='{review_type_meta}' que não está "
                f"no enum válido v2.1. Valores aceitos: "
                f"{sorted(VALID_REVIEW_TYPES_V21)}. Ver references/modes/MODES_OVERVIEW.md."
            ),
        )

    # Trigger 1: o manuscrito reivindica ser SR no texto?
    sr_claim_patterns = [
        r"\bsystematic\s+(literature\s+)?review\b",
        r"\brevisão\s+sistemática\b",
        r"\brevision\s+sistemática\b",  # erro comum em ES
    ]
    claims_sr_in_text = any(re.search(p, full_low) for p in sr_claim_patterns)

    if not claims_sr_in_text and review_type_meta not in SYSTEMATIC_REVIEW_VALID_VALUES:
        return EliminatorResult(
            code="E16",
            name="Systematic Review sem 2 revisores",
            failed=False,
            severity="invalid_content",
            detail="N/A — manuscrito não se autodeclara Systematic Review.",
        )

    # Detectar evidência de 2 revisores
    two_reviewer_patterns = [
        r"\btwo\s+(independent\s+)?reviewers?\b",
        r"\btwo\s+researchers?\s+independent",
        r"\bdois\s+revisores?\s+independentes?\b",
        r"\bdos\s+revisores?\s+independent",
        r"\b2\s+revisores?\b",
    ]
    kappa_patterns = [
        r"\bcohen[''′]?s?\s+kappa\b",
        r"\bkappa\s*=\s*0?\.\d{1,3}",
        r"\binter[\s-]rater\s+(agreement|reliability)\b",
        r"\bfleiss[''′]?s?\s+kappa\b",
    ]
    has_two_reviewer_claim = any(re.search(p, full_low) for p in two_reviewer_patterns)
    has_kappa = any(re.search(p, full_low) for p in kappa_patterns)

    # Caso 1: metadado declara modo NÃO-SR-estrito mas texto/título tem "systematic review" → bloqueante
    if (review_type_meta and
            review_type_meta not in SYSTEMATIC_REVIEW_VALID_VALUES and
            claims_sr_in_text):
        layer = REVIEW_TYPE_TO_LAYER.get(review_type_meta, "unknown")
        return EliminatorResult(
            code="E16",
            name="Systematic Review sem 2 revisores",
            failed=True,
            severity="invalid_content",
            detail=(
                f"Metadado declara review_type='{review_type_meta}' (camada {layer}) "
                f"mas o texto/título contém 'systematic review'. Renomear para o modo "
                f"declarado (e.g., {review_type_meta.replace('_', ' ').title()}) ou "
                f"alterar metadado para 'systematic_review_with_2_reviewers' (camada terciária) "
                f"+ comprovar 2 revisores humanos com kappa documentado."
            ),
        )

    # Caso 2: metadado declara SR estrito mas falta evidência → bloqueante
    if review_type_meta in SYSTEMATIC_REVIEW_VALID_VALUES:
        if not (has_two_reviewer_claim and has_kappa):
            return EliminatorResult(
                code="E16",
                name="Systematic Review sem 2 revisores",
                failed=True,
                severity="invalid_content",
                detail=("Metadado declara review_type SR estrito (camada terciária) "
                        "mas falta evidência (claim de 2 revisores OU kappa documentado) no texto."),
            )
        return EliminatorResult(
            code="E16",
            name="Systematic Review com 2 revisores",
            failed=False,
            severity="invalid_content",
            detail="OK — metadado SR estrito + evidência de 2 revisores e kappa documentado.",
        )

    # Caso 3: SEM review_type no metadado (manuscrito legacy pré-v2.0)
    # Texto reivindica SR mas é pré-v2.0 — emitir warning, não bloquear.
    return EliminatorResult(
        code="E16",
        name="Systematic Review sem 2 revisores (legacy)",
        failed=False,
        severity="invalid_content",
        detail=("WARN — manuscrito legacy sem 'review_type' declarado. Reivindica 'systematic review' "
                "mas Decisão 1 da v2.0 não estava em vigor. Recomenda-se redepósito como "
                "'AI-Assisted Scoping Review' ou outro modo da v2.1 conforme apropriado "
                "(ver references/modes/MODES_OVERVIEW.md para os 10 modos disponíveis)."),
    )


def run_all_eliminators(
    *,
    package_dir: Path,
    content: dict,
    html_content: str,
    qa_path: Path,
    searches: dict | list | None,
    version: str,
    plagiarism_report: dict | None = None,
    dead_dois: list[str] | None = None,
) -> EliminatorReport:
    """Executa os 16 eliminatórios e retorna relatório consolidado.

    Eliminatórios:
      E1-E10 — fraude/invalidez estrutural (forçam Conteúdo 0.0 e Forma E)
      E11    — incompletude / fase ghostwriter (não bloqueia notas)
      E12-E15 — invalidez de conteúdo
      E16    — Systematic Review sem 2 revisores (NOVO em v2.0)
    """
    manuscript_authors = content.get("authors", [])
    if isinstance(manuscript_authors, str):
        manuscript_authors = [manuscript_authors]

    results = [
        # Fraude/invalidez estrutural
        check_e1_ai_as_author(html_content, manuscript_authors),
        check_e2_synthetic_manuscript(content, html_content),
        check_e3_synthesis_too_short(content),
        check_e4_bibliography_too_small(content),
        check_e5_prisma_flow(package_dir),
        check_e6_qa_absent(qa_path),
        check_e7_few_databases(searches),
        check_e8_ai_declaration(content),
        check_e9_critical_plagiarism(plagiarism_report),
        check_e10_dead_dois(content, dead_dois),
        # Incompletude
        check_e11_phase_ghostwriter(version),
        # Invalidez de conteúdo (Rodada C)
        check_e12_problematization(content),
        check_e13_no_dialogue(content),
        check_e14_conclusion_doesnt_answer_rqs(content),
        check_e15_synthesis_listing(content),
        # Nomenclatura imprópria (v2.0)
        check_e16_systematic_review_without_two_reviewers(content, html_content),
    ]
    return EliminatorReport(results=results)
