"""
ignorantia.assessor.temperature — Termômetro 0-1 baseado em 4 critérios mensuráveis.

Os 4 critérios derivam dos requisitos das grandes editoras/institutos científicos
(Elsevier, Nature Springer, Wiley, IEEE, ACM, Lancet, BMJ, etc.):

  T1 — Cumprimento do reporting guideline aplicável (PRISMA / Kitchenham / Bluebook)
  T2 — Compliance com limites quantitativos (plágio, extensão, abstract)
  T3 — Profundidade do corpus + venues elite
  T4 — Análise semântica C7 (quando disponível)

Pesos:
  Com C7 disponível:    T1=30%, T2=20%, T3=30%, T4=20%
  Sem C7 (standalone):  T1=37,5%, T2=25%, T3=37,5% (T4 redistribuído)

A temperatura é número 0-1 SEM mapeamento para Qualis/Quartil. Esse mapeamento
fica para a Sprint Badge ao final da v2.0.0, quando faremos calibragem empírica
contra ≥120 papers reais (15+ por estrato por área) via arXiv + PubMed Central +
SciELO Brasil.

Limitações da temperatura como está:
- Score de 0.7 não significa "B1"; significa "este trabalho cumpre 70% dos critérios
  mensuráveis das grandes editoras".
- Sem amostragem empírica, qualquer mapeamento para estrato seria arbitrário.

Por isso, no JSON de saída, a temperatura aparece como número 0-1 com tooltip
explicando os 4 critérios.
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
    detect_lang_is_ptbr,
)


@dataclass
class TemperatureCriterion:
    """Um dos 4 critérios T1-T4."""
    code: str  # T1, T2, T3, T4
    name: str
    score_0_1: float  # 0.0 a 1.0
    weight: float  # peso na composição final
    components: list[dict] = field(default_factory=list)  # sub-detalhes


@dataclass
class TemperatureReport:
    """Relatório consolidado da temperatura."""
    criteria: list[TemperatureCriterion] = field(default_factory=list)
    final_temperature: float = 0.0  # 0-1
    c7_available: bool = False
    weights_used: dict = field(default_factory=dict)


# ── T1 — Cumprimento do reporting guideline ────────────────────────────────


def assess_t1_reporting_guideline(
    *, package_dir: Path, content: dict
) -> TemperatureCriterion:
    """T1: Cumprimento do reporting guideline aplicável.

    Para SLR (caso geral): PRISMA-2020 com 27 itens + flow diagram.
    Detecta: presença do flow JSON/SVG, coerência numérica, menção aos itens
    do checklist no protocolo/manuscrito.
    """
    components = []
    score_total = 0.0
    max_total = 0.0

    # Subitem 1.1 — PRISMA flow diagram presente E coerente (peso 0.35)
    flow_data = load_json(package_dir / "prisma-flow.json")
    flow_svg_exists = (package_dir / "prisma-flow.svg").exists()
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
    if coherent and flow_svg_exists:
        s = 0.35
    elif flow_data and flow_svg_exists:
        s = 0.20
    elif flow_svg_exists or flow_data:
        s = 0.10
    else:
        s = 0.0
    score_total += s
    max_total += 0.35
    components.append({
        "name": "PRISMA flow presente e coerente",
        "score": s,
        "max": 0.35,
        "detail": (f"flow data {'OK' if flow_data else 'ausente'}, "
                   f"SVG {'OK' if flow_svg_exists else 'ausente'}, "
                   f"coerência {'OK' if coherent else 'falha'}")
    })

    # Subitem 1.2 — Protocolo PRISMA-compliant (peso 0.30)
    protocol = file_text(package_dir / "protocol.md")
    has_pico = bool(re.search(r"PICO|PICOC|PEO|SPIDER|PCC|CIMO", protocol, re.IGNORECASE))
    has_ci = bool(re.search(r"CI[1-9]|crit[eé]ri[oa]s?\s+de\s+inclus", protocol, re.IGNORECASE))
    has_ce = bool(re.search(r"CE[1-9]|crit[eé]ri[oa]s?\s+de\s+exclus", protocol, re.IGNORECASE))
    has_strings = bool(re.search(
        r"TITLE-ABS|TS=|abs:|all:|search_query|MeSH Terms",
        protocol, re.IGNORECASE
    ))
    n_components = sum([has_pico, has_ci, has_ce, has_strings])
    s = 0.30 * (n_components / 4)
    score_total += s
    max_total += 0.30
    components.append({
        "name": "Protocolo PRISMA-compliant (PICO + CI + CE + strings)",
        "score": s,
        "max": 0.30,
        "detail": f"{n_components}/4 componentes detectados",
    })

    # Subitem 1.3 — Itens estruturais (abstract estruturado, métodos descritos) (peso 0.20)
    abstract = strip_html(content.get("abstract_html", "") or "")
    n_abs = len(abstract.split())
    structured = sum(
        1 for p in [r"contexto|background|objetivo|aim|objective",
                    r"método|method", r"resultados?|results",
                    r"conclus[aã]o|conclusion"]
        if re.search(p, abstract, re.IGNORECASE)
    )
    methodology = content.get("methodology_html", "") or ""
    has_methodology = bool(strip_html(methodology).strip())
    abstract_ok = (200 <= n_abs <= 320 and structured >= 3)
    if abstract_ok and has_methodology:
        s = 0.20
    elif (n_abs >= 150 and structured >= 2) and has_methodology:
        s = 0.10
    elif has_methodology:
        s = 0.05
    else:
        s = 0.0
    score_total += s
    max_total += 0.20
    components.append({
        "name": "Abstract estruturado + metodologia descrita",
        "score": s,
        "max": 0.20,
        "detail": f"abstract {n_abs}w, {structured}/4 elementos; metodologia {'OK' if has_methodology else 'ausente'}",
    })

    # Subitem 1.4 — Threats to validity discutidos (peso 0.15)
    threats = content.get("threats_html", "") or ""
    types_validity = sum(
        1 for t in ["construct", "internal", "external", "conclusion"]
        if re.search(rf"{t}\s+validity|validade\s+(de\s+)?{t}", threats, re.IGNORECASE)
    )
    s = 0.15 * (types_validity / 4)
    score_total += s
    max_total += 0.15
    components.append({
        "name": "Threats to validity (4 tipos)",
        "score": s,
        "max": 0.15,
        "detail": f"{types_validity}/4 tipos discutidos",
    })

    return TemperatureCriterion(
        code="T1",
        name="Reporting guideline (PRISMA-2020)",
        score_0_1=score_total / max_total if max_total > 0 else 0.0,
        weight=0.30,
        components=components,
    )


# ── T2 — Compliance com limites quantitativos ──────────────────────────────


def assess_t2_quantitative_compliance(
    *, content: dict, plagiarism_summary: dict | None
) -> TemperatureCriterion:
    """T2: Compliance com limites quantitativos do venue elite típico.

    - Plágio: similaridade < 20% (limite IEEE Trans on AI, comum a outros)
    - Extensão: dentro de limites razoáveis (< 30k palavras para SLR)
    - Abstract: 200-300 palavras com elementos estruturados
    """
    components = []
    score_total = 0.0
    max_total = 0.0

    # Subitem 2.1 — Plágio dentro do limite (peso 0.40)
    if plagiarism_summary:
        n_critical = plagiarism_summary.get("critical_matches", 0)
        n_warning = plagiarism_summary.get("warning_matches", 0)
        if n_critical > 0:
            s = 0.0  # Plágio crítico bloqueia tudo
        elif n_warning >= 3:
            s = 0.20
        elif n_warning >= 1:
            s = 0.30
        else:
            s = 0.40
    else:
        s = 0.20  # Não foi avaliado
    score_total += s
    max_total += 0.40
    components.append({
        "name": "Plágio < 20% (limite IEEE/COPE)",
        "score": s,
        "max": 0.40,
        "detail": (f"{plagiarism_summary.get('critical_matches', 0)} críticos, "
                   f"{plagiarism_summary.get('warning_matches', 0)} avisos"
                   if plagiarism_summary else "não avaliado"),
    })

    # Subitem 2.2 — Extensão razoável (peso 0.30)
    total_words = sum(
        word_count(content.get(k, "") or "")
        for k in ["abstract_html", "introduction_html", "background_html",
                  "methodology_html", "synthesis_html", "discussion_html",
                  "threats_html", "conclusion_html"]
    )
    if 5000 <= total_words <= 30000:
        s = 0.30
    elif 3000 <= total_words < 5000:
        s = 0.20
    elif 30000 < total_words <= 40000:
        s = 0.20
    elif total_words < 3000:
        s = 0.10
    else:
        s = 0.05
    score_total += s
    max_total += 0.30
    components.append({
        "name": "Extensão dentro de limites editoriais",
        "score": s,
        "max": 0.30,
        "detail": f"{total_words} palavras (alvo: 5000-30000)",
    })

    # Subitem 2.3 — Abstract 200-300 palavras estruturado (peso 0.30)
    abstract = strip_html(content.get("abstract_html", "") or "")
    n_abs = len(abstract.split())
    structured = sum(
        1 for p in [r"contexto|background|objetivo|aim|objective",
                    r"método|method", r"resultados?|results",
                    r"conclus[aã]o|conclusion"]
        if re.search(p, abstract, re.IGNORECASE)
    )
    if 200 <= n_abs <= 300 and structured == 4:
        s = 0.30
    elif 200 <= n_abs <= 320 and structured >= 3:
        s = 0.20
    elif n_abs >= 150 and structured >= 2:
        s = 0.10
    else:
        s = 0.0
    score_total += s
    max_total += 0.30
    components.append({
        "name": "Abstract 200-300 palavras + 4 elementos",
        "score": s,
        "max": 0.30,
        "detail": f"{n_abs} palavras, {structured}/4 elementos",
    })

    return TemperatureCriterion(
        code="T2",
        name="Compliance quantitativo (limites editoriais)",
        score_0_1=score_total / max_total if max_total > 0 else 0.0,
        weight=0.20,
        components=components,
    )


# ── T3 — Profundidade do corpus + venues elite ─────────────────────────────


ELITE_VENUES_PATTERN = re.compile(
    r"IEEE\s+Trans|ACM\s+Trans|TVCG|TPAMI|TSE|CSUR|TOCHI|TOSEM|TIIS|TIST|TODS|TOG|TOPLAS|TOIS|"
    r"\bNature\b|\bScience\b|PNAS|Cell|Lancet|NEJM|JAMA|BMJ|"
    r"NeurIPS|ICML|ICLR|CHI|SIGGRAPH|ICSE|FSE|UIST|CVPR|ICCV|ACL|EMNLP|JMLR|"
    r"Computers\s*&\s*Education|Cadernos\s+de\s+Saúde\s+Pública|"
    r"Educação\s*&\s*Pesquisa|Br(itish)?\s*J(ournal)?\s*(?:of\s+)?Educational\s*Technology|"
    r"Review\s*of\s*Educational\s*Research|"
    r"American\s+Educational\s+Research\s+Journal|"
    r"Educational\s+Researcher|"
    r"J(ournal)?\s*of\s*Educational\s*Psychology|"
    r"Psychological\s+Bulletin|Psychological\s+Review|"
    r"Annual\s+Review\s+of\s+Psychology|"
    r"Trends\s+in\s+Cognitive\s+Sciences|"
    r"PLOS|eLife|"
    r"Annals\s+of\s+Internal\s+Medicine|"
    r"PLOS\s+Medicine|"
    r"Cochrane\s+Database|"
    r"Lancet\s+Public\s+Health|Lancet\s+Psychiatry|"
    r"Social\s+Science\s+(?:&|and)\s+Medicine|"
    r"Int(ernational)?\s+J(ournal)?\s+(?:of\s+)?Epidemiol|"
    r"Computing\s+Surveys|"
    r"Visualization\s+and\s+Computer\s+Graphics|"
    r"Software\s+Engineering\s+and\s+Methodology|"
    r"Interactive\s+Intelligent\s+Systems|"
    r"Conference\s+on\s+Human\s+Factors\s+in\s+Computing|"
    r"International\s+Conference\s+on\s+Software\s+Engineering|"
    r"Journal\s+of\s+Machine\s+Learning\s+Research|"
    r"Neural\s+Information\s+Processing\s+Systems|"
    r"ASME|JACS|Angewandte|Chemical Reviews|Chem Soc Rev|"
    r"PRL|PRX|Reviews of Modern Physics|"
    r"Cambridge\s+University|Oxford\s+University|MIT\s+Press|"
    r"Science\s+Advances|Nature\s+Communications|American\s+Sociological\s+Review|\bASR\b|American\s+Journal\s+of\s+Sociology|\bAJS\b|Quarterly\s+Journal\s+of\s+Economics|\bQJE\b|American\s+Economic\s+Review|\bAER\b|Annual\s+Review\s+of\s+Sociology|Royal\s+Society\s+Open\s+Science|"
    r"Royal\s+Society|"
    r"J(ournal)?\.?\s+Am(erican)?\.?\s+Chem(ical)?\.?\s+Soc(iety)?|"
    r"Angew(andte)?\.?\s+Chem(ie)?|"
    r"Chem(ical)?\.?\s+Soc(iety)?\.?\s+Rev(iews)?|"
    r"Chem(ical)?\.?\s+Rev(iews)?|"
    r"Nature\s+Chemistry|"
    r"Phys(ical)?\.?\s+Rev(iew)?\.?\s+Lett(ers)?|"
    r"Phys(ical)?\.?\s+Rev(iew)?\.?\s+X|"
    r"Rev(iews)?\.?\s+Mod(ern)?\.?\s+Phys(ics)?|\bRMP\b|"
    r"J(ournal)?\.?\s+Mech(anical)?\.?\s+Des(ign)?|"
    r"Composites\s+Part\s+B|Composites\s+Part\s+A|"
    r"Yale\s+L(aw)?\.?\s*J(ournal)?|\bYLJ\b|"
    r"Harvard\s+L(aw)?\.?\s*Rev(iew)?|\bHLR\b|"
    r"Stanford\s+L(aw)?\.?\s*Rev(iew)?|\bSLR\b|"
    r"American\s+Historical\s+Review|\bAHR\b|"
    r"\bPMLA\b|Publications\s+of\s+the\s+Modern\s+Language\s+Association|"
    r"J(ournal)?\.?\s+(?:of\s+)?Aesthetics\s+(?:&|and)\s+Art\s+Criticism|\bJAAC\b|"
    r"\bMind\b\s*\(philosophy\)|"
    r"Cambridge\s+L(aw)?\.?\s*J(ournal)?|\bCLJ\b|"
    r"Critical\s+Inquiry|"
    r"American\s+Political\s+Science\s+Review|\bAPSR\b|"
    r"University\s+of\s+Chicago\s+Press|"
    r"Revista\s+Brasileira\s+de\s+Educação|\bRBE\b|"
    r"Revista\s+Brasileira\s+de\s+Estudos\s+Pedagógicos|\bRBEP\b|"
    r"Revista\s+Brasileira\s+de\s+Ciências\s+Sociais|\bRBCS\b|"
    r"Psicologia\s*:?\s*Reflexão\s+e\s+Crítica|"
    r"Revista\s+de\s+Saúde\s+Pública|\bRSP\b|Rev\.?\s+Saude\s+Pública|"
    r"Ciência\s+(?:&|e)\s+Saúde\s+Coletiva|\bCSC\b|"
    r"Educação\s+em\s+Revista|"
    r"Cadernos\s+CEDES|"
    r"Dados\s*[—-]?\s*Revista\s+de\s+Ciências\s+Sociais|"
    r"Lua\s+Nova|"
    r"Estudos\s+de\s+Psicologia\s*\(?Natal\)?|"
    r"Psicologia\s*(?:&|e)\s*Sociedade|"
    r"Journal\s+of\s+the\s+Brazilian\s+Computer\s+Society|\bJBCS\b|"
    r"SBC\s+Reviews\s+on\s+Computer\s+Science|\bROCS\b|"
    r"Revista\s+Direito\s+GV|"
    r"Manuscrito\s*[—-]?\s*Revista\s+Internacional\s+de\s+Filosofia|"
    r"Trans\s*[/]?\s*Form\s*[/]?\s*Ação|"
    r"Química\s+Nova|Quim\.?\s+Nova|"
    r"Brazilian\s+Journal\s+of\s+Physics|\bBJP\b|"
    r"Journal\s+of\s+the\s+Brazilian\s+Society\s+of\s+Mechanical\s+Sciences|\bJBSMSE\b|"
    # Rodada H — venues Q1 em gerontologia / saúde digital (extensão empírica)
    r"\bScientific\s+Reports\b|"
    r"\bThe\s+Gerontologist\b|\bGerontologist\b|"
    r"Innovation\s+in\s+Aging|"
    r"Frontiers\s+in\s+Education|Frontiers\s+in\s+Psychology|Frontiers\s+in\s+Public\s+Health|"
    r"\bJMIR\s+Aging\b|\bJMIR\s+Mental\s+Health\b|\bJMIR\s+Serious\s+Games\b|\bJMIR\b|"
    r"Educational\s+Gerontology|"
    r"International\s+Journal\s+of\s+Older\s+People\s+Nursing|"
    r"\bDigital\s+Health\b",
    re.IGNORECASE,
)


def assess_t3_corpus_depth(
    *, content: dict, extraction_path: Path, area: str = ""
) -> TemperatureCriterion:
    """T3: Profundidade do corpus + venues elite + saturação."""
    components = []
    score_total = 0.0
    max_total = 0.0

    extr_rows = load_csv(extraction_path)
    n_inc = len(extr_rows)

    # Subitem 3.1 — % de venues elite (peso 0.40)
    elite_count = 0
    for r in extr_rows:
        venue = (r.get("venue", "") or "") + " " + (r.get("citation", "") or "")
        if ELITE_VENUES_PATTERN.search(venue):
            elite_count += 1
    pct_elite = (elite_count / n_inc * 100) if n_inc else 0
    if pct_elite >= 50:
        s = 0.40
    elif pct_elite >= 30:
        s = 0.30
    elif pct_elite >= 15:
        s = 0.20
    elif pct_elite >= 5:
        s = 0.10
    else:
        s = 0.0
    score_total += s
    max_total += 0.40
    components.append({
        "name": "% venues elite na bibliografia",
        "score": s,
        "max": 0.40,
        "detail": f"{elite_count}/{n_inc} ({pct_elite:.0f}%)",
    })

    # Subitem 3.2 — Saturação por RQ (peso 0.30)
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
            s = 0.30
        else:
            ratio = (len(rq_coverage) - len(unsatured)) / len(rq_coverage)
            s = 0.30 * ratio
    else:
        s = 0.0
    score_total += s
    max_total += 0.30
    components.append({
        "name": "Saturação por RQ (≥3 estudos cada)",
        "score": s,
        "max": 0.30,
        "detail": (f"{len(rq_coverage)} RQs detectadas no corpus"
                   if rq_coverage else "sem rastreamento de RQs em extraction.csv"),
    })

    # Subitem 3.3 — Diversidade temporal e geográfica (peso 0.30)
    years = []
    countries = set()
    for r in extr_rows:
        try:
            years.append(int(str(r.get("year", "")).strip()))
        except ValueError:
            continue
        c = (r.get("country", "") or r.get("country_authors", "") or "").strip().lower()
        if c:
            countries.add(c)
    span = max(years) - min(years) if years else 0
    n_countries = len(countries)
    div_score = 0.0
    if span >= 5:
        div_score += 0.15
    elif span >= 3:
        div_score += 0.075
    if n_countries >= 5:
        div_score += 0.15
    elif n_countries >= 3:
        div_score += 0.075
    s = div_score
    score_total += s
    max_total += 0.30
    components.append({
        "name": "Diversidade temporal + geográfica",
        "score": s,
        "max": 0.30,
        "detail": f"span {span} anos, {n_countries} países",
    })

    return TemperatureCriterion(
        code="T3",
        name="Profundidade do corpus + venues elite",
        score_0_1=score_total / max_total if max_total > 0 else 0.0,
        weight=0.30,
        components=components,
    )


# ── T4 — Análise semântica (Claude Chat) ───────────────────────────────────


def assess_t4_semantic(content: dict) -> TemperatureCriterion | None:
    """T4: Análise semântica pelo Claude Chat.

    Retorna None se C7 não disponível (modo standalone).
    """
    review = content.get("qualitative_review", None)
    if not review:
        return None

    components = []
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
        components.append({
            "name": label,
            "score": sub_score / 10,
            "max": 1.0,
            "detail": sub.get("rationale", "")[:200],
        })

    avg = sum(sub_scores) / len(sub_scores) if sub_scores else 0
    return TemperatureCriterion(
        code="T4",
        name="Análise semântica (Claude Chat)",
        score_0_1=avg / 10.0,
        weight=0.20,
        components=components,
    )


# ── Orquestração ───────────────────────────────────────────────────────────


def compute_temperature(
    *,
    package_dir: Path,
    content: dict,
    extraction_path: Path,
    plagiarism_summary: dict | None = None,
    area: str = "",
) -> TemperatureReport:
    """Calcula a temperatura 0-1 baseada nos 4 critérios.

    Sem C7 disponível: T1=37,5%, T2=25%, T3=37,5%
    Com C7 disponível: T1=30%, T2=20%, T3=30%, T4=20%
    """
    t1 = assess_t1_reporting_guideline(package_dir=package_dir, content=content)
    t2 = assess_t2_quantitative_compliance(
        content=content, plagiarism_summary=plagiarism_summary
    )
    t3 = assess_t3_corpus_depth(
        content=content, extraction_path=extraction_path, area=area
    )
    t4 = assess_t4_semantic(content)

    if t4:
        # Pesos com C7 ativo
        t1.weight = 0.30
        t2.weight = 0.20
        t3.weight = 0.30
        t4.weight = 0.20
        criteria = [t1, t2, t3, t4]
        c7_available = True
        weights = {"T1": 0.30, "T2": 0.20, "T3": 0.30, "T4": 0.20}
    else:
        # Pesos sem C7 (T4 redistribuído proporcionalmente)
        t1.weight = 0.375
        t2.weight = 0.25
        t3.weight = 0.375
        criteria = [t1, t2, t3]
        c7_available = False
        weights = {"T1": 0.375, "T2": 0.25, "T3": 0.375, "T4": 0.0}

    final_temp = sum(c.score_0_1 * c.weight for c in criteria)

    return TemperatureReport(
        criteria=criteria,
        final_temperature=final_temp,
        c7_available=c7_available,
        weights_used=weights,
    )


def render_temperature_summary(report: TemperatureReport) -> dict:
    """Resumo serializável da temperatura para o JSON."""
    return {
        "value": round(report.final_temperature, 3),
        "scale": "0.0 to 1.0",
        "c7_available": report.c7_available,
        "weights_used": report.weights_used,
        "tooltip_explanation": (
            "Temperatura baseada em 4 critérios mensuráveis das grandes editoras "
            "(Elsevier, Nature Springer, Wiley, IEEE, ACM, Lancet, BMJ, etc.): "
            "T1 reporting guideline (PRISMA), T2 limites quantitativos (plágio, "
            "extensão), T3 profundidade do corpus + venues elite, T4 análise "
            "semântica (quando disponível). Mapeamento para Qualis/Quartil será "
            "calibrado empiricamente em Sprint Badge ao final da v2.0.0."
        ),
        "criteria": [
            {
                "code": c.code,
                "name": c.name,
                "score_0_1": round(c.score_0_1, 3),
                "weight": c.weight,
                "components": c.components,
            }
            for c in report.criteria
        ],
    }
