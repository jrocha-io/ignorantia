"""
ignorantia.assessor.sprint_badge — Mapeamento Conteúdo → Qualis/Quartil (Sprint Badge).

Calcula um marcador editorial que mapeia o eixo Conteúdo (0.0-10.0) para
classificação Qualis brasileiro (CAPES 2021-2024) e Quartil Scopus/JCR.

Ajustes aplicados antes do mapeamento:
  - 0.5 se pct_elite < 10  (bibliografia fraca penaliza)
  + 0.3 se c7_score >= 8   (semântico forte premia)
  - 0.5 se c7_score < 5    (semântico fraco penaliza, somente se C7 disponível)

Faixas (heurístico, pré-Sprint empírico completo):
  < 5.0   →  ⚠️ SUB-B4 / abaixo de Q4
  < 6.0   →  C / Apresentação local
  < 6.3   →  B4 / Q4 inferior   (percentil 0-12,5)
  < 6.6   →  B3 / Q4 superior   (percentil 12,5-25)
  < 7.0   →  B2 / Q3 inferior   (percentil 25-37,5)
  < 8.0   →  B1 / Q3 superior   (percentil 37,5-50)
  < 8.5   →  A4 / Q2 inferior   (percentil 50-62,5)
  < 9.0   →  A3 / Q2 superior   (percentil 62,5-75)
  < 9.5   →  A2 / Q1 inferior   (percentil 75-87,5)
  < 10.0  →  A1 / Q1 superior   (percentil 87,5-100)
  = 10.0 + c7≥9 + pct_elite≥50 →  🏆 ELITE GLOBAL

Bypass:
  E1-E10 falhou OU E12-E15 falhou → 🚫 NÃO-CLASSIFICÁVEL
  versão 0.x.y (ghostwriter)      → ⚪ POTENCIAL (badge real entre parênteses)

Calibração documentada em whitepaper-sprint-badge-calibration.md (Rodada P).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Versão da calibração — incrementar ao mudar TIER_TABLE ou TIER_TABLE_MIN
# Histórico de calibrações preservado em references/calibrations/.
CALIBRATION_VERSION = "1.0-2026-04-29"
CALIBRATION_NOTES = (
    "TIER_TABLE: 9 faixas calibradas em 4 cenários canônicos (validação empírica em FT real pendente). "
    "TIER_TABLE_MIN: 3 faixas calibradas empiricamente em 187 SLRs reais (Rodada N), "
    "precision Q1 = 97.6%, recall Q1 = 55.7%, acurácia útil = 59.5%."
)


# ── Estruturas ──────────────────────────────────────────────────────


@dataclass
class SprintBadge:
    """Resultado do mapeamento Sprint Badge."""

    # Status: 'classified' | 'unclassifiable' | 'potential' | 'sub_b4' | 'elite_global'
    status: str
    # Rótulos visíveis
    label_pt: str  # ex: "A2 (Qualis 2021-2024)"
    label_en: str  # ex: "Q1"
    # Tooltip explicativo
    tooltip_pt: str
    tooltip_en: str
    # Cor do badge
    color: str  # hex ou nome semântico
    # Notas para diagnóstico
    raw_score: float
    adjusted_score: float
    adjustments_applied: list[str]


# ── Mapeamento de faixas ─────────────────────────────────────────────


# (limite_superior, qualis_pt, quartil_en, percentil_label, color)
TIER_TABLE = [
    (6.0, "C",  "Below Q4",       "(local presentation level)",         "#9090a8"),
    (6.3, "B4", "Q4 (lower)",     "0-12.5 percentile (Q4 inferior)",    "#7878a0"),
    (6.6, "B3", "Q4 (upper)",     "12.5-25 percentile (Q4 superior)",   "#5a8090"),
    (7.0, "B2", "Q3 (lower)",     "25-37.5 percentile (Q3 inferior)",   "#4a8585"),
    (8.0, "B1", "Q3 (upper)",     "37.5-50 percentile (Q3 superior)",   "#4a9070"),
    (8.5, "A4", "Q2 (lower)",     "50-62.5 percentile (Q2 inferior)",   "#588060"),
    (9.0, "A3", "Q2 (upper)",     "62.5-75 percentile (Q2 superior)",   "#688058"),
    (9.5, "A2", "Q1 (lower)",     "75-87.5 percentile (Q1 inferior)",   "#787850"),
    (10.0, "A1", "Q1 (upper)",    "87.5-100 percentile (Q1 superior)",  "#806848"),
]


# Tabela calibrada empiricamente em Rodada N (187 SLRs reais) para PACOTE MÍNIMO
# (manuscrito construído apenas a partir de metadata Crossref+OpenAlex, sem texto integral).
# Granularidade reduzida a 3 faixas porque o sinal não permite distinguir 9 estratos sem texto integral.
# Thresholds otimizados via grid search (acurácia 59.5%, precision Q1 = 97.6%).
TIER_TABLE_MIN = [
    (3.8, "SUB-Q4",   "Below Q4",       "(perfil insuficiente)",                                "#d68a1e"),
    (4.3, "Q2-Q3",    "Q2-Q3 range",    "(perfil compatível com Q2-Q3 / A3-B1)",                "#4a8585"),
    (10.0, "Q1",      "Q1 range",       "(perfil compatível com Q1 / A1-A2 — alta precisão)",   "#787850"),
]


# ── Cálculo ─────────────────────────────────────────────────────────


def compute_sprint_badge(
    *,
    content_score: float,
    eliminator_failed: bool,
    is_ghostwriter_phase: bool,
    pct_elite: float,
    c7_score: float | None = None,
    is_minimal_package: bool = False,
) -> SprintBadge:
    """Computa o Sprint Badge para um manuscrito.

    Args:
        content_score: nota Conteúdo 0.0-10.0
        eliminator_failed: True se algum E1-E10 ou E12-E15 falhou
        is_ghostwriter_phase: True se versão 0.x.y
        pct_elite: % de refs em venues elite (0-100)
        c7_score: pontuação C7 (semântico Claude Chat); None se não disponível
        is_minimal_package: True se manuscrito é pacote mínimo (apenas metadata
                            sem texto integral). Quando True, usa TIER_TABLE_MIN
                            (3 faixas: SUB-Q4 / Q2-Q3 / Q1) calibrada em Rodada N
                            sobre 187 SLRs reais. Acurácia 59.5%, precision Q1 97.6%.

    Returns:
        SprintBadge com status, labels, tooltip, cor.
    """
    adjustments = []
    adjusted = content_score

    # Ajustes de bibliografia
    if pct_elite < 10:
        adjusted -= 0.5
        adjustments.append(f"−0.5 (bibliografia fraca: {pct_elite:.0f}% elite < 10%)")

    # Ajustes semânticos (C7) — só aplica se C7 estiver disponível
    if c7_score is not None:
        if c7_score >= 8.0:
            adjusted += 0.3
            adjustments.append(f"+0.3 (C7 semântico forte: {c7_score:.1f}/10)")
        elif c7_score < 5.0:
            adjusted -= 0.5
            adjustments.append(f"−0.5 (C7 semântico fraco: {c7_score:.1f}/10)")

    adjusted = max(0.0, min(10.0, adjusted))

    # ── Bypass: eliminatório falhou ──
    if eliminator_failed:
        return SprintBadge(
            status="unclassifiable",
            label_pt="🚫 NÃO-CLASSIFICÁVEL",
            label_en="🚫 UNCLASSIFIABLE",
            tooltip_pt=("Trabalho falhou critério eliminatório (E1-E10 ou E12-E15). "
                        "Não é possível atribuir Qualis/Quartil — primeiro corrigir o "
                        "problema invalidante."),
            tooltip_en=("Work failed eliminator criterion (E1-E10 or E12-E15). "
                        "Cannot assign Qualis/Quartile — first correct the invalidating issue."),
            color="#c93a3a",
            raw_score=content_score,
            adjusted_score=adjusted,
            adjustments_applied=adjustments,
        )

    # ── Sub-B4: nota muito baixa ──
    if adjusted < 5.0 and not is_minimal_package:
        return SprintBadge(
            status="sub_b4",
            label_pt="⚠️ SUB-B4 (abaixo de Q4)",
            label_en="⚠️ Below Q4",
            tooltip_pt=(f"Nota ajustada {adjusted:.1f}/10 está abaixo do mínimo Qualis B4. "
                        "Trabalho válido mas não atinge perfil de aceite editorial em venue indexado. "
                        "Considerar venue de divulgação local/institucional."),
            tooltip_en=(f"Adjusted score {adjusted:.1f}/10 is below minimum for Qualis B4. "
                        "Valid work but does not meet editorial profile for indexed venue. "
                        "Consider local/institutional outlet."),
            color="#d68a1e",
            raw_score=content_score,
            adjusted_score=adjusted,
            adjustments_applied=adjustments,
        )

    # ── Modo pacote mínimo: usar TIER_TABLE_MIN (3 faixas) ──
    if is_minimal_package:
        # Sem ghostwriter logic aqui — pacote mínimo é sempre informativo, não potencial
        if adjusted < 3.8:
            return SprintBadge(
                status="sub_q4_minimal",
                label_pt="⚠️ SUB-Q4 (pacote mínimo)",
                label_en="⚠️ Below Q4 (minimal package)",
                tooltip_pt=(f"Nota ajustada {adjusted:.1f}/10 (modo pacote mínimo). "
                            "Perfil insuficiente mesmo considerando que material é apenas metadata. "
                            "ATENÇÃO: classificação calibrada em corpus de 187 SLRs reais (Rodada N); "
                            "para classificação fina (A1/A2/A3/B1), submeter pacote completo com texto integral."),
                tooltip_en=(f"Adjusted score {adjusted:.1f}/10 (minimal package mode). "
                            "Insufficient profile even considering metadata-only input. "
                            "NOTE: classification calibrated on 187 real SLRs (Round N); "
                            "for fine-grained classification (A1/A2/A3/B1), submit full package with full text."),
                color="#d68a1e",
                raw_score=content_score, adjusted_score=adjusted,
                adjustments_applied=adjustments,
            )
        if adjusted < 4.3:
            return SprintBadge(
                status="q2_q3_minimal",
                label_pt="🟡 Perfil Q2-Q3 (pacote mínimo)",
                label_en="🟡 Q2-Q3 profile (minimal)",
                tooltip_pt=(f"Nota ajustada {adjusted:.1f}/10 (pacote mínimo). "
                            f"Perfil compatível com Qualis A3-B1 / Quartil Scopus Q2-Q3. "
                            "Calibração: corpus de 187 SLRs reais (Rodada N); acurácia ~60% nesta faixa. "
                            "Para classificação fina, submeter pacote completo com seções estruturadas."),
                tooltip_en=(f"Adjusted score {adjusted:.1f}/10 (minimal package). "
                            f"Profile compatible with Qualis A3-B1 / Scopus Q2-Q3. "
                            "Calibration: 187 real SLRs corpus (Round N); ~60% accuracy in this band. "
                            "For fine-grained classification, submit full package with structured sections."),
                color="#4a8585",
                raw_score=content_score, adjusted_score=adjusted,
                adjustments_applied=adjustments,
            )
        # ≥ 4.3: Q1 com alta precision (97.6% segundo Rodada N)
        return SprintBadge(
            status="q1_minimal",
            label_pt="🟢 Perfil Q1 (pacote mínimo)",
            label_en="🟢 Q1 profile (minimal)",
            tooltip_pt=(f"Nota ajustada {adjusted:.1f}/10 (pacote mínimo). "
                        f"Perfil compatível com Qualis A1-A2 / Quartil Scopus Q1. "
                        "Calibração Rodada N (n=187): precisão 97.6% — quando o sistema diz Q1, "
                        "é Q1 quase sempre. Para distinguir A1 vs A2, submeter pacote completo."),
            tooltip_en=(f"Adjusted score {adjusted:.1f}/10 (minimal package). "
                        f"Profile compatible with Qualis A1-A2 / Scopus Q1. "
                        "Round N calibration (n=187): 97.6% precision — when system says Q1, "
                        "it IS Q1 almost always. To distinguish A1 vs A2, submit full package."),
            color="#787850",
            raw_score=content_score, adjusted_score=adjusted,
            adjustments_applied=adjustments,
        )

    # ── Elite global: 10.0 + bibliografia + semântico ──
    if (adjusted >= 10.0 and pct_elite >= 50
            and c7_score is not None and c7_score >= 9.0):
        return SprintBadge(
            status="elite_global",
            label_pt="🏆 ELITE GLOBAL (A1+ / Q1 top)",
            label_en="🏆 ELITE GLOBAL (Q1 top)",
            tooltip_pt=("Nota máxima + bibliografia ≥50% elite + C7 semântico ≥9.0. "
                        "Perfil compatível com Nature/Science/Cell. NOTA: este badge "
                        "indica perfil editorial — aceitação real depende de fit, contexto "
                        "institucional e timing fora do escopo do ignorantia."),
            tooltip_en=("Max score + ≥50% elite biblio + C7 ≥9.0. Profile compatible with "
                        "Nature/Science/Cell. NOTE: badge indicates editorial profile — "
                        "actual acceptance depends on fit, institutional context, timing "
                        "outside ignorantia's scope."),
            color="#806848",
            raw_score=content_score,
            adjusted_score=adjusted,
            adjustments_applied=adjustments,
        )

    # ── Faixa Qualis/Quartil padrão ──
    qualis_pt = "C"
    quartil_en = "Below Q4"
    percentile_label = ""
    color = "#9090a8"
    for upper, qpt, qen, plabel, c in TIER_TABLE:
        if adjusted < upper:
            qualis_pt, quartil_en, percentile_label, color = qpt, qen, plabel, c
            break
    else:
        # adjusted >= 10.0 mas sem elite global
        qualis_pt, quartil_en, percentile_label, color = "A1", "Q1 (upper)", \
            "87.5-100 percentile (Q1 superior)", "#806848"

    # Ghostwriter (versão 0.x.y) → POTENCIAL com badge real entre parênteses
    if is_ghostwriter_phase:
        return SprintBadge(
            status="potential",
            label_pt=f"⚪ POTENCIAL ({qualis_pt})",
            label_en=f"⚪ POTENTIAL ({quartil_en})",
            tooltip_pt=(f"Versão ghostwriter (0.x.y) — Claude gerou primeira passada. "
                        f"Se honrado pela equipe humana, perfil seria {qualis_pt} "
                        f"(Qualis 2021-2024) / {quartil_en} (Scopus/JCR). "
                        f"Nota ajustada: {adjusted:.1f}/10. {percentile_label}."),
            tooltip_en=(f"Ghostwriter version (0.x.y) — Claude generated first pass. "
                        f"If honored by human team, profile would be {quartil_en} "
                        f"(Scopus/JCR) / {qualis_pt} (Qualis BR). "
                        f"Adjusted score: {adjusted:.1f}/10. {percentile_label}."),
            color=color,
            raw_score=content_score,
            adjusted_score=adjusted,
            adjustments_applied=adjustments,
        )

    # Caso normal: classificado
    return SprintBadge(
        status="classified",
        label_pt=f"{qualis_pt} (Qualis 2021-2024)",
        label_en=f"{quartil_en}",
        tooltip_pt=(f"Qualis brasileiro: {qualis_pt} (CAPES 2021-2024) · "
                    f"Quartil Scopus/JCR equivalente: {quartil_en} · {percentile_label}. "
                    f"Nota ajustada: {adjusted:.1f}/10 (bruta: {content_score:.1f}/10). "
                    f"NOTA: badge é estimativa de perfil editorial baseada em proxies "
                    f"(PRISMA + bibliografia + síntese), não predição de aceitação real."),
        tooltip_en=(f"Scopus/JCR Quartile: {quartil_en} · "
                    f"Qualis BR equivalent: {qualis_pt} · {percentile_label}. "
                    f"Adjusted score: {adjusted:.1f}/10 (raw: {content_score:.1f}/10). "
                    f"NOTE: badge estimates editorial profile based on proxies, "
                    f"not actual acceptance prediction."),
        color=color,
        raw_score=content_score,
        adjusted_score=adjusted,
        adjustments_applied=adjustments,
    )


# ── Helpers para extrair entradas do assessment ─────────────────────


def extract_pct_elite_from_assessment(assessment: dict) -> float:
    """Extrai pct_elite das dimensões do conteúdo (C3 — qualidade do corpus).

    Procura no critério "Venues de elite" da dimensão C3.
    """
    dims = assessment.get("content_axis", {}).get("dimensions", [])
    for dim in dims:
        if dim.get("code") == "C3":
            for crit in dim.get("criteria", []):
                desc = crit.get("description", "")
                # Esperado: "Venues de elite: 52% (alvo ≥20%)"
                m = re.search(r"Venues\s+de\s+elite:\s*(\d+(?:\.\d+)?)\s*%", desc)
                if m:
                    try:
                        return float(m.group(1))
                    except ValueError:
                        pass
    return 0.0


def extract_c7_score_from_assessment(assessment: dict) -> float | None:
    """Extrai C7 score (semântico Claude Chat) das dimensões.

    Returns None se C7 não disponível (modo standalone).
    """
    dims = assessment.get("content_axis", {}).get("dimensions", [])
    for dim in dims:
        if dim.get("code") == "C7":
            # Se peso é 0 ou pontuação é 0 e descrição diz "não disponível", retorna None
            for crit in dim.get("criteria", []):
                desc = crit.get("description", "")
                if "não disponível" in desc.lower() or "not available" in desc.lower():
                    return None
            # Caso contrário, normalizar ao 0-10 (peso é 1.0)
            pct = dim.get("percentage", 0.0)
            return pct / 10.0  # percentage 0-100 → score 0-10
    return None


def has_eliminator_failure(assessment: dict) -> bool:
    """Verifica se algum E1-E10 ou E12-E15 falhou (E11 incompleto não falha aqui)."""
    elims = assessment.get("eliminators", {})
    return bool(elims.get("has_fraud_or_invalid", False)
                or elims.get("has_invalid_content", False))


def is_ghostwriter_version(version: str) -> bool:
    """True se versão é 0.x.y."""
    return version.startswith("0.")


# ── Orquestrador ─────────────────────────────────────────────────────


def detect_minimal_package(assessment: dict, content: dict | None = None) -> tuple[bool, list[str]]:
    """Detecta heuristicamente se o pacote é mínimo (apenas metadata, sem texto integral).

    Sinais (≥2 → minimal):
        - ai_declaration menciona "metadata", "Crossref", "OpenAlex" como ferramenta principal
        - Background/methodology contém placeholder "não extraído" ou "not extracted"
        - References majoritariamente sem DOI
        - not_this_version_items menciona "metadata"

    Returns:
        (is_minimal, signals_detected)
    """
    signals = []
    if content is None:
        content = {}

    # 1. ai_declaration menciona metadata como fonte primária
    ai_decl = content.get('ai_declaration', {})
    tool_str = str(ai_decl.get('tool', '')).lower()
    if any(kw in tool_str for kw in ['metadata', 'crossref', 'openalex', 'sem geração de texto']):
        signals.append('ai_declaration_metadata')

    # 2. Background/methodology placeholder
    bg = (content.get('background_html') or '').lower()
    if 'não extraído' in bg or 'not extracted' in bg or 'texto integral indisponível' in bg:
        signals.append('placeholder_in_background')

    # 3. References majoritariamente sem DOI
    refs = content.get('references', [])
    if refs and len(refs) >= 5:
        no_doi_pct = sum(1 for r in refs if not r.get('doi')) / len(refs)
        if no_doi_pct > 0.7:
            signals.append('references_no_doi')

    # 4. not_this_version_items menciona "metadata"
    nv_items = content.get('not_this_version_items', [])
    if any('metadata' in str(item).lower() or 'crossref' in str(item).lower() for item in nv_items):
        signals.append('explicit_metadata_only')

    return (len(signals) >= 2, signals)


def compute_sprint_badge_from_assessment(assessment: dict, version: str,
                                          content: dict | None = None,
                                          force_minimal: bool | None = None) -> SprintBadge:
    """Calcula Sprint Badge a partir do assessment dict completo + versão.

    Args:
        assessment: dict completo do assessment
        version: versão do manuscrito
        content: dict do content.json (opcional, para detecção minimal)
        force_minimal: None = auto-detect; True/False = override
    """
    if force_minimal is True:
        is_minimal = True
    elif force_minimal is False:
        is_minimal = False
    else:
        is_minimal, _signals = detect_minimal_package(assessment, content)

    return compute_sprint_badge(
        content_score=assessment.get("content_axis", {}).get("score", 0.0),
        eliminator_failed=has_eliminator_failure(assessment),
        is_ghostwriter_phase=is_ghostwriter_version(version),
        pct_elite=extract_pct_elite_from_assessment(assessment),
        c7_score=extract_c7_score_from_assessment(assessment),
        is_minimal_package=is_minimal,
    )


def serialize_badge(badge: SprintBadge) -> dict:
    """Converte para dict JSON-serializável.

    Inclui CALIBRATION_VERSION para auditabilidade — permite rastrear qual
    versão da calibração foi usada quando o badge foi gerado, mesmo que a
    skill seja atualizada depois.
    """
    return {
        "status": badge.status,
        "label_pt": badge.label_pt,
        "label_en": badge.label_en,
        "tooltip_pt": badge.tooltip_pt,
        "tooltip_en": badge.tooltip_en,
        "color": badge.color,
        "raw_score": badge.raw_score,
        "adjusted_score": badge.adjusted_score,
        "adjustments_applied": badge.adjustments_applied,
        "calibration_version": CALIBRATION_VERSION,
    }
