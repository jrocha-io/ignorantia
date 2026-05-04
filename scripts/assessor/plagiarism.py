"""
ignorantia.assessor.plagiarism — Camada 1 de detecção de plágio.

Camada 1 (interna ao corpus): compara strings de N+ palavras consecutivas
do manuscrito contra os abstracts e excerpts dos estudos incluídos.

Pega o caso mais comum: autor copia trecho de paper que está lendo,
sem aspas/atribuição.

Camadas 2 (web_search) e 3 (Copyleaks) ficam para o Sprint 2.

Tipos de match:
  🔴 Match alto (>15 palavras consecutivas, sem aspas)  → eliminatório E9
  🟡 Match médio (12-15 palavras, sem aspas)            → aviso
  🟢 Match com aspas e atribuição                       → citação legítima

Limites baseados em:
  - University of Virginia Honor Committee: ≥3 palavras consecutivas exigem aspas
  - 12 palavras é threshold conservador (acima de "termo técnico padrão")
  - 15 palavras: alta confiança de cópia (não pode ser coincidência)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .helpers import strip_html, consecutive_words


@dataclass
class PlagiarismMatch:
    """Um match detectado entre o manuscrito e uma fonte."""
    n_words: int
    matched_phrase: str
    source_id: str  # ID do estudo no corpus
    source_field: str  # 'abstract' | 'excerpt' | 'finding'
    has_quotes: bool  # texto está entre aspas?
    has_attribution: bool  # citação [n] próxima?
    severity: str  # 'critical' | 'warning' | 'legitimate'


@dataclass
class PlagiarismReport:
    """Relatório consolidado da camada 1."""
    matches: list[PlagiarismMatch] = field(default_factory=list)
    layer: str = "1 (corpus interno)"
    n_phrases_checked: int = 0
    n_sources_compared: int = 0

    @property
    def critical_matches(self) -> int:
        return sum(1 for m in self.matches if m.severity == "critical")

    @property
    def warning_matches(self) -> int:
        return sum(1 for m in self.matches if m.severity == "warning")

    @property
    def legitimate_matches(self) -> int:
        return sum(1 for m in self.matches if m.severity == "legitimate")


def normalize_text(text: str) -> str:
    """Lowercase + remove pontuação não-essencial + colapsa whitespace."""
    if not text:
        return ""
    text = strip_html(text).lower()
    # Remove pontuação que pode variar
    text = re.sub(r"[.,;:!?\(\)\[\]\"'`]", " ", text)
    # Colapsa whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_corpus_phrases(
    extraction_rows: list[dict],
    min_words: int = 12,
) -> dict[str, list[tuple[str, str]]]:
    """Extrai frases (≥min_words) de cada estudo do corpus.

    Returns: {study_id: [(field_name, phrase), ...]}
    """
    corpus = {}
    for row in extraction_rows:
        sid = row.get("id") or row.get("study_id") or row.get("ID") or ""
        if not sid:
            continue
        phrases_per_field = []
        for field_name in ["abstract", "excerpt", "main_findings",
                            "conclusion", "summary"]:
            text = row.get(field_name, "") or ""
            text = normalize_text(text)
            for phrase in consecutive_words(text, min_words):
                phrases_per_field.append((field_name, phrase))
        corpus[sid] = phrases_per_field
    return corpus


def check_for_quotes_attribution(
    manuscript_text: str, phrase_position: int, phrase_length: int,
) -> tuple[bool, bool]:
    """Verifica se uma frase está entre aspas e tem atribuição próxima.

    Returns: (has_quotes, has_attribution)
    """
    # Janela ao redor da frase para contexto
    start = max(0, phrase_position - 100)
    end = min(len(manuscript_text), phrase_position + phrase_length + 100)
    context = manuscript_text[start:end]

    # Aspas em volta da frase
    has_quotes = bool(re.search(r'["\u201c\u201d].{1,400}["\u201c\u201d]', context, re.DOTALL))

    # Atribuição: [n] ou (Autor, ano) ou Autor (ano) próximo
    has_attribution = bool(re.search(
        r"\[\d+\]|\([A-Z][a-zA-Zàâãéèêíîóôõúûç]+(?:\s+et\s+al\.?)?,?\s*\d{4}|"
        r"[A-Z][a-zA-Zàâãéèêíîóôõúûç]+(?:\s+et\s+al\.?)?\s*\(\d{4}\)",
        context
    ))
    return has_quotes, has_attribution


def detect_plagiarism_layer1(
    manuscript_html: str,
    extraction_rows: list[dict],
    *,
    min_words_warning: int = 12,
    min_words_critical: int = 15,
) -> PlagiarismReport:
    """
    Camada 1: detecção interna ao corpus.

    Para cada frase de N+ palavras consecutivas no manuscrito, compara
    contra todas as frases extraídas dos estudos do corpus.

    Retorna **um match por região contígua** (não múltiplos sobrepostos).
    A região é estendida para encontrar o trecho contíguo mais longo
    que aparece tanto no manuscrito quanto no corpus.
    """
    report = PlagiarismReport()
    if not manuscript_html or not extraction_rows:
        return report

    manuscript_normalized = normalize_text(manuscript_html)

    # Extrai frases do corpus
    corpus_phrases = extract_corpus_phrases(extraction_rows, min_words=min_words_warning)
    report.n_sources_compared = len(corpus_phrases)

    # Set de todas as frases do corpus para lookup rápido
    corpus_index: dict[str, tuple[str, str]] = {}
    corpus_full_texts: dict[str, dict[str, str]] = {}  # sid → {field → full normalized text}
    for sid, items in corpus_phrases.items():
        for field_name, phrase in items:
            corpus_index[phrase] = (sid, field_name)

    # Reconstruir corpus_full_texts a partir dos rows
    for row in extraction_rows:
        sid = row.get("id") or row.get("study_id") or row.get("ID") or ""
        if not sid:
            continue
        corpus_full_texts[sid] = {}
        for field_name in ["abstract", "excerpt", "main_findings",
                            "conclusion", "summary"]:
            text = row.get(field_name, "") or ""
            corpus_full_texts[sid][field_name] = normalize_text(text)

    # Para cada frase mínima do manuscrito, ver se há match
    manuscript_phrases = consecutive_words(manuscript_normalized, min_words_warning)
    report.n_phrases_checked = len(manuscript_phrases)

    # Strategy: detectar regiões contíguas de match e reportar só a maior
    # de cada região
    matched_regions = []  # list of (sid, field, words_matched_phrase)

    i = 0
    seen_starts: set[str] = set()
    while i < len(manuscript_phrases):
        phrase = manuscript_phrases[i]
        # Skip se já reportamos uma região que começa exatamente aqui
        if phrase in seen_starts:
            i += 1
            continue

        if phrase in corpus_index:
            sid, field_name = corpus_index[phrase]
            full_corpus_text = corpus_full_texts[sid][field_name]

            # Tentar estender a região contígua
            words_in_phrase = phrase.split()
            initial_word_idx = manuscript_normalized.find(phrase)
            if initial_word_idx == -1:
                i += 1
                continue

            # Extrair toda a sequência contígua começando aqui
            remaining = manuscript_normalized[initial_word_idx:]
            remaining_words = remaining.split()

            # Encontra o maior prefixo de remaining_words que está em full_corpus_text
            best_match_words = words_in_phrase[:]
            for n_extra in range(1, min(50, len(remaining_words) - len(words_in_phrase) + 1)):
                candidate = " ".join(remaining_words[: len(words_in_phrase) + n_extra])
                if candidate in full_corpus_text:
                    best_match_words = remaining_words[: len(words_in_phrase) + n_extra]
                else:
                    break

            best_match = " ".join(best_match_words)
            matched_regions.append((sid, field_name, best_match, len(best_match_words)))

            # Marca como visto e avança apenas 1 (para detectar matches em outras regiões)
            seen_starts.add(phrase)
            # Avançar para depois desta região no índice de phrases mínimas
            i += max(1, len(best_match_words) - min_words_warning)
        else:
            i += 1

    # Reportar
    for sid, field_name, match_text, n_words in matched_regions:
        position = manuscript_html.lower().find(match_text[:60])
        if position == -1:
            position = 0

        has_quotes, has_attribution = check_for_quotes_attribution(
            manuscript_html, position, len(match_text)
        )

        # Determina severidade
        if has_quotes and has_attribution:
            severity = "legitimate"
        elif n_words >= min_words_critical and not has_quotes:
            severity = "critical"
        else:
            severity = "warning"

        report.matches.append(PlagiarismMatch(
            n_words=n_words,
            matched_phrase=match_text[:120] + ("..." if len(match_text) > 120 else ""),
            source_id=sid,
            source_field=field_name,
            has_quotes=has_quotes,
            has_attribution=has_attribution,
            severity=severity,
        ))

    return report


def render_plagiarism_summary(report: PlagiarismReport, is_ptbr: bool = True) -> dict:
    """Resumo serializável do relatório (para o JSON de avaliação)."""
    return {
        "layer": report.layer,
        "n_phrases_checked": report.n_phrases_checked,
        "n_sources_compared": report.n_sources_compared,
        "critical_matches": report.critical_matches,
        "warning_matches": report.warning_matches,
        "legitimate_matches": report.legitimate_matches,
        "matches": [
            {
                "n_words": m.n_words,
                "matched_phrase": m.matched_phrase,
                "source_id": m.source_id,
                "source_field": m.source_field,
                "has_quotes": m.has_quotes,
                "has_attribution": m.has_attribution,
                "severity": m.severity,
            }
            for m in report.matches
        ],
        "advisory": (
            "Camada 1 (interna ao corpus) é triagem básica. Para submissão a "
            "venue de elite, recomenda-se passagem em iThenticate/Turnitin/Copyleaks "
            "antes da submissão final."
            if is_ptbr else
            "Layer 1 (corpus internal) is basic triage. For elite venue submission, "
            "recommend running iThenticate/Turnitin/Copyleaks before final submission."
        ),
    }
