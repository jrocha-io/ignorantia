"""
Stage 4: Scope Matching (manuscript ↔ venue).

Combina 4 sinais determinísticos para produzir scope_score ∈ [0,1]:
  1. TF-IDF cosine entre manuscript e venue corpus (peso 0.50)
  2. Thesaurus match entre keywords e descritores controlados (peso 0.25)
  3. Citation overlap entre referências e DOIs típicos do venue (peso 0.15)
  4. Anchor word matching (palavras-chave manualmente curadas no perfil) (peso 0.10)

Sem treinar modelos. Sem GPU. Reproduzível.
"""

from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass

from .parse import ManuscriptDocument


@dataclass
class ScopeScore:
    aggregate: float
    tfidf_cosine: float
    thesaurus_match: float
    citation_overlap: float
    anchor_match: float
    out_of_scope_signals: list[str]


# ---------- TF-IDF mínimo sem sklearn ----------

def _tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"\b[a-zçãõéáíóúñü]{3,}\b", text)


_STOPWORDS_EN = {"the", "and", "for", "with", "this", "that", "from", "are", "was", "were",
                 "have", "has", "had", "will", "would", "could", "should", "been", "being",
                 "more", "than", "into", "such", "its", "any", "all", "but", "not"}
_STOPWORDS_PT = {"para", "com", "que", "uma", "este", "esta", "como", "mais", "mas", "por",
                 "dos", "das", "nos", "nas", "ele", "ela", "eles", "elas", "seu", "sua",
                 "seus", "suas", "também", "ainda", "todos", "todas", "muito", "muita",
                 "ser", "está", "são", "foi", "foram", "tem", "tinha"}
_STOPWORDS_ES = {"para", "con", "que", "una", "los", "las", "del", "más", "pero", "por",
                 "ese", "esa", "este", "esta", "ello", "muy", "más", "ser", "está", "están",
                 "fue", "fueron", "tiene", "tenía"}

_ALL_STOPWORDS = _STOPWORDS_EN | _STOPWORDS_PT | _STOPWORDS_ES


def _filter_tokens(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in _ALL_STOPWORDS and len(t) > 2]


def _term_frequency(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counter = Counter(tokens)
    total = float(sum(counter.values()))
    return {t: c / total for t, c in counter.items()}


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    norm_a = sum(v * v for v in a.values()) ** 0.5
    norm_b = sum(v * v for v in b.values()) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_venue_pseudo_corpus(profile: dict) -> list[str]:
    """Sintetiza um pseudo-corpus do venue a partir dos campos do perfil."""
    parts: list[str] = []
    parts.append(profile.get("metadata", {}).get("name", ""))
    parts.append(profile.get("metadata", {}).get("name_pt", ""))
    soft = profile.get("soft_signals", {}) or {}
    parts.extend(soft.get("scope_keywords", []) or [])
    scope = profile.get("scope", {}) or {}
    parts.extend(scope.get("thesaurus_descriptors", []) or [])
    parts.extend(scope.get("areas_qualis", []) or [])
    return parts


# ---------- Stage 4 main ----------

def compute_scope_score(doc: ManuscriptDocument, profile: dict) -> ScopeScore:
    # 1. TF-IDF cosine (sem IDF real porque corpus é único — vira freq cosine)
    doc_tokens = _filter_tokens(_tokenize(doc.raw_text))
    venue_text = " ".join(_build_venue_pseudo_corpus(profile))
    venue_tokens = _filter_tokens(_tokenize(venue_text))
    tfidf_score = _cosine_similarity(
        _term_frequency(doc_tokens),
        _term_frequency(venue_tokens),
    )

    # 2. Thesaurus match
    descriptors = (profile.get("scope", {}) or {}).get("thesaurus_descriptors", []) or []
    if descriptors:
        text_low = doc.raw_text.lower()
        matches = sum(1 for d in descriptors if d.lower().split(" [")[0] in text_low)
        thesaurus_match = min(matches / max(len(descriptors), 1), 1.0)
    else:
        thesaurus_match = 0.0

    # 3. Citation overlap
    typical_dois = ((profile.get("soft_signals") or {}).get("typical_recent_dois") or [])
    if typical_dois:
        ms_dois = set(re.findall(r"10\.\d{4,9}/[\w./;()\-]+", doc.raw_text))
        venue_dois = set(d.lower() for d in typical_dois)
        if ms_dois:
            overlap = len(ms_dois & venue_dois) / float(len(ms_dois))
            citation_overlap = min(overlap * 5, 1.0)  # multiplicador suave: 20% overlap → 1.0
        else:
            citation_overlap = 0.0
    else:
        citation_overlap = 0.0

    # 4. Anchor match (scope_keywords manualmente curadas)
    scope_keywords = (profile.get("soft_signals") or {}).get("scope_keywords", []) or []
    if scope_keywords:
        text_low = doc.raw_text.lower()
        matches = sum(1 for kw in scope_keywords if kw.lower() in text_low)
        anchor_match = min(matches / max(len(scope_keywords), 1) * 2, 1.0)
    else:
        anchor_match = 0.0

    # 5. Out-of-scope signals (penalty if found)
    out_kws = (profile.get("soft_signals") or {}).get("out_of_scope_keywords", []) or []
    out_signals = []
    if out_kws:
        text_low = doc.raw_text.lower()
        for kw in out_kws:
            if kw.lower() in text_low:
                out_signals.append(kw)

    # Aggregate
    aggregate = (
        0.50 * tfidf_score +
        0.25 * thesaurus_match +
        0.15 * citation_overlap +
        0.10 * anchor_match
    )
    # Penalty leve por out-of-scope
    if out_signals:
        aggregate = max(0.0, aggregate - 0.15 * min(len(out_signals), 3))

    return ScopeScore(
        aggregate=round(aggregate, 4),
        tfidf_cosine=round(tfidf_score, 4),
        thesaurus_match=round(thesaurus_match, 4),
        citation_overlap=round(citation_overlap, 4),
        anchor_match=round(anchor_match, 4),
        out_of_scope_signals=out_signals,
    )
