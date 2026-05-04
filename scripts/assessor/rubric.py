"""
ignorantia.assessor.rubric — Rubrica em DOIS EIXOS independentes.

Eixo Conteúdo:  escala numérica 0.0 - 10.0
  C1 — Problematização e tese          (peso 1.0)
  C2 — Diálogo entre autores           (peso 1.5)
  C3 — Qualidade do corpus             (peso 2.0)
  C4 — Síntese substantiva             (peso 2.0)
  C5 — Coerência teórico-metodológica  (peso 1.0)
  C6 — Argumentação e originalidade    (peso 1.5)
  C7 — Análise semântica (Claude Chat) (peso 1.0)

Eixo Forma:     escala alfabética E / D / C / B / A / A+
  F1 — Estrutura ABNT/IEEE/Vancouver/APA      (peso 2.5)
  F2 — Compliance ético-legal                  (peso 3.0)
  F3 — Rigor metodológico procedimental        (peso 2.5)
  F4 — Apresentação e auditabilidade           (peso 2.0)

Bonificadores Conteúdo: até +0.3
Arredondamento: SEMPRE para baixo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .helpers import (
    file_text,
    load_csv,
    load_json,
    word_count,
    strip_html,
    regex_any,
    regex_count,
    floor_to_decimal,
    detect_lang_is_ptbr,
)


# ── Data classes ────────────────────────────────────────────────────────────


@dataclass
class Criterion:
    """Um critério da rubrica."""
    label: str  # ex: "0.5/0.7"
    description: str
    points_obtained: float
    points_max: float


@dataclass
class DimensionResult:
    """Resultado de uma dimensão (C1-C7 ou F1-F4)."""
    code: str
    name: str
    weight: float
    axis: str  # "content" or "form"
    criteria: list[Criterion] = field(default_factory=list)
    notes_critical: list[str] = field(default_factory=list)
    notes_important: list[str] = field(default_factory=list)
    notes_polish: list[str] = field(default_factory=list)

    @property
    def points_obtained(self) -> float:
        return sum(c.points_obtained for c in self.criteria)

    @property
    def percentage(self) -> float:
        if self.weight == 0:
            return 0.0
        return min(100.0, (self.points_obtained / self.weight) * 100)


@dataclass
class AxisReport:
    """Resultado consolidado de um eixo (Conteúdo OU Forma)."""
    axis: str  # "content" or "form"
    dimensions: list[DimensionResult] = field(default_factory=list)
    bonus_points: float = 0.0
    bonus_applied: list[str] = field(default_factory=list)
    raw_total: float = 0.0  # antes de bonificadores
    final_score: float = 0.0  # 0.0 - 10.0 (interno)
    final_letter: str = ""  # apenas para forma: E / D / C / B / A / A+

    def all_critical_notes(self) -> list[str]:
        return [n for d in self.dimensions for n in d.notes_critical]

    def all_important_notes(self) -> list[str]:
        return [n for d in self.dimensions for n in d.notes_important]

    def all_polish_notes(self) -> list[str]:
        return [n for d in self.dimensions for n in d.notes_polish]


@dataclass
class RubricReport:
    """Relatório consolidado dos DOIS eixos."""
    content_report: AxisReport
    form_report: AxisReport

    @property
    def content_score(self) -> float:
        return self.content_report.final_score

    @property
    def form_letter(self) -> str:
        return self.form_report.final_letter


# ── Constantes ──────────────────────────────────────────────────────────────


# Padrões para detectar venues de elite
ELITE_VENUES_PATTERN = re.compile(
    r"IEEE\s+Trans|ACM\s+Trans|TVCG|TPAMI|TSE|CSUR|TOCHI|TOIS|TOG|TODS|"
    r"\bNature\b|\bScience\b|PNAS|Cell|Lancet|NEJM|JAMA|BMJ|"
    r"NeurIPS|ICML|ICLR|CHI|SIGGRAPH|ICSE|FSE|UIST|CVPR|ICCV|ACL|EMNLP|"
    r"ASME|JACS|Angewandte|Chemical Reviews|Chem Soc Rev|"
    r"PRL|PRX|Reviews of Modern Physics|"
    r"Cambridge\s+University|Oxford\s+University|MIT\s+Press|"
    r"PLOS|eLife|Royal\s+Society",
    re.IGNORECASE,
)
# Reescrever para usar source-of-truth de temperature.py (Rodada I).
# rubric.py historicamente teve seu próprio pattern simplificado; agora delegamos.
from .temperature import ELITE_VENUES_PATTERN as _ELITE_FULL  # noqa: E402
ELITE_VENUES_PATTERN = _ELITE_FULL


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
]


# ── Multiplicador de severidade para corpus pequeno (Rodada D) ─────────────
#
# Filosofia: corpus pequeno NÃO É só "menos pontos em C3". Ele invalida
# parcialmente as outras dimensões também. Síntese aprofundada com 4 estudos
# é estruturalmente impossível — não há base para cross-tab profundo, para
# saturação por RQ, para diversidade. O multiplicador reflete isto.
#
# Aplicado em: C2 (Diálogo), C4 (Síntese), C6 (Argumentação).
# NÃO aplicado em: C1 (Problematização), C3 (Qualidade do corpus — este
# já mede o tamanho diretamente), C5 (Coerência), C7 (Semântico).
#
# Calibragem alvo:
#   corpus 4 estudos  → mult ~0.55 (rebaixa C2/C4/C6 substancialmente)
#   corpus 8 estudos  → mult ~0.70
#   corpus 12 estudos → mult ~0.85
#   corpus 15 estudos → mult 1.00 (sem penalização)
#   corpus 30+        → mult 1.00


def corpus_severity_multiplier(n_studies: int, area_threshold: int = 15) -> float:
    """Calcula multiplicador para penalizar análises baseadas em corpus pequeno.

    Curva: sigmoide-like com piso 0.30 em corpus muito pequeno e teto 1.0
    em corpus completo. Sem corpus mínimo, dimensões dependentes ficam
    severamente reduzidas.
    """
    if n_studies <= 0:
        return 0.30
    ratio = n_studies / area_threshold
    if ratio >= 1.0:
        return 1.0
    if ratio <= 0.2:
        return 0.30
    # Linear interpolation entre 0.30 (ratio 0.2) e 1.0 (ratio 1.0)
    return 0.30 + (ratio - 0.2) * (0.70 / 0.8)


# ── Eixo CONTEÚDO — C1 a C7 ────────────────────────────────────────────────


def assess_c1_problematization(content: dict) -> DimensionResult:
    """C1 — Problematização e tese (peso 1.0)."""
    dim = DimensionResult(code="C1", name="Problematização e tese",
                          weight=1.0, axis="content")
    intro = content.get("introduction_html", "") or ""
    intro_text = strip_html(intro)
    rqs = content.get("rqs", [])

    # 0.4 — lacuna identificada
    has_gap = bool(re.search(
        r"\blacuna(s)?\b|\bgap[s]?\b|\bainda não\b|\byet to be\b|"
        r"\bpermanece em aberto\b|\bnot yet\b",
        intro_text, re.IGNORECASE
    ))
    score = 0.4 if has_gap else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.4",
        description="Lacuna identificada na introdução",
        points_obtained=score, points_max=0.4,
    ))
    if not has_gap:
        dim.notes_critical.append(
            "Introdução não identifica lacuna explícita. Adicionar marcadores como "
            "'lacuna', 'ainda não foi investigado', 'permanece em aberto'."
        )

    # 0.3 — RQs explícitas na introdução
    has_rqs_in_intro = bool(re.search(
        r"RQ\s*\d|research question|pergunta\s+de\s+pesquisa",
        intro_text, re.IGNORECASE
    ))
    has_rqs_declared = len(rqs) > 0
    if has_rqs_in_intro and has_rqs_declared:
        score = 0.3
    elif has_rqs_declared:
        score = 0.15
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"RQs declaradas: {len(rqs)} (visíveis na intro: {has_rqs_in_intro})",
        points_obtained=score, points_max=0.3,
    ))
    if score < 0.3:
        dim.notes_important.append(
            "RQs devem ser declaradas explicitamente no final da introdução "
            "(RQ1, RQ2, ...)."
        )

    # 0.3 — contextualização teórica
    intro_words = len(intro_text.split())
    n_refs_in_intro = len(re.findall(r"\[\d+\]|\(\w+,?\s*\d{4}\)", intro))
    if intro_words >= 200 and n_refs_in_intro >= 3:
        score = 0.3
    elif intro_words >= 100 and n_refs_in_intro >= 1:
        score = 0.15
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"Contextualização: {intro_words} palavras, {n_refs_in_intro} citações",
        points_obtained=score, points_max=0.3,
    ))
    if score < 0.3:
        dim.notes_important.append(
            "Expandir introdução com contextualização teórica e ≥3 referências."
        )

    return dim


def assess_c2_dialogue(content: dict, ctx: dict | None = None) -> DimensionResult:
    """C2 — Diálogo entre autores (peso 1.5)."""
    dim = DimensionResult(code="C2", name="Diálogo entre autores",
                          weight=1.5, axis="content")
    synthesis = content.get("synthesis_html", "") or ""
    synthesis_text = strip_html(synthesis)
    n_words = len(synthesis_text.split())

    # Multiplicador de severidade por corpus pequeno
    n_studies = 0
    if ctx and ctx.get("extraction_path"):
        n_studies = len(load_csv(ctx["extraction_path"]))
    is_se_cs = ctx.get("is_se_cs", False) if ctx else False
    is_health = ctx.get("is_health", False) if ctx else False
    threshold = 30 if is_se_cs else 20 if is_health else 15
    sev_mult = corpus_severity_multiplier(n_studies, threshold)

    # 0.6 — densidade de cross-tab markers (ENDURECIDO: alvo 12/1000w em vez de 8/1000w)
    n_crosstab = sum(1 for p in CROSSTAB_MARKERS if re.search(p, synthesis_text, re.IGNORECASE))
    if n_words > 0:
        density = n_crosstab / (n_words / 1000)
    else:
        density = 0
    if density >= 12:
        score = 0.6
    elif density >= 6:
        score = 0.3
    elif density >= 2:
        score = 0.15
    else:
        score = 0.0
    score *= sev_mult  # aplica penalização por corpus
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.6",
        description=f"Densidade cross-tab: {n_crosstab} markers em {n_words} palavras (≈{density:.1f}/1000w; mult={sev_mult:.2f})",
        points_obtained=score, points_max=0.6,
    ))
    if density < 12:
        dim.notes_important.append(
            f"Cross-tabulação esparsa ({density:.1f}/1000w; alvo ≥12). Estudos extraídos "
            "podem ser comparados/contrastados explicitamente na síntese."
        )

    # 0.5 — citações múltiplas em mesmo argumento (ENDURECIDO: alvo 8 em vez de 5)
    n_multi_cite = len(re.findall(
        r"\[\d+(?:,\s*\d+){1,}\]|\(\w+,?\s*\d{4}[;\s]+\w+,?\s*\d{4}",
        synthesis
    ))
    if n_multi_cite >= 8:
        score = 0.5
    elif n_multi_cite >= 4:
        score = 0.25
    elif n_multi_cite >= 1:
        score = 0.10
    else:
        score = 0.0
    score *= sev_mult
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description=f"Citações múltiplas em mesmo argumento: {n_multi_cite} (mult={sev_mult:.2f})",
        points_obtained=score, points_max=0.5,
    ))

    # 0.4 — diversidade de fontes (ENDURECIDO: alvo 15 em vez de 10)
    n_distinct_refs = len(set(re.findall(r"\[(\d+)\]", synthesis)))
    if n_distinct_refs >= 15:
        score = 0.4
    elif n_distinct_refs >= 8:
        score = 0.2
    elif n_distinct_refs >= 3:
        score = 0.10
    else:
        score = 0.0
    # Não aplica sev_mult aqui — a contagem direta já reflete corpus
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description=f"Diversidade: {n_distinct_refs} referências distintas na síntese",
        points_obtained=score, points_max=0.4,
    ))

    return dim


def assess_c3_corpus_quality(content: dict, ctx: dict) -> DimensionResult:
    """C3 — Qualidade do corpus (peso 2.0)."""
    dim = DimensionResult(code="C3", name="Qualidade do corpus",
                          weight=2.0, axis="content")
    extr_rows = load_csv(ctx.get("extraction_path"))
    qa_rows = load_csv(ctx.get("qa_path"))
    n_inc = len(extr_rows)
    is_ptbr = detect_lang_is_ptbr(content)

    # 0.5 — número de estudos (ENDURECIDO: curva mais íngreme; abaixo de 50% = quase zero)
    is_se_cs = ctx.get("is_se_cs", False)
    is_health = ctx.get("is_health", False)
    threshold = 30 if is_se_cs else 20 if is_health else 15
    if n_inc >= threshold:
        score = 0.5
    elif n_inc >= threshold * 0.7:
        # 70-100% → 0.30 a 0.50 (linear)
        score = 0.30 + (n_inc - threshold * 0.7) / (threshold * 0.3) * 0.20
    elif n_inc >= threshold * 0.5:
        # 50-70% → 0.10 a 0.30 (linear)
        score = 0.10 + (n_inc - threshold * 0.5) / (threshold * 0.2) * 0.20
    else:
        # < 50% → quase zero (curva exponencial inversa)
        score = 0.10 * (n_inc / (threshold * 0.5)) ** 2
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description=f"{n_inc} estudos incluídos (mínimo da área: {threshold})",
        points_obtained=score, points_max=0.5,
    ))
    if n_inc < threshold:
        if n_inc < threshold * 0.5:
            dim.notes_critical.append(
                f"CRÍTICO — corpus de {n_inc} estudos é insuficiente. Mínimo da área: {threshold}."
            )
        else:
            dim.notes_important.append(
                f"Considerar ampliar busca (atual: {n_inc}, alvo: {threshold})."
            )

    # 0.6 — venues de elite
    elite_count = 0
    for r in extr_rows:
        venue = (r.get("venue", "") or "") + " " + (r.get("citation", "") or "")
        if ELITE_VENUES_PATTERN.search(venue):
            elite_count += 1
    pct_elite = (elite_count / n_inc * 100) if n_inc else 0
    target_pct = 20 if is_ptbr else 30
    if pct_elite >= target_pct:
        score = 0.6
    elif pct_elite >= target_pct / 2:
        score = 0.6 * (pct_elite / target_pct)
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.6",
        description=f"Venues de elite: {pct_elite:.0f}% (alvo ≥{target_pct}%)",
        points_obtained=score, points_max=0.6,
    ))
    if pct_elite < target_pct:
        dim.notes_important.append(
            f"Aumentar presença de venues de elite (atual: {pct_elite:.0f}%, alvo: ≥{target_pct}%)."
        )

    # 0.3 — saturação por RQ
    rqs_declared = content.get("rqs", [])
    rq_coverage: dict[str, int] = {}
    for r in extr_rows:
        for rq in re.split(r"[,;]\s*", r.get("rq_addressed", "") or ""):
            rq = rq.strip()
            if rq:
                rq_coverage[rq] = rq_coverage.get(rq, 0) + 1
    if rqs_declared and rq_coverage:
        unsatured = [rq for rq, count in rq_coverage.items() if count < 3]
        if not unsatured:
            score = 0.3
        else:
            ratio = (len(rq_coverage) - len(unsatured)) / len(rq_coverage)
            score = 0.3 * ratio
    else:
        score = 0.0
        unsatured = []
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=(f"Saturação por RQ: {len(rq_coverage) - len(unsatured)}/{len(rq_coverage)}"
                     if rq_coverage else "RQs não rastreáveis em extraction.csv"),
        points_obtained=score, points_max=0.3,
    ))

    # 0.3 — diversidade temporal
    years = []
    for r in extr_rows:
        try:
            years.append(int(str(r.get("year", "")).strip()))
        except ValueError:
            continue
    if years:
        span = max(years) - min(years)
        score = 0.3 if span >= 5 else 0.15 if span >= 3 else 0.0
    else:
        score = 0.0
        span = 0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"Span temporal: {span} anos" if years else "anos ausentes",
        points_obtained=score, points_max=0.3,
    ))

    # 0.3 — QA scores médios
    if qa_rows:
        totals = []
        max_seen = 0
        for r in qa_rows:
            v = r.get("consensus_total") or r.get("reviewer1_total") or "0"
            try:
                t = float(v)
                totals.append(t)
                max_seen = max(max_seen, t)
            except (ValueError, TypeError):
                continue
        if totals and max_seen > 0:
            avg_pct = (sum(totals) / len(totals)) / max_seen * 100
            score = 0.3 if avg_pct >= 70 else 0.15 if avg_pct >= 60 else 0.0
        else:
            avg_pct = 0
            score = 0.0
    else:
        avg_pct = 0
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"QA score médio: {avg_pct:.0f}%",
        points_obtained=score, points_max=0.3,
    ))

    return dim


def assess_c4_synthesis(content: dict, ctx: dict | None = None) -> DimensionResult:
    """C4 — Síntese substantiva (peso 2.0)."""
    dim = DimensionResult(code="C4", name="Síntese substantiva",
                          weight=2.0, axis="content")
    synthesis = content.get("synthesis_html", "") or ""
    n_words = word_count(synthesis)
    rqs = content.get("rqs", [])

    # Multiplicador de severidade por corpus pequeno
    n_studies = 0
    if ctx and ctx.get("extraction_path"):
        n_studies = len(load_csv(ctx["extraction_path"]))
    is_se_cs = ctx.get("is_se_cs", False) if ctx else False
    is_health = ctx.get("is_health", False) if ctx else False
    threshold = 30 if is_se_cs else 20 if is_health else 15
    sev_mult = corpus_severity_multiplier(n_studies, threshold)

    # 0.6 — extensão suficiente (ENDURECIDO: alvo 1000 em vez de 800)
    if n_words >= 1000:
        score = 0.6
    elif n_words >= 700:
        # 700-1000 → 0.30 a 0.60 (linear)
        score = 0.30 + (n_words - 700) / 300 * 0.30
    elif n_words >= 500:
        # 500-700 → 0.10 a 0.30 (linear; síntese ainda válida mas modesta)
        score = 0.10 + (n_words - 500) / 200 * 0.20
    else:
        score = 0.0
    score *= sev_mult
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.6",
        description=f"Síntese tem {n_words} palavras (alvo ≥1000; mult={sev_mult:.2f})",
        points_obtained=score, points_max=0.6,
    ))
    if n_words < 1000:
        dim.notes_important.append(
            f"Aprofundar síntese costurando achados extraídos "
            f"(atual: {n_words} palavras, alvo: ≥1000)."
        )

    # 0.7 — RQs cobertas em parágrafos dedicados (mantido)
    rqs_in_synth = 0
    for i, rq in enumerate(rqs, 1):
        if re.search(rf"\bRQ\s*{i}\b", synthesis, re.IGNORECASE):
            rqs_in_synth += 1
    if rqs:
        score = 0.7 * (rqs_in_synth / len(rqs))
    else:
        score = 0.0
    score *= sev_mult
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.7",
        description=f"RQs cobertas com cabeçalho/marcador: {rqs_in_synth}/{len(rqs)} (mult={sev_mult:.2f})",
        points_obtained=score, points_max=0.7,
    ))
    if rqs and rqs_in_synth < len(rqs):
        dim.notes_important.append(
            f"Estruturar síntese com cabeçalho ou marcador para cada RQ "
            f"(faltam {len(rqs) - rqs_in_synth})."
        )

    # 0.4 — cross-tabulação efetiva (ENDURECIDO: alvo 8 em vez de 5)
    synth_text = strip_html(synthesis)
    n_crosstab = sum(1 for p in CROSSTAB_MARKERS if re.search(p, synth_text, re.IGNORECASE))
    if n_crosstab >= 8:
        score = 0.4
    elif n_crosstab >= 4:
        score = 0.2
    elif n_crosstab >= 1:
        score = 0.10
    else:
        score = 0.0
    score *= sev_mult
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description=f"Cross-tabulação: {n_crosstab} marcadores (mult={sev_mult:.2f})",
        points_obtained=score, points_max=0.4,
    ))

    # 0.3 — não-extrapolação (proxy)
    extrap = re.findall(
        r"\bdefinitivamente\b|\bcomprova[a-zçã]+\b|\babsolutamente\b|"
        r"\bproved?\b|\bdefinitively\b|\babsolutely\b",
        synthesis + " " + content.get("conclusion_html", ""),
        re.IGNORECASE
    )
    score = 0.3 if not extrap else 0.15
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"Linguagem proporcional aos dados ({len(extrap)} marcadores de extrapolação)",
        points_obtained=score, points_max=0.3,
    ))
    if extrap:
        dim.notes_polish.append(
            "Revisar uso de 'definitivamente' / 'comprova' / 'absolutamente' — "
            "geralmente extrapolam o que dados de SLR podem afirmar."
        )

    return dim


def assess_c5_coherence(content: dict) -> DimensionResult:
    """C5 — Coerência teórico-metodológica (peso 1.0)."""
    dim = DimensionResult(code="C5", name="Coerência teórico-metodológica",
                          weight=1.0, axis="content")
    rqs = content.get("rqs", [])
    conclusion = content.get("conclusion_html", "") or ""
    conclusion_text = strip_html(conclusion).lower()

    # 0.5 — conclusão responde RQs (espelhamento, ENDURECIDO: requer ≥3 palavras-chave em vez de 2)
    if rqs:
        # Detecção robusta: por número OU por palavras-chave
        stopwords = {"rq", "para", "como", "quais", "qual", "que", "the", "of", "is",
                     "are", "in", "on", "at", "to", "and", "or", "with", "by"}
        n_answered = 0
        for i, rq in enumerate(rqs, 1):
            by_number = bool(re.search(rf"\bRQ\s*{i}\b", conclusion_text))
            rq_clean = re.sub(rf"^RQ\s*{i}[:.\s]+", "", rq, flags=re.IGNORECASE)
            words = [w for w in re.findall(r"\b[\w\u00C0-\u017F'-]+\b", rq_clean.lower())
                     if len(w) >= 4 and w not in stopwords]
            # ENDURECIDO: requer 3 palavras-chave em vez de 2
            by_content = bool(words) and sum(1 for w in words if w in conclusion_text) >= 3
            if by_number or by_content:
                n_answered += 1
        if n_answered == len(rqs):
            score = 0.5
        elif n_answered >= 1:
            # Resposta parcial dá menos peso (era linear, agora curva sub-linear)
            score = 0.5 * (n_answered / len(rqs)) ** 1.5
        else:
            score = 0.0
    else:
        score = 0.0
        n_answered = 0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description=f"Conclusão responde {n_answered}/{len(rqs)} RQs",
        points_obtained=score, points_max=0.5,
    ))

    # 0.3 — threats to validity
    threats = content.get("threats_html", "") or ""
    types_validity = sum(
        1 for t in ["construct", "internal", "external", "conclusion"]
        if re.search(rf"{t}\s+validity|validade\s+(de\s+)?{t}", threats, re.IGNORECASE)
    )
    if types_validity >= 3:
        score = 0.3
    elif types_validity >= 1:
        score = 0.15
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"Threats to validity: {types_validity}/4 tipos",
        points_obtained=score, points_max=0.3,
    ))
    if types_validity < 3:
        dim.notes_important.append(
            "Cobrir os 4 tipos de validade (construct, internal, external, conclusion)."
        )

    # 0.2 — abstract estruturado
    abstract_text = strip_html(content.get("abstract_html", "") or "")
    n_abs = len(abstract_text.split())
    structured_markers = sum(
        1 for p in [r"contexto|background|objetivo|aim|objective",
                    r"método|method", r"resultados?|results",
                    r"conclus[aã]o|conclusion"]
        if re.search(p, abstract_text, re.IGNORECASE)
    )
    if 200 <= n_abs <= 320 and structured_markers >= 3:
        score = 0.2
    elif n_abs >= 150 and structured_markers >= 2:
        score = 0.1
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.2",
        description=f"Abstract: {n_abs} palavras, {structured_markers}/4 elementos",
        points_obtained=score, points_max=0.2,
    ))

    return dim


def assess_c6_argumentation(content: dict, ctx: dict) -> DimensionResult:
    """C6 — Argumentação e originalidade aparente (peso 1.5)."""
    dim = DimensionResult(code="C6", name="Argumentação e originalidade",
                          weight=1.5, axis="content")
    discussion = content.get("discussion_html", "") or ""
    extr_rows = load_csv(ctx.get("extraction_path"))
    n_studies = len(extr_rows)

    # Multiplicador de severidade por corpus pequeno
    is_se_cs = ctx.get("is_se_cs", False)
    is_health = ctx.get("is_health", False)
    threshold = 30 if is_se_cs else 20 if is_health else 15
    sev_mult = corpus_severity_multiplier(n_studies, threshold)

    # 0.5 — guidelines numeradas na discussão (ENDURECIDO: alvo 7 em vez de 5)
    n_guidelines = regex_count(discussion, r"\bG\d|guideline\s*\d|diretriz\s*\d")
    if n_guidelines >= 7:
        score = 0.5
    elif n_guidelines >= 4:
        score = 0.25
    elif n_guidelines >= 2:
        score = 0.10
    else:
        score = 0.0
    score *= sev_mult
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description=f"Guidelines numeradas: {n_guidelines} (mult={sev_mult:.2f})",
        points_obtained=score, points_max=0.5,
    ))
    if n_guidelines < 7:
        dim.notes_important.append(
            f"Estruturar discussão em torno de guidelines numeradas (atual: {n_guidelines}, alvo: ≥7). "
            "Guidelines devem ter base nos achados extraídos — Claude não inventa."
        )

    # 0.3 — diversidade de tipos de estudo no corpus (ENDURECIDO: alvo 5 em vez de 4)
    types = set()
    for r in extr_rows:
        t = (r.get("study_type", "") or r.get("methods", "") or "").lower().split(",")[0].strip()
        if t:
            types.add(t)
    if len(types) >= 5:
        score = 0.3
    elif len(types) >= 3:
        score = 0.15
    elif len(types) >= 2:
        score = 0.05
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"Diversidade de tipos: {len(types)}",
        points_obtained=score, points_max=0.3,
    ))

    # 0.4 — diversidade geográfica (ENDURECIDO: alvo 7 em vez de 5)
    countries = set()
    for r in extr_rows:
        c = (r.get("country", "") or r.get("country_authors", "") or "").strip().lower()
        if c:
            countries.add(c)
    if len(countries) >= 7:
        score = 0.4
    elif len(countries) >= 4:
        score = 0.2
    elif len(countries) >= 2:
        score = 0.05
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description=f"Diversidade geográfica: {len(countries)} países",
        points_obtained=score, points_max=0.4,
    ))

    # 0.3 — sinalização de limitações declaradas (>=3) — não aplica sev_mult
    not_items = content.get("not_this_version_items", [])
    n_not = len(not_items) if isinstance(not_items, list) else 0
    score = 0.3 if n_not >= 3 else 0.15 if n_not >= 1 else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"Limitações declaradas em §09: {n_not}",
        points_obtained=score, points_max=0.3,
    ))

    return dim


def assess_c7_semantic(content: dict) -> DimensionResult:
    """C7 — Análise semântica (peso 1.0).

    Esta dimensão depende do `qualitative-content-review.md` produzido pelo
    Claude no Claude Chat. Em modo standalone, retorna nota 0 com explicação.
    """
    dim = DimensionResult(code="C7", name="Análise semântica (Claude Chat)",
                          weight=1.0, axis="content")
    review = content.get("qualitative_review", None)
    if not review:
        dim.criteria.append(Criterion(
            label="0.0/1.0",
            description="C7 não disponível — modo standalone OU review ausente. "
                        "Disponível apenas no Claude Chat.",
            points_obtained=0.0, points_max=1.0,
        ))
        dim.notes_polish.append(
            "C7 (análise semântica) requer execução do skill no Claude Chat. "
            "O arquivo qualitative-content-review.md deve estar no pacote."
        )
        return dim

    # review é um dict com 4 análises numeradas
    sub_scores = []
    for key, label in [
        ("synthesis_quality", "Qualidade da síntese"),
        ("argumentation", "Argumentação"),
        ("bibliography_canonical", "Bibliografia canônica"),
        ("originality_apparent", "Originalidade aparente"),
    ]:
        sub = review.get(key, {})
        sub_score = sub.get("score", 0)
        try:
            sub_score = float(sub_score)
        except (ValueError, TypeError):
            sub_score = 0
        sub_scores.append(sub_score)
        # Cada sub-análise vale 0.25 (4 × 0.25 = 1.0)
        dim_score = 0.25 * (sub_score / 10.0)
        dim.criteria.append(Criterion(
            label=f"{dim_score:.3f}/0.25",
            description=f"{label}: {sub_score}/10",
            points_obtained=dim_score, points_max=0.25,
        ))

    return dim


def compute_content_bonus(*, package_dir: Path, content: dict) -> tuple[float, list[str]]:
    """Bonificadores no eixo Conteúdo (até +0.3)."""
    bonus = 0.0
    applied = []
    protocol = file_text(package_dir / "protocol.md")
    readme = file_text(package_dir / "README.md")

    if re.search(r"zenodo\.org/.{1,30}\d+|10\.5281/zenodo\.\d+", protocol + readme):
        bonus += 0.1
        applied.append("Pré-registro Zenodo identificado (+0.1)")

    if re.search(r"snowball|wohlin", protocol, re.IGNORECASE):
        bonus += 0.1
        applied.append("Snowballing executado (+0.1)")

    venues = content.get("venues") or []
    has_diamond = any(
        "diamond" in (v.get("access_model", "") or "").lower() for v in venues
    )
    if has_diamond:
        bonus += 0.1
        applied.append("Venue OA Diamond sugerido (+0.1)")

    return min(bonus, 0.3), applied


def assess_content_axis(
    *, package_dir: Path, content: dict, ctx: dict,
) -> AxisReport:
    """Avalia o eixo CONTEÚDO (escala 0.0-10.0)."""
    dimensions = [
        assess_c1_problematization(content),
        assess_c2_dialogue(content, ctx=ctx),
        assess_c3_corpus_quality(content, ctx),
        assess_c4_synthesis(content, ctx=ctx),
        assess_c5_coherence(content),
        assess_c6_argumentation(content, ctx),
        assess_c7_semantic(content),
    ]
    raw = sum(d.points_obtained for d in dimensions)
    bonus, bonus_applied = compute_content_bonus(package_dir=package_dir, content=content)
    final = floor_to_decimal(min(raw + bonus, 10.0))

    return AxisReport(
        axis="content",
        dimensions=dimensions,
        bonus_points=bonus,
        bonus_applied=bonus_applied,
        raw_total=raw,
        final_score=final,
    )


# ── Eixo FORMA — F1 a F4 ────────────────────────────────────────────────────


def assess_f1_structure(*, package_dir: Path, content: dict, html_content: str) -> DimensionResult:
    """F1 — Estrutura ABNT/IEEE/Vancouver/APA (peso 2.5)."""
    dim = DimensionResult(code="F1", name="Estrutura formal",
                          weight=2.5, axis="form")

    # 0.5 — todas as seções §00-§10 não-vazias
    sections = ["abstract_html", "introduction_html", "background_html",
                "methodology_html", "synthesis_html", "discussion_html",
                "threats_html", "conclusion_html"]
    nonempty = sum(1 for k in sections if (content.get(k) or "").strip())
    score = 0.5 * (nonempty / len(sections))
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description=f"Seções narrativas: {nonempty}/{len(sections)}",
        points_obtained=score, points_max=0.5,
    ))

    # 0.4 — figuras e tabelas numeradas
    n_figs = len(re.findall(r"<figure", html_content, re.IGNORECASE))
    n_tables = len(re.findall(r"<table", html_content, re.IGNORECASE))
    n_figcaptions = len(re.findall(r"<figcaption", html_content, re.IGNORECASE))
    n_thead = len(re.findall(r"<thead|<caption", html_content, re.IGNORECASE))
    score = 0.4 if (n_figs == n_figcaptions and n_tables <= n_thead + 1) else 0.2
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.4",
        description=f"Figs ({n_figs}/{n_figcaptions} captions), tabelas ({n_tables})",
        points_obtained=score, points_max=0.4,
    ))

    # 0.4 — referências com formatação consistente
    refs = content.get("references", [])
    if refs:
        with_doi = sum(1 for r in refs if r.get("doi"))
        score = 0.4 * (with_doi / len(refs))
    else:
        score = 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description=f"Refs com DOI: {sum(1 for r in refs if r.get('doi')) if refs else 0}/{len(refs)}",
        points_obtained=score, points_max=0.4,
    ))

    # 0.4 — abstract estruturado em norma
    abstract_text = strip_html(content.get("abstract_html", "") or "")
    n_abs = len(abstract_text.split())
    structured = sum(
        1 for p in [r"contexto|background|objetivo|aim|objective",
                    r"método|method", r"resultados?|results",
                    r"conclus[aã]o|conclusion"]
        if re.search(p, abstract_text, re.IGNORECASE)
    )
    score = 0.4 if (200 <= n_abs <= 320 and structured >= 3) else 0.2 if n_abs >= 150 else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.4",
        description=f"Abstract estruturado: {n_abs} palavras, {structured}/4 elementos",
        points_obtained=score, points_max=0.4,
    ))

    # 0.4 — sumário/lista/numeração consistente
    has_toc = "id=\"toc\"" in html_content or "id='toc'" in html_content
    has_nav = "<nav" in html_content
    score = 0.4 if (has_toc or has_nav) else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.4",
        description="Sumário/navegação presente",
        points_obtained=score, points_max=0.4,
    ))

    # 0.4 — citações ABNT em CAIXA ALTA quando aplicável
    is_ptbr = detect_lang_is_ptbr(content)
    if is_ptbr:
        # Verificar amostra: pelo menos uma citação no texto principal
        # com sobrenome em CAIXA ALTA
        synth = content.get("synthesis_html", "") or ""
        n_caps = len(re.findall(r"\([A-ZÀ-Ý]{2,}", synth))
        n_lower = len(re.findall(r"\([A-Z][a-zà-ÿ]+,\s*\d{4}", synth))
        if n_caps + n_lower == 0:
            score = 0.2  # Pode estar usando [n], aceita
        elif n_caps >= n_lower:
            score = 0.4
        else:
            score = 0.2
    else:
        score = 0.4
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.4",
        description="Citações conforme norma do idioma",
        points_obtained=score, points_max=0.4,
    ))

    return dim


def assess_f2_compliance(*, package_dir: Path, content: dict, ctx: dict) -> DimensionResult:
    """F2 — Compliance ético-legal (peso 3.0)."""
    dim = DimensionResult(code="F2", name="Compliance ético-legal",
                          weight=3.0, axis="form")
    is_ptbr = detect_lang_is_ptbr(content)
    readme = file_text(package_dir / "README.md")
    compliance = file_text(package_dir / "compliance-checklist.md")
    text_blob = readme + " " + compliance + " " + file_text(package_dir / "protocol.md")
    ai_decl = content.get("ai_declaration") or {}

    # 0.8 — Declaração de IA completa
    required = ["tool", "provider", "interface", "stages",
                "purpose_per_stage", "human_oversight", "authors_responsible"]
    filled = sum(1 for f in required if ai_decl.get(f))
    score = 0.8 * (filled / len(required))
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.8",
        description=f"Declaração IA: {filled}/{len(required)} campos",
        points_obtained=score, points_max=0.8,
    ))

    # 0.5 — IA NÃO listada como autora
    score = 0.5  # E1 já elimina se falha; aqui pontuamos por completude
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.5",
        description="IA NÃO listada como autora",
        points_obtained=score, points_max=0.5,
    ))

    if is_ptbr:
        # 0.4 — Documento de Área CAPES referenciado
        has_capes = bool(re.search(
            r"Documento\s+de\s+Área|CAPES.{0,30}(área|Sucupira)",
            text_blob, re.IGNORECASE
        ))
        score = 0.4 if has_capes else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.4",
            description="Documento de Área CAPES referenciado",
            points_obtained=score, points_max=0.4,
        ))

        # 0.4 — CEP/CONEP declarado
        has_cep = bool(re.search(
            r"CEP|CONEP|CNS\s*466|CNS\s*510|Resolução\s*466|Resolução\s*510",
            text_blob, re.IGNORECASE
        ))
        score = 0.4 if has_cep else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.4",
            description="Status CEP/CONEP declarado",
            points_obtained=score, points_max=0.4,
        ))

        # 0.4 — LGPD considerada
        has_lgpd = bool(re.search(r"LGPD|13\.709|dados\s+pessoa", text_blob, re.IGNORECASE))
        score = 0.4 if has_lgpd else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.4",
            description="LGPD considerada",
            points_obtained=score, points_max=0.4,
        ))

        # 0.3 — LDA / licença CC-BY-4.0
        has_license = (package_dir / "LICENSE").exists() or bool(re.search(
            r"CC[\s-]BY[\s-]?4\.?0|9\.610|creative\s*commons",
            text_blob, re.IGNORECASE
        ))
        score = 0.3 if has_license else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.3",
            description="LDA: licença declarada (CC-BY-4.0)",
            points_obtained=score, points_max=0.3,
        ))

        # 0.2 — Vedação a projetos terceiros
        has_vedacao = bool(re.search(
            r"projeto.*terceir|veda(ção|do).*IAG|art\.?\s*9.*IAG",
            text_blob, re.IGNORECASE
        ))
        score = 0.2 if has_vedacao else 0.1
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.2",
            description="Vedação Portaria CNPq art. 9",
            points_obtained=score, points_max=0.2,
        ))
    else:
        # EN
        has_cope = bool(re.search(r"COPE|publicationethics", text_blob, re.IGNORECASE))
        has_icmje = bool(re.search(r"ICMJE", text_blob, re.IGNORECASE))
        score = 0.6 if (has_cope and has_icmje) else 0.3 if (has_cope or has_icmje) else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.6",
            description="COPE + ICMJE referenced",
            points_obtained=score, points_max=0.6,
        ))

        score = 0.4
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.4",
            description="AI-generated images declared/absent",
            points_obtained=score, points_max=0.4,
        ))

        has_coi = bool(re.search(r"conflict of interest|competing interests", text_blob, re.IGNORECASE))
        has_funding = bool(re.search(r"funding|grant|fellowship", text_blob, re.IGNORECASE))
        score = 0.4 if (has_coi and has_funding) else 0.2 if (has_coi or has_funding) else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.4",
            description="CoI + Funding statements",
            points_obtained=score, points_max=0.4,
        ))

        has_confid = bool(re.search(r"confidentiality|do not upload", text_blob, re.IGNORECASE))
        score = 0.3 if has_confid else 0.0
        dim.criteria.append(Criterion(
            label=f"{score:.1f}/0.3",
            description="Peer-review confidentiality",
            points_obtained=score, points_max=0.3,
        ))

    return dim


def assess_f3_methodology_procedural(*, package_dir: Path, content: dict, ctx: dict) -> DimensionResult:
    """F3 — Rigor metodológico procedimental (peso 2.5)."""
    dim = DimensionResult(code="F3", name="Rigor metodológico procedimental",
                          weight=2.5, axis="form")
    protocol = file_text(package_dir / "protocol.md")
    readme = file_text(package_dir / "README.md")

    # 0.6 — protocolo com PICO/PICOC + CI/CE + strings
    has_pico = bool(re.search(r"PICO|PICOC|PEO|SPIDER|PCC|CIMO", protocol, re.IGNORECASE))
    has_ci = bool(re.search(r"CI[1-9]|crit[eé]ri[oa]s?\s+de\s+inclus", protocol, re.IGNORECASE))
    has_ce = bool(re.search(r"CE[1-9]|crit[eé]ri[oa]s?\s+de\s+exclus", protocol, re.IGNORECASE))
    has_strings = bool(re.search(
        r"TITLE-ABS|TS=|abs:|all:|search_query|MeSH Terms",
        protocol, re.IGNORECASE
    ))
    score = 0.6 if all([has_pico, has_ci, has_ce, has_strings]) else (
        0.3 if (has_pico and (has_ci or has_ce)) else 0.0
    )
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.6",
        description="Protocolo: PICO/PICOC + CI/CE + strings",
        points_obtained=score, points_max=0.6,
    ))

    # 0.5 — PRISMA flow coerente
    flow_data = load_json(package_dir / "prisma-flow.json")
    coherent = False
    if flow_data:
        try:
            n_id = sum(d.get("n", 0) for d in flow_data["identification"]["from_databases"])
            n_dedup = flow_data.get("after_dedup", 0)
            n_screened = flow_data["screening"]["screened"]
            n_assessed = flow_data["eligibility"]["assessed"]
            n_inc = flow_data["included"]["studies"]
            coherent = (n_id >= n_dedup >= n_screened >= n_assessed >= n_inc) and n_inc > 0
        except (KeyError, TypeError):
            coherent = False
    score = 0.5 if coherent else 0.25 if flow_data else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description="PRISMA flow numericamente coerente",
        points_obtained=score, points_max=0.5,
    ))

    # 0.5 — ≥ 5 bases
    searches = ctx.get("searches") or {}
    n_bases = 0
    if isinstance(searches, dict):
        per_db = searches.get("per_database", [])
        n_bases = len(per_db) if isinstance(per_db, list) else 0
    elif isinstance(searches, list):
        n_bases = len(searches)
    score = 0.5 if n_bases >= 5 else 0.25 if n_bases >= 3 else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description=f"≥ 5 bases consultadas (atual: {n_bases})",
        points_obtained=score, points_max=0.5,
    ))

    # 0.3 — snowballing
    has_snowball = bool(re.search(
        r"snowball|wohlin|forward.*citation|backward.*citation",
        protocol, re.IGNORECASE
    ))
    score = 0.3 if has_snowball else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.3",
        description="Snowballing (Wohlin 2014)",
        points_obtained=score, points_max=0.3,
    ))

    # 0.4 — QA cobertura
    qa_rows = load_csv(ctx.get("qa_path"))
    extr_rows = load_csv(ctx.get("extraction_path"))
    n_extr = len(extr_rows)
    n_qa = len(qa_rows)
    if n_extr > 0:
        coverage = n_qa / n_extr
    else:
        coverage = 0.0
    score = 0.4 * min(1.0, coverage)
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description=f"QA aplicada a {n_qa}/{n_extr} estudos",
        points_obtained=score, points_max=0.4,
    ))

    # 0.2 — threshold + kappa documentados
    has_threshold = bool(re.search(r"threshold|corte|≥\s*\d|>=\s*\d", protocol, re.IGNORECASE))
    has_kappa = bool(re.search(r"kappa|Cohen.{0,5}kappa", protocol + " " + readme, re.IGNORECASE))
    score = 0.2 if (has_threshold and has_kappa) else 0.1 if (has_threshold or has_kappa) else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.2",
        description=f"Threshold QA + kappa (T={has_threshold}, K={has_kappa})",
        points_obtained=score, points_max=0.2,
    ))

    return dim


def assess_f4_presentation(*, package_dir: Path, content: dict,
                            html_content: str, version: str) -> DimensionResult:
    """F4 — Apresentação e auditabilidade (peso 2.0)."""
    dim = DimensionResult(code="F4", name="Apresentação e auditabilidade",
                          weight=2.0, axis="form")

    # 0.5 — HTML interativo
    has_toggles = all(t in html_content for t in
                       ["toggle-annotations", "toggle-dark", "toggle-collapse-all"])
    has_search = 'id="q"' in html_content or "id='q'" in html_content
    has_d3 = "d3@7" in html_content or "d3.v7" in html_content or "d3.min.js" in html_content
    score = 0.5 if (has_toggles and has_search and has_d3) else 0.25 if has_toggles else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.5",
        description="HTML interativo (toggles + busca + D3)",
        points_obtained=score, points_max=0.5,
    ))

    # 0.4 — pacote completo
    expected = ["manuscript.html", "protocol.md", "searches.json", "screening.csv",
                "quality-appraisal.csv", "extraction.csv", "prisma-flow.svg",
                "references.bib", "README.md", "ai-declaration.md",
                "venue-suggestions.md", "compliance-checklist.md"]
    present = [f for f in expected if (package_dir / f).exists()]
    score = 0.4 * (len(present) / len(expected))
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description=f"Artefatos do pacote: {len(present)}/{len(expected)}",
        points_obtained=score, points_max=0.4,
    ))

    # 0.4 — README com hashes + changelog
    readme = file_text(package_dir / "README.md")
    has_hashes = "sha256" in readme.lower()
    has_changelog = bool(re.search(r"changelog|mudanças|changes", readme, re.IGNORECASE))
    score = 0.4 if (has_hashes and has_changelog) else 0.2 if (has_hashes or has_changelog) else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.4",
        description="README: hashes SHA-256 + changelog",
        points_obtained=score, points_max=0.4,
    ))

    # 0.3 — SemVer no header E footer
    in_header = f"v{version}" in html_content[:8000]
    in_footer = f"v{version}" in html_content[-3000:]
    score = 0.3 if (in_header and in_footer) else 0.15 if (in_header or in_footer) else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.2f}/0.3",
        description=f"SemVer v{version} em header e footer",
        points_obtained=score, points_max=0.3,
    ))

    # 0.4 — §09 com ≥ 3 itens
    not_items = content.get("not_this_version_items", [])
    n = len(not_items) if isinstance(not_items, list) else 0
    score = 0.4 if n >= 3 else 0.2 if n >= 1 else 0.0
    dim.criteria.append(Criterion(
        label=f"{score:.1f}/0.4",
        description=f"§09 'O que esta versão NÃO é': {n} itens",
        points_obtained=score, points_max=0.4,
    ))

    return dim


def points_to_letter(points: float) -> str:
    """Mapeia 0.0-10.0 → letra E / D / C / B / A / A+."""
    if points >= 9.6:
        return "A+"
    elif points >= 8.6:
        return "A"
    elif points >= 7.0:
        return "B"
    elif points >= 5.0:
        return "C"
    elif points >= 3.0:
        return "D"
    else:
        return "E"


def assess_form_axis(
    *, package_dir: Path, content: dict, html_content: str,
    version: str, ctx: dict,
) -> AxisReport:
    """Avalia o eixo FORMA (escala E/D/C/B/A/A+)."""
    dimensions = [
        assess_f1_structure(package_dir=package_dir, content=content, html_content=html_content),
        assess_f2_compliance(package_dir=package_dir, content=content, ctx=ctx),
        assess_f3_methodology_procedural(package_dir=package_dir, content=content, ctx=ctx),
        assess_f4_presentation(package_dir=package_dir, content=content,
                               html_content=html_content, version=version),
    ]
    raw = sum(d.points_obtained for d in dimensions)
    final = floor_to_decimal(min(raw, 10.0))

    return AxisReport(
        axis="form",
        dimensions=dimensions,
        bonus_points=0.0,
        bonus_applied=[],
        raw_total=raw,
        final_score=final,
        final_letter=points_to_letter(final),
    )


# ── Orquestração ───────────────────────────────────────────────────────────


def assess_all(
    *,
    package_dir: Path,
    content: dict,
    html_content: str,
    extraction_path: Path,
    qa_path: Path,
    searches: dict | list | None,
    version: str,
    is_se_cs: bool = False,
    is_health: bool = False,
) -> RubricReport:
    """Aplica os DOIS eixos. NÃO checa eliminatórios — isso é responsabilidade
    de eliminators.run_all_eliminators chamado antes."""
    ctx = {
        "is_se_cs": is_se_cs,
        "is_health": is_health,
        "extraction_path": extraction_path,
        "qa_path": qa_path,
        "searches": searches,
    }
    content_report = assess_content_axis(
        package_dir=package_dir, content=content, ctx=ctx,
    )
    form_report = assess_form_axis(
        package_dir=package_dir, content=content, html_content=html_content,
        version=version, ctx=ctx,
    )
    return RubricReport(content_report=content_report, form_report=form_report)
