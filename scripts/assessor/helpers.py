"""ignorantia.assessor.helpers — funções utilitárias."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


def file_text(path: str | Path) -> str:
    """Read file as text; return empty string if not exists."""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def load_json(path: str | Path) -> Any | None:
    """Load JSON; return None on failure."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_csv(path: str | Path) -> list[dict]:
    """Load CSV as list of dicts."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except (csv.Error, OSError):
        return []


def sha256_short(path: str | Path, length: int = 12) -> str | None:
    """Compute first N chars of SHA-256 of file."""
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:length]
    except OSError:
        return None


def strip_html(text: str) -> str:
    """Remove HTML tags from string."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text).strip()


def word_count(text: str) -> int:
    """Count words in text (ignoring HTML)."""
    return len(strip_html(text).split())


def html_escape(s: str) -> str:
    """HTML-escape (single function alias)."""
    return html.escape(s or "", quote=True)


def floor_to_decimal(value: float, decimals: int = 1) -> float:
    """Round DOWN to N decimals — never up."""
    multiplier = 10 ** decimals
    return int(value * multiplier) / multiplier


def consecutive_words(text: str, min_words: int = 12) -> list[str]:
    """Extract sequences of N+ consecutive non-punctuation tokens.

    Returns list of phrases (lowercased) of exactly min_words words each,
    in sliding window over the entire text (ignoring sentence boundaries).
    Useful for plagiarism detection at phrase level.
    """
    if not text:
        return []
    text = strip_html(text)
    # tokenize to words (alphanumeric + accents + apostrophes/hyphens)
    tokens = re.findall(r"\b[\w\u00C0-\u017F'-]+\b", text.lower())
    if len(tokens) < min_words:
        return []
    phrases = []
    for start in range(len(tokens) - min_words + 1):
        phrase = " ".join(tokens[start : start + min_words])
        phrases.append(phrase)
    return phrases


def detect_lang_is_ptbr(content_or_lang: dict | str) -> bool:
    """Decide if content/manuscript is pt-BR."""
    if isinstance(content_or_lang, str):
        return content_or_lang.lower().startswith("pt")
    if isinstance(content_or_lang, dict):
        lang = (content_or_lang.get("lang") or "pt-BR").lower()
        return lang.startswith("pt")
    return True


def regex_any(text: str, patterns: list[str], flags: int = re.IGNORECASE) -> bool:
    """Return True if any of the given regex patterns matches the text."""
    if not text:
        return False
    for p in patterns:
        if re.search(p, text, flags):
            return True
    return False


def regex_count(text: str, pattern: str, flags: int = re.IGNORECASE) -> int:
    """Count regex matches in text."""
    if not text:
        return 0
    return len(re.findall(pattern, text, flags))
