"""
ignorantia.assessor.venues — Calcula status colorido por venue.

Para cada venue do catálogo (`references/venues-catalog.json`), verifica
critérios programaticamente verificáveis e atribui status:

  🟢 Pronto      — todos critérios atendidos
  🟡 Próximo     — 1-2 critérios faltando, ajustes leves
  🟠 Distante    — 3+ critérios faltando, revisão substancial
  🔴 Inadequado  — escopo/área não combina ou critério eliminatório falha

Critérios verificados:
  S1 — Escopo cobre o tema (keywords)
  S2 — Tipo de trabalho aceito (SLR sim/não)
  S3 — Reporting guideline correto
  S4 — Política de IA atendida
  S5 — Bibliografia atende mínimo de venues elite
  S6 — Idioma compatível (pt-BR vs EN)
  S7 — Comprimento/abstract compatível
  S8 — Corpus mínimo da área

Em fase ghostwriter (0.x.y), TODOS os venues ficam 🔴 com aviso.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .helpers import file_text, load_json, load_csv, strip_html, word_count, detect_lang_is_ptbr


@dataclass
class VenueCheck:
    """Resultado de uma verificação contra um venue."""
    venue_id: str
    venue_name: str
    publisher: str
    qualis_equiv: str
    quartil: str
    status: str  # "excellent" | "ready" | "near" | "far" | "inadequate"
    status_icon: str  # 🔵 / 🟢 / 🟡 / 🟠 / 🔴
    failed_checks: list[dict] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    advisory: str = ""
    url_guidelines: str = ""
    excellence_signals: list[str] = field(default_factory=list)  # quais critérios estão acima do mínimo


@dataclass
class VenuesReport:
    """Relatório consolidado da avaliação por venue."""
    checks: list[VenueCheck] = field(default_factory=list)
    phase_blocked: bool = False
    phase_message: str = ""

    @property
    def n_excellent(self) -> int:
        return sum(1 for c in self.checks if c.status == "excellent")

    @property
    def n_ready(self) -> int:
        return sum(1 for c in self.checks if c.status == "ready")

    @property
    def n_near(self) -> int:
        return sum(1 for c in self.checks if c.status == "near")

    @property
    def n_far(self) -> int:
        return sum(1 for c in self.checks if c.status == "far")

    @property
    def n_inadequate(self) -> int:
        return sum(1 for c in self.checks if c.status == "inadequate")


# ── Verificações por venue ──────────────────────────────────────────────


def check_scope(venue: dict, content: dict) -> tuple[bool, str]:
    """S1 — Escopo do venue cobre o tema do trabalho.

    Algoritmo refinado (v2.0.0-alpha14):
    - Word-boundary regex (\\b) para evitar substring spurious (ex: "AI" em "AIDS")
    - Stems detectados (terminam em consoante curta sem espaço): apenas \\b no início,
      permitindo "pedagóg" matchar "pedagógicas", "currícul" matchar "currículos" etc.
    - Peso 2× para keywords compostas (multi-palavra) — mais discriminantes
    - Score ponderado: título peso 3, contexto peso 1
    - Critério: ≥1 composta no título OU ≥2 simples no título OU
                ≥1 simples no título + ≥1 contextual OU score ≥4.0
    """
    keywords = venue.get("topic_keywords", [])
    if not keywords or "all" in keywords:
        return True, "Venue aceita qualquer tema"

    title_text = " ".join([
        content.get("title", "") or "",
        content.get("subtitle", "") or "",
    ]).lower()
    context_text = " ".join([
        strip_html(content.get("abstract_html", "") or ""),
        strip_html(content.get("introduction_html", "") or ""),
    ]).lower()

    def is_stem(kw: str) -> bool:
        """Heurística: keyword é stem (apenas \\b no início) se:
        - tem 4-7 caracteres E
        - não tem espaço/hífen/underscore E
        - termina em consoante (não em vogal típica de palavra completa).
        Exemplos: 'pedagóg', 'currícul', 'didát', 'polít' → stems
                  'educação', 'ensino', 'cognition' → palavras completas
        """
        if " " in kw or "-" in kw or "_" in kw:
            return False
        if not (4 <= len(kw) <= 8):
            return False
        # Termina em consoante? (g, t, l, c, m, n, r, s costumam ser stems em PT)
        last = kw[-1].lower()
        # Vogais típicas em palavras completas: a, e, i, o, u, ã, õ, é, ê, í, ó, ô, ú, á, à, â
        vowels_complete = "aeiouãõéêíóôúáàâ"
        return last not in vowels_complete

    def kw_match(kw: str, text: str) -> bool:
        """Match com word boundary, case-insensitive. Stems usam apenas \\b inicial."""
        escaped = re.escape(kw.lower())
        if is_stem(kw):
            pattern = r"\b" + escaped  # word-start only (matcha pedagóg + icas)
        else:
            pattern = r"\b" + escaped + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    # Score ponderado
    score = 0.0
    title_simple_hits = []
    title_compound_hits = []
    context_hits = []

    for kw in keywords:
        kw_lower = kw.lower()
        is_compound = " " in kw_lower or "-" in kw_lower or "_" in kw_lower
        weight = 2.0 if is_compound else 1.0

        if kw_match(kw, title_text):
            score += 3.0 * weight
            if is_compound:
                title_compound_hits.append(kw)
            else:
                title_simple_hits.append(kw)
        elif kw_match(kw, context_text):
            score += 1.0 * weight
            context_hits.append(kw)

    # Critérios de aceitação (qualquer um basta):
    # (a) ≥1 keyword COMPOSTA no título → tema central específico
    # (b) ≥2 keywords simples no título → tema central múltiplo
    # (c) ≥1 keyword no título + ≥1 keyword adicional em qualquer lugar → confirmação
    # (d) score ponderado ≥4.0 → contexto forte
    if title_compound_hits:
        return True, f"Tema central específico no título ({len(title_compound_hits)} keywords compostas: {', '.join(title_compound_hits[:3])})"
    if len(title_simple_hits) >= 2:
        return True, f"Tema central confirmado ({len(title_simple_hits)} keywords no título: {', '.join(title_simple_hits[:3])})"
    if title_simple_hits and context_hits:
        return True, (f"Tema confirmado (1 keyword no título: {title_simple_hits[0]}, "
                      f"{len(context_hits)} adicional(is) no contexto)")
    if score >= 4.0:
        all_hits = title_simple_hits + context_hits + title_compound_hits
        return True, f"Tema contextualmente alinhado (score {score:.1f}; keywords: {', '.join(all_hits[:5])})"

    return False, (f"Tema não corresponde ao escopo do venue. "
                   f"Score ponderado: {score:.1f} (mínimo: 4.0). "
                   f"Esperadas: {', '.join(keywords[:5])}")


def check_accepts_slr(venue: dict, content: dict) -> tuple[bool, str]:
    """S2 — Venue aceita SLR como tipo de trabalho."""
    accepts = venue.get("accepts_slr", True)
    if accepts:
        return True, "Venue aceita SLR"
    return False, "Venue NÃO publica SLRs (ex: TPAMI prefere papers de pesquisa original)"


def check_reporting_guideline(venue: dict, package_dir: Path, content: dict) -> tuple[bool, str]:
    """S3 — Reporting guideline correto seguido."""
    guideline = venue.get("reporting_guideline", "")
    if guideline == "—" or not guideline:
        return True, "Venue não exige reporting guideline específico"

    # Heurística: se o texto explicita "não-PRISMA" ou "tradicional", aceita sem checar
    if re.search(r"não[-\s]*PRISMA|tradicional|adaptaç", guideline, re.IGNORECASE):
        return True, f"Venue aceita {guideline} (análise tradicional não exige PRISMA)"

    protocol = file_text(package_dir / "protocol.md")
    readme = file_text(package_dir / "README.md")
    text_blob = (protocol + " " + readme).lower()

    if "PRISMA" in guideline.upper():
        if "prisma" in text_blob:
            return True, "PRISMA mencionado no protocolo"
        return False, f"Venue exige {guideline} mas PRISMA não aparece no protocol.md"
    if "Kitchenham" in guideline:
        if "kitchenham" in text_blob:
            return True, "Kitchenham mencionado no protocolo"
        return False, f"Venue exige {guideline} mas Kitchenham não aparece no protocol.md"
    if "Bluebook" in guideline:
        if "bluebook" in text_blob:
            return True, "Bluebook mencionado"
        return False, f"Venue exige {guideline} mas Bluebook não aparece"
    return True, f"Reporting guideline ({guideline}) genérico — verificar manualmente"


def check_ai_policy(venue: dict, content: dict) -> tuple[bool, str]:
    """S4 — Política de IA atendida."""
    ai = content.get("ai_declaration") or {}
    required = ["tool", "stages", "authors_responsible"]
    missing = [f for f in required if not ai.get(f)]
    if missing:
        return False, f"Declaração de IA incompleta: {', '.join(missing)}"
    # Política específica do venue (heurística)
    policy = venue.get("ai_policy", "")
    if "ICMJE" in policy or "art. 9" in policy:
        # Verifica que IA não está como autora
        authors = content.get("authors", [])
        if isinstance(authors, str):
            authors = [authors]
        ai_as_author = any(
            re.search(r"^(claude|gpt|chatgpt|gemini|llama|copilot|bard)",
                      str(a).strip(), re.IGNORECASE)
            for a in authors
        )
        if ai_as_author:
            return False, "IA listada como autora — viola ICMJE/CNPq"
    return True, f"Política IA atendida ({policy})"


def check_elite_refs(venue: dict, extr_path: Path) -> tuple[bool, str]:
    """S5 — % de venues elite na bibliografia atende mínimo do venue."""
    min_pct = venue.get("min_pct_elite_refs")
    if min_pct is None:
        return True, "Venue não exige mínimo específico de venues elite"

    extr = load_csv(extr_path)
    if not extr:
        return False, "Sem dados de extração para verificar bibliografia"

    elite_pattern = re.compile(
        r"IEEE\s+Trans|ACM\s+Trans|TVCG|TPAMI|TSE|CSUR|TOCHI|TOSEM|TIIS|TIST|TODS|TOG|TOPLAS|TOIS|"
        r"\bNature\b|\bScience\b|PNAS|Cell|Lancet|NEJM|JAMA|BMJ|"
        r"NeurIPS|ICML|ICLR|CHI|SIGGRAPH|ICSE|FSE|UIST|JMLR|"
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
        r"Science\s+Advances|"
        r"Nature\s+Communications|"
        r"American\s+Sociological\s+Review|\bASR\b|"
        r"American\s+Journal\s+of\s+Sociology|\bAJS\b|"
        r"Quarterly\s+Journal\s+of\s+Economics|\bQJE\b|"
        r"American\s+Economic\s+Review|\bAER\b|"
        r"Annual\s+Review\s+of\s+Sociology|"
        r"Royal\s+Society\s+Open\s+Science|"
        r"Royal\s+Society|"
        r"\bJACS\b|J(ournal)?\.?\s+Am(erican)?\.?\s+Chem(ical)?\.?\s+Soc(iety)?|"
        r"Angew(andte)?\.?\s+Chem(ie)?|"
        r"Chem(ical)?\.?\s+Soc(iety)?\.?\s+Rev(iews)?|"
        r"Chem(ical)?\.?\s+Rev(iews)?|"
        r"Nature\s+Chemistry|"
        r"Phys(ical)?\.?\s+Rev(iew)?\.?\s+Lett(ers)?|\bPRL\b|"
        r"Phys(ical)?\.?\s+Rev(iew)?\.?\s+X|\bPRX\b|"
        r"Rev(iews)?\.?\s+Mod(ern)?\.?\s+Phys(ics)?|\bRMP\b|"
        r"\bASME\b|J(ournal)?\.?\s+Mech(anical)?\.?\s+Des(ign)?|"
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
    elite_count = sum(
        1 for r in extr
        if elite_pattern.search((r.get("venue", "") or "") + " " + (r.get("citation", "") or ""))
    )
    pct = (elite_count / len(extr) * 100) if extr else 0

    if pct >= min_pct:
        return True, f"Bibliografia tem {pct:.0f}% venues elite (mínimo: {min_pct}%)"
    return False, (f"Bibliografia tem apenas {pct:.0f}% venues elite "
                   f"(mínimo do venue: {min_pct}%)")


def check_language(venue: dict, content: dict) -> tuple[bool, str]:
    """S6 — Idioma compatível."""
    venue_lang = venue.get("lang", "en")
    content_lang = (content.get("lang", "pt-BR") or "pt-BR").lower()

    if venue_lang == "en" and content_lang.startswith("pt"):
        return False, "Venue aceita apenas EN; manuscrito está em pt-BR"
    if venue_lang == "pt" and not content_lang.startswith("pt"):
        return False, "Venue aceita apenas pt-BR; manuscrito está em EN"
    return True, f"Idioma compatível ({venue_lang})"


def check_length_abstract(venue: dict, content: dict) -> tuple[bool, str]:
    """S7 — Comprimento e formato do abstract compatíveis."""
    issues = []

    # Abstract
    abstract = strip_html(content.get("abstract_html", "") or "")
    n_abs = len(abstract.split())
    abs_format = venue.get("abstract_format", "")
    # Detecta limite de palavras no formato
    abs_match = re.search(r"(\d{2,3})", abs_format)
    if abs_match:
        max_abs = int(abs_match.group(1))
        if n_abs > max_abs * 1.1:
            issues.append(f"abstract {n_abs}w excede limite ~{max_abs}w")
    if "structured" in abs_format.lower():
        elements = sum(
            1 for p in [r"contexto|background|objetivo|aim|objective",
                        r"método|method", r"resultados?|results",
                        r"conclus[aã]o|conclusion"]
            if re.search(p, abstract, re.IGNORECASE)
        )
        if elements < 3:
            issues.append(f"abstract estruturado exige 4 elementos (tem {elements})")

    # Total
    max_words = venue.get("max_words")
    if max_words:
        total = sum(
            word_count(content.get(k, "") or "")
            for k in ["abstract_html", "introduction_html", "background_html",
                      "methodology_html", "synthesis_html", "discussion_html",
                      "threats_html", "conclusion_html"]
        )
        if total > max_words * 1.1:
            issues.append(f"manuscrito {total}w excede limite {max_words}w")

    if issues:
        return False, "; ".join(issues)
    return True, "Comprimento e formato compatíveis"


def check_corpus_size(venue: dict, extr_path: Path) -> tuple[bool, str]:
    """S8 — Corpus mínimo do venue."""
    min_size = venue.get("min_corpus_size")
    if min_size is None:
        return True, "Venue não exige mínimo de corpus"

    extr = load_csv(extr_path)
    n = len(extr)
    if n >= min_size:
        return True, f"Corpus {n} estudos (mínimo: {min_size})"
    return False, f"Corpus {n} estudos é insuficiente (mínimo: {min_size})"


# ── Verificação de excelência (🔵 Excelente — Rodada E2a) ──────────────


def check_excellence_dimensions(
    venue: dict,
    *,
    content: dict,
    extraction_path: Path,
) -> tuple[int, list[str]]:
    """Conta quantas das 5 dimensões estão ACIMA do mínimo do venue.

    Dimensões (cada uma vale 1 ponto):
      D1 — Corpus ≥ 1.5× o mínimo do venue
      D2 — % venues elite ≥ 1.5× o mínimo do venue
      D3 — Saturação ≥ 5 estudos por RQ (não só 3)
      D4 — Cobertura temporal ≥ 8 anos (não só 5)
      D5 — Diversidade geográfica ≥ 7 países (não só 5)

    Retorna (n_dimensions_above_minimum, list_of_signals).

    Para nível 🔵, requer ≥ 3 de 5 dimensões acima do mínimo.
    """
    extr = load_csv(extraction_path)
    n_studies = len(extr)
    signals = []

    # D1 — Corpus acima do mínimo
    min_corpus = venue.get("min_corpus_size")
    if min_corpus and n_studies >= min_corpus * 1.5:
        signals.append(f"D1: corpus {n_studies} ≥ 1.5× mínimo ({min_corpus})")

    # D2 — % elite refs acima do mínimo
    min_pct_elite = venue.get("min_pct_elite_refs")
    if min_pct_elite and extr:
        elite_pattern = re.compile(
            r"IEEE\s+Trans|ACM\s+Trans|TVCG|TPAMI|TSE|CSUR|TOCHI|TOSEM|TIIS|TIST|TODS|TOG|TOPLAS|TOIS|"
            r"\bNature\b|\bScience\b|PNAS|Cell|Lancet|NEJM|JAMA|BMJ|"
            r"NeurIPS|ICML|ICLR|CHI|SIGGRAPH|ICSE|FSE|UIST|JMLR|"
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
            r"Science\s+Advances|"
            r"Nature\s+Communications|"
            r"American\s+Sociological\s+Review|\bASR\b|"
            r"American\s+Journal\s+of\s+Sociology|\bAJS\b|"
            r"Quarterly\s+Journal\s+of\s+Economics|\bQJE\b|"
            r"American\s+Economic\s+Review|\bAER\b|"
            r"Annual\s+Review\s+of\s+Sociology|"
            r"Royal\s+Society\s+Open\s+Science|"
            r"Royal\s+Society|"
            r"\bJACS\b|J(ournal)?\.?\s+Am(erican)?\.?\s+Chem(ical)?\.?\s+Soc(iety)?|"
            r"Angew(andte)?\.?\s+Chem(ie)?|"
            r"Chem(ical)?\.?\s+Soc(iety)?\.?\s+Rev(iews)?|"
            r"Chem(ical)?\.?\s+Rev(iews)?|"
            r"Nature\s+Chemistry|"
            r"Phys(ical)?\.?\s+Rev(iew)?\.?\s+Lett(ers)?|\bPRL\b|"
            r"Phys(ical)?\.?\s+Rev(iew)?\.?\s+X|\bPRX\b|"
            r"Rev(iews)?\.?\s+Mod(ern)?\.?\s+Phys(ics)?|\bRMP\b|"
            r"\bASME\b|J(ournal)?\.?\s+Mech(anical)?\.?\s+Des(ign)?|"
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
        elite_count = sum(
            1 for r in extr
            if elite_pattern.search((r.get("venue", "") or "") + " " + (r.get("citation", "") or ""))
        )
        pct = (elite_count / len(extr) * 100) if extr else 0
        if pct >= min_pct_elite * 1.5:
            signals.append(f"D2: {pct:.0f}% venues elite ≥ 1.5× mínimo ({min_pct_elite}%)")

    # D3 — Saturação ≥ 5 estudos por RQ
    rq_coverage: dict[str, int] = {}
    for r in extr:
        for rq in re.split(r"[,;]\s*", r.get("rq_addressed", "") or ""):
            rq = rq.strip()
            if rq:
                rq_coverage[rq] = rq_coverage.get(rq, 0) + 1
    if rq_coverage and all(c >= 5 for c in rq_coverage.values()):
        signals.append(f"D3: ≥5 estudos por RQ em todas {len(rq_coverage)} RQs")

    # D4 — Cobertura temporal ≥ 8 anos
    years = []
    for r in extr:
        try:
            years.append(int(str(r.get("year", "")).strip()))
        except ValueError:
            continue
    if years and (max(years) - min(years)) >= 8:
        signals.append(f"D4: cobertura temporal {max(years)-min(years)} anos ≥ 8")

    # D5 — Diversidade geográfica ≥ 7 países
    countries = set()
    for r in extr:
        c = (r.get("country", "") or r.get("country_authors", "") or "").strip().lower()
        if c:
            countries.add(c)
    if len(countries) >= 7:
        signals.append(f"D5: diversidade geográfica {len(countries)} países ≥ 7")

    return len(signals), signals


# ── Orquestração ───────────────────────────────────────────────────────


def evaluate_venue(
    venue: dict,
    *,
    package_dir: Path,
    content: dict,
    extraction_path: Path,
) -> VenueCheck:
    """Avalia o pacote contra um venue específico, retornando VenueCheck."""
    # Tratar venues bloqueados (Annual Reviews INVITED ONLY, TiCS proposal-first)
    if venue.get("submission_blocked"):
        return VenueCheck(
            venue_id=venue["id"],
            venue_name=venue["name"],
            publisher=venue.get("publisher", ""),
            qualis_equiv=venue.get("qualis_equiv", ""),
            quartil=venue.get("quartil", ""),
            status="inadequate",
            status_icon="🔴",
            failed_checks=[{
                "name": "Submission policy",
                "detail": venue.get("submission_blocked_reason", "Venue não aceita submissões espontâneas."),
            }],
            advisory=venue.get("submission_blocked_reason", "Venue não aceita submissões espontâneas."),
            url_guidelines=venue.get("url_guidelines", ""),
        )

    # Executa as 8 verificações
    checks = [
        ("S1 — Escopo", check_scope(venue, content)),
        ("S2 — Aceita SLR", check_accepts_slr(venue, content)),
        ("S3 — Reporting guideline", check_reporting_guideline(venue, package_dir, content)),
        ("S4 — Política IA", check_ai_policy(venue, content)),
        ("S5 — Venues elite na bib", check_elite_refs(venue, extraction_path)),
        ("S6 — Idioma", check_language(venue, content)),
        ("S7 — Comprimento/abstract", check_length_abstract(venue, content)),
        ("S8 — Corpus mínimo", check_corpus_size(venue, extraction_path)),
    ]

    failed_checks = []
    passed_checks = []
    eliminator_failed = False

    for name, (passed, detail) in checks:
        if passed:
            passed_checks.append(name)
        else:
            failed_checks.append({"name": name, "detail": detail})
            # S1, S2, S6 são eliminatórios → 🔴
            if name.startswith(("S1", "S2", "S6")):
                eliminator_failed = True

    # Determinar status
    n_failed = len(failed_checks)
    excellence_signals = []

    if eliminator_failed:
        status = "inadequate"
        icon = "🔴"
        advisory = "Venue inadequado para este trabalho. Eliminatório (escopo/SLR/idioma) falhou."
    elif n_failed == 0:
        # Tudo passou — verificar se é 🔵 Excelente ou 🟢 Pronto
        n_above, signals = check_excellence_dimensions(
            venue, content=content, extraction_path=extraction_path
        )
        excellence_signals = signals
        if n_above >= 3:
            status = "excellent"
            icon = "🔵"
            advisory = (
                f"Excelente. Trabalho está confortavelmente acima dos mínimos do venue "
                f"em {n_above} de 5 dimensões. Submissão tem boa margem de segurança."
            )
        else:
            status = "ready"
            icon = "🟢"
            advisory = (
                "Pronto para submissão (no limite dos mínimos). Verificar manualmente "
                "significância e originalidade."
            )
    elif n_failed <= 2:
        status = "near"
        icon = "🟡"
        advisory = f"Próximo. {n_failed} ajuste(s) recomendado(s) antes de submeter."
    else:
        status = "far"
        icon = "🟠"
        advisory = f"Distante. {n_failed} critérios precisam de revisão substancial."

    return VenueCheck(
        venue_id=venue["id"],
        venue_name=venue["name"],
        publisher=venue.get("publisher", ""),
        qualis_equiv=venue.get("qualis_equiv", ""),
        quartil=venue.get("quartil", ""),
        status=status,
        status_icon=icon,
        failed_checks=failed_checks,
        passed_checks=passed_checks,
        advisory=advisory,
        url_guidelines=venue.get("url_guidelines", ""),
        excellence_signals=excellence_signals,
    )


def evaluate_all_venues(
    *,
    package_dir: Path,
    content: dict,
    extraction_path: Path,
    catalog_path: Path,
    phase: str = "honored",
    area: str = "",
) -> VenuesReport:
    """Avalia o pacote contra todos os venues do catálogo."""
    catalog = load_json(catalog_path) or {}
    is_ptbr = detect_lang_is_ptbr(content)

    # Selecionar venues relevantes pela área e idioma
    all_venues = []
    if is_ptbr:
        all_venues.extend(catalog.get("venues_qualis_a1_ptbr", []))
        # Adiciona alguns elite EN também (autor pode internacionalizar)
        all_venues.extend([v for v in catalog.get("venues_elite", [])
                            if "all" in v.get("topic_keywords", []) or v.get("accepts_slr")])
    else:
        all_venues.extend(catalog.get("venues_elite", []))

    # Em fase ghostwriter, todos venues ficam 🔴
    if phase == "ghostwriter":
        checks = []
        for venue in all_venues:
            checks.append(VenueCheck(
                venue_id=venue["id"],
                venue_name=venue["name"],
                publisher=venue.get("publisher", ""),
                qualis_equiv=venue.get("qualis_equiv", ""),
                quartil=venue.get("quartil", ""),
                status="inadequate",
                status_icon="🔴",
                advisory="Fase ghostwriter (0.x.y) — não submetível em qualquer venue.",
                url_guidelines=venue.get("url_guidelines", ""),
            ))
        return VenuesReport(
            checks=checks,
            phase_blocked=True,
            phase_message="Todos venues bloqueados — fase ghostwriter (0.x.y).",
        )

    # Caso normal: avaliar cada venue
    checks = [
        evaluate_venue(venue, package_dir=package_dir,
                       content=content, extraction_path=extraction_path)
        for venue in all_venues
    ]

    # Ordenar: excellent primeiro, depois ready, near, far, inadequate
    status_order = {"excellent": 0, "ready": 1, "near": 2, "far": 3, "inadequate": 4}
    checks.sort(key=lambda c: (status_order[c.status], c.venue_name))

    return VenuesReport(checks=checks)


def render_venues_summary(report: VenuesReport) -> dict:
    """Resumo serializável para o JSON."""
    return {
        "n_excellent": report.n_excellent,
        "n_ready": report.n_ready,
        "n_near": report.n_near,
        "n_far": report.n_far,
        "n_inadequate": report.n_inadequate,
        "phase_blocked": report.phase_blocked,
        "phase_message": report.phase_message,
        "checks": [
            {
                "venue_id": c.venue_id,
                "venue_name": c.venue_name,
                "publisher": c.publisher,
                "qualis_equiv": c.qualis_equiv,
                "quartil": c.quartil,
                "status": c.status,
                "status_icon": c.status_icon,
                "failed_checks": c.failed_checks,
                "passed_checks": c.passed_checks,
                "advisory": c.advisory,
                "url_guidelines": c.url_guidelines,
                "excellence_signals": c.excellence_signals,
            }
            for c in report.checks
        ],
    }
