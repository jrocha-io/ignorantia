"""
ignorantia.assessor.visual_aids — TLDR cards, grifos de keywords-tema, marca-texto de claims (Rodada G).

Três features visuais para acelerar leitura crítica:

1. **TLDR cards**: para cada RQ, extrai a primeira frase da subsection
   correspondente em `synthesis_html` e produz um card visual no topo do
   manuscrito.

2. **Keywords-tema**: extrai termos relevantes do título + RQs do próprio
   trabalho (não do venue) e os envolve em <mark class="topic-kw"> nas
   seções narrativas, para o leitor identificar rapidamente onde cada
   palavra-chave central aparece.

3. **Marca-texto de claims**: sentenças contendo ≥1 citação [N] são
   envoltas em <span class="claim"> com fundo sutil — deixa visualmente
   claro o que é claim verificável vs. prosa explanatória.

Tudo é determinístico, offline, baseado em regex sobre o conteúdo HTML.
Não inventa conteúdo; apenas decora o existente.
"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import Iterable

from .helpers import strip_html


# ── Stop-words PT/EN para extração de keywords-tema ─────────────────


STOPWORDS = {
    # PT-BR
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "para", "por", "com", "sem", "sobre", "sob",
    "que", "qual", "quais", "como", "onde", "quando", "porque", "porquê",
    "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
    "aquele", "aquela", "isto", "isso", "aquilo",
    "ser", "estar", "ter", "haver", "fazer", "ir", "vir", "poder", "dever",
    "é", "são", "foi", "foram", "será", "seria", "tem", "têm", "tinha",
    "se", "sua", "seu", "suas", "seus", "ele", "ela", "eles", "elas",
    "mas", "ou", "e", "também", "ainda", "já", "mais", "menos", "muito",
    "pela", "pelo", "pelas", "pelos", "ao", "aos", "à", "às", "no", "nos",
    "deste", "desta", "desse", "dessa", "neste", "nesta", "nele", "nela",
    "à", "às", "uma", "umas", "qual", "quais", "todos", "todas", "outro", "outra",
    "rq", "rq1", "rq2", "rq3", "rq4", "rq5",
    # EN
    "the", "a", "an", "of", "for", "in", "on", "at", "by", "with", "without",
    "about", "and", "or", "but", "if", "while", "to", "from",
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
    "do", "does", "did", "this", "that", "these", "those",
    "it", "its", "their", "his", "her", "they", "them", "we", "our",
    "what", "which", "who", "where", "when", "why", "how",
    "as", "than", "such", "more", "most", "less", "least", "very",
}


# ── 1. TLDR cards a partir de RQs ───────────────────────────────────


def extract_tldr_from_synthesis(synthesis_html: str, rqs: list[str]) -> list[dict]:
    """Para cada RQ, tenta extrair a primeira frase da subsection correspondente
    em synthesis_html.

    Convenção esperada: synthesis_html usa <h3> ou <h4> com 'RQ1', 'RQ2' etc.
    para delimitar subseções. Caso não haja, retorna lista vazia (sem TLDR).

    Returns list of dicts: {rq_id, rq_text, tldr_sentence}
    """
    if not rqs or not synthesis_html:
        return []

    out = []
    # Para cada RQ, encontrar bloco que comece com h3/h4 contendo "RQ{N}"
    for i, rq in enumerate(rqs, start=1):
        rq_label = f"RQ{i}"
        # Padrão: <h3>RQ{N} ... </h3> seguido de conteúdo até próximo h3 ou fim
        pattern = re.compile(
            rf"<h[34][^>]*>[^<]*{re.escape(rq_label)}[^<]*</h[34]>"
            r"(.+?)"
            r"(?=<h[34]|$)",
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(synthesis_html)
        if not m:
            continue
        block = m.group(1)
        plain = strip_html(block).strip()
        if not plain:
            continue
        # Primeira frase: até primeiro . ! ? seguido de espaço ou fim
        # Cuidado: 'Smith et al.' não é fim. Heurística: . seguido de espaço + maiúscula.
        sent_match = re.match(r"(.+?[.!?])(?:\s+[A-ZÀ-Ú]|\s*$)", plain)
        if sent_match:
            sentence = sent_match.group(1).strip()
        else:
            # Fallback: primeiros 200 chars
            sentence = plain[:200].rsplit(" ", 1)[0] + "…"
        out.append({
            "rq_id": rq_label,
            "rq_text": rq.strip(),
            "tldr_sentence": sentence,
        })
    return out


def render_tldr_cards_html(tldrs: list[dict], lang: str = "pt-BR") -> str:
    """Renderiza cards TLDR em HTML horizontal."""
    if not tldrs:
        return ""
    is_ptbr = lang.lower().startswith("pt")
    label_tldr = "TL;DR" if is_ptbr else "TL;DR"
    intro = (
        "Resumo de uma frase para cada pergunta de pesquisa. Extraído da síntese — não foi reescrito."
        if is_ptbr else
        "One-sentence summary per research question. Extracted from synthesis — not rewritten."
    )

    cards_html = []
    for t in tldrs:
        rq_id = html_escape(t["rq_id"])
        rq_text = html_escape(t["rq_text"])
        tldr = html_escape(t["tldr_sentence"])
        # Limpar prefixo "RQ1: " do rq_text se presente
        rq_text_clean = re.sub(r"^RQ\d+\s*[:\-—]\s*", "", rq_text)
        cards_html.append(
            f'<article class="tldr-card">'
            f'<header class="tldr-card-head">'
            f'<span class="tldr-badge">{label_tldr}</span>'
            f'<span class="tldr-rq-id">{rq_id}</span>'
            f'</header>'
            f'<p class="tldr-rq-text">{rq_text_clean}</p>'
            f'<p class="tldr-sentence">{tldr}</p>'
            f'</article>'
        )

    return (
        '<section class="tldr-section" aria-label="' + (
            "Resumos de uma frase por RQ" if is_ptbr else "One-sentence summaries per RQ"
        ) + '">'
        f'<p class="tldr-intro">{html_escape(intro)}</p>'
        '<div class="tldr-grid">'
        + "".join(cards_html)
        + '</div>'
        '</section>'
    )


# ── 2. Keywords-tema ────────────────────────────────────────────────


def extract_topic_keywords(content: dict, max_keywords: int = 8) -> list[str]:
    """Extrai keywords-tema do título + RQs do próprio trabalho.

    Estratégia: tokenizar título + RQs, remover stopwords, contar n-gramas
    (1-grama e 2-grama), retornar os mais frequentes com tamanho ≥ 4.

    O título tem peso maior (3×) que RQs (1×) porque concentra o tema central.
    Bigrams com verbos ou tokens funcionais são filtrados.
    """
    title = (content.get("title", "") or "") + " " + (content.get("subtitle", "") or "")
    rqs_text = " ".join(content.get("rqs", []) or [])

    title_lower = title.lower()
    rqs_lower = rqs_text.lower()

    # Função auxiliar: limpar e tokenizar
    def tokenize(text: str) -> list[str]:
        cleaned = re.sub(r"[^\wÀ-ÿ\s\-]", " ", text)
        return [t for t in cleaned.split() if len(t) >= 4 and t not in STOPWORDS]

    title_tokens = tokenize(title_lower)
    rqs_tokens = tokenize(rqs_lower)

    # Verbos comuns PT/EN que poluem bigrams se aparecerem (sufixos típicos)
    VERB_SUFFIXES_PT = ("ar", "er", "ir", "ando", "endo", "indo", "ado", "ido",
                        "ou", "am", "em", "iam", "ram", "ria", "iam")
    VERB_BLOCKLIST = {
        "afeta", "aparecem", "afetam", "aparece", "aparecer", "afetando",
        "exigem", "exige", "exigir", "tornam", "torna", "exibe", "exibem",
        "varia", "variam", "ocorrem", "ocorre", "mostra", "mostram",
        "discute", "discutem", "considera", "consideram",
        "affect", "affects", "appear", "appears", "show", "shows",
        "discuss", "discusses", "consider", "considers",
    }

    def is_verb_like(tok: str) -> bool:
        if tok in VERB_BLOCKLIST:
            return True
        # PT verbos típicos de RQ: "afeta", "exibe", "mostra"
        if any(tok.endswith(s) for s in VERB_SUFFIXES_PT) and len(tok) <= 8:
            return True
        return False

    # 1-gramas com peso (título peso 3, RQs peso 1)
    counts: dict[str, int] = {}
    for tok in title_tokens:
        counts[tok] = counts.get(tok, 0) + 3
    for tok in rqs_tokens:
        counts[tok] = counts.get(tok, 0) + 1

    # 2-gramas: extrair separadamente do título (peso 6) e das RQs (peso 2)
    def extract_bigrams(text: str, weight: int) -> None:
        word_seq = re.findall(r"\b[\wÀ-ÿ\-]{3,}\b", text.lower())
        for i in range(len(word_seq) - 1):
            a, b = word_seq[i], word_seq[i + 1]
            if a in STOPWORDS or b in STOPWORDS:
                continue
            if len(a) < 4 or len(b) < 4:
                continue
            if is_verb_like(a) or is_verb_like(b):
                continue
            bigram = f"{a} {b}"
            counts[bigram] = counts.get(bigram, 0) + weight

    extract_bigrams(title_lower, 6)
    extract_bigrams(rqs_lower, 2)

    # Filtrar 1-gramas que sejam verbos
    counts = {k: v for k, v in counts.items() if " " in k or not is_verb_like(k)}

    # Ordenar: contagem desc, depois priorizar bigramas (mais discriminantes)
    sorted_kws = sorted(counts.items(), key=lambda x: (-x[1], -(" " in x[0]), -len(x[0])))

    # Filtrar redundância: se um bigrama foi escolhido, suas partes individuais
    # ainda podem entrar (útil para grifar palavra única quando não está em par)
    chosen = []
    chosen_set = set()
    for kw, _ in sorted_kws:
        if kw in chosen_set:
            continue
        chosen.append(kw)
        chosen_set.add(kw)
        if len(chosen) >= max_keywords:
            break

    return chosen


def highlight_keywords(html: str, keywords: list[str]) -> str:
    """Envolve ocorrências de keywords-tema em <mark class="topic-kw">.

    Não toca em conteúdo dentro de tags HTML (atributos, scripts, etc.).
    Não toca em conteúdo dentro de [N] (citações).
    """
    if not html or not keywords:
        return html

    # Construir regex única com alternativas, ordenando por tamanho desc para
    # casar 2-gramas antes de 1-gramas
    sorted_kws = sorted(keywords, key=lambda k: -len(k))
    escaped = [re.escape(k) for k in sorted_kws]
    # Word boundary unicode-aware: usar lookaround em chars não-palavra
    kw_pattern = re.compile(
        r"(?<![\wÀ-ÿ])(" + "|".join(escaped) + r")(?![\wÀ-ÿ])",
        re.IGNORECASE,
    )

    # Estratégia: dividir em segmentos protegidos (tags, citações) vs texto livre
    # e aplicar a substituição apenas em texto livre.
    segments = []
    last = 0
    # Match de tags HTML completas + citações [N]
    protect_pattern = re.compile(r"(<[^>]+>|\[\d+(?:\s*,\s*\d+)*\])")
    for m in protect_pattern.finditer(html):
        if m.start() > last:
            segments.append(("text", html[last:m.start()]))
        segments.append(("protected", m.group(0)))
        last = m.end()
    if last < len(html):
        segments.append(("text", html[last:]))

    # Aplicar marca em texto livre
    out = []
    for kind, seg in segments:
        if kind == "text":
            seg = kw_pattern.sub(r'<mark class="topic-kw">\1</mark>', seg)
        out.append(seg)
    return "".join(out)


# ── 3. Marca-texto de claims (sentenças com [N]) ────────────────────


# Pattern de fim de sentença: . ! ? seguido de espaço + maiúscula, ou fim de string/parágrafo.
# Usamos um regex que captura sentenças completas dentro de blocos de texto.
SENTENCE_PATTERN = re.compile(
    r"([^.!?]*?\[\d+(?:\s*,\s*\d+)*\][^.!?]*?[.!?])(?=\s|$|<)",
    re.DOTALL,
)


def mark_claims(html: str) -> str:
    """Envolve sentenças contendo ≥1 citação [N] em <span class="claim">.

    Estratégia conservadora: opera apenas em texto livre (não dentro de tags),
    e só envolve sentenças que terminem em pontuação.
    """
    if not html:
        return html

    # Dividir em segmentos protegidos vs texto livre
    segments = []
    last = 0
    # Apenas tags HTML são protegidas (citações [N] devem ficar no texto para serem marcadas)
    tag_pattern = re.compile(r"<[^>]+>")
    for m in tag_pattern.finditer(html):
        if m.start() > last:
            segments.append(("text", html[last:m.start()]))
        segments.append(("tag", m.group(0)))
        last = m.end()
    if last < len(html):
        segments.append(("text", html[last:]))

    # Em cada segmento de texto, marcar sentenças com [N]
    out = []
    for kind, seg in segments:
        if kind == "text" and "[" in seg:
            # Para cada match de sentença com citação, envolver
            # Mas precisamos deixar o texto sem citação inalterado
            new_seg = SENTENCE_PATTERN.sub(r'<span class="claim">\1</span>', seg)
            out.append(new_seg)
        else:
            out.append(seg)
    return "".join(out)


# ── Decoração orquestrada ───────────────────────────────────────────


def decorate_section(html: str, keywords: list[str]) -> str:
    """Aplica grifos + marca-texto em uma seção HTML.

    Ordem importa: claims primeiro (envolvem sentenças inteiras), depois
    keywords (envolvem palavras dentro). Assim, <mark> fica aninhado em <span class="claim">,
    o que renderiza corretamente.
    """
    if not html:
        return html
    html = mark_claims(html)
    html = highlight_keywords(html, keywords)
    return html
