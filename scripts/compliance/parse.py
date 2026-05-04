"""
Stage 1: Parse & Normalize.

Recebe manuscrito em formato bruto (HTML, DOCX, TXT, JATS XML) e produz
representação interna estruturada (ManuscriptDocument).

Para v2.0, suporta:
  - HTML (preferred — formato nativo do ignorantia)
  - TXT (fallback)
  - DOCX (via python-docx se disponível; senão exige pre-conversão)
  - JATS XML (parser leve para extração de seções)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ManuscriptDocument:
    """Representação canônica do manuscrito após parsing."""
    raw_text: str = ""
    title: str = ""
    abstract: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    references_block: str = ""
    declarations: dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    char_count_with_spaces: int = 0
    detected_language: str = "unknown"
    source_path: Optional[str] = None
    source_format: str = "unknown"
    parse_warnings: list[str] = field(default_factory=list)


# ---------- Helpers ----------

def _strip_html(html: str) -> str:
    """Remove tags HTML preservando conteúdo textual.
    Implementação manual sem dependência (BeautifulSoup é heavyweight)."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _detect_language(text: str) -> str:
    """Heurística leve sem dependências externas.
    Conta marcadores de cada idioma."""
    sample = text.lower()[:5000]
    pt_markers = ["é ", "são ", "não ", "também ", "está ", "tem ", "para ", "com ", "uma ", "de "]
    en_markers = [" the ", " is ", " are ", " of ", " in ", " and ", " to ", " for ", " with ", " that "]
    es_markers = [" es ", " son ", " no ", " también ", " está ", " para ", " con ", " una ", " del ", " que "]
    pt_count = sum(sample.count(m) for m in pt_markers)
    en_count = sum(sample.count(m) for m in en_markers)
    es_count = sum(sample.count(m) for m in es_markers)
    counts = {"pt": pt_count, "en": en_count, "es": es_count}
    if max(counts.values()) < 3:
        return "unknown"
    return max(counts, key=counts.get)


def _extract_html_sections(html: str) -> dict[str, str]:
    """Extrai seções por h1/h2/h3 do HTML."""
    sections: dict[str, str] = {}
    # Match <h1|h2|h3>Heading</h1...> + conteúdo até próximo cabeçalho
    pattern = r"<h[1-3][^>]*>(.*?)</h[1-3]>(.*?)(?=<h[1-3]|\Z)"
    for match in re.finditer(pattern, html, flags=re.DOTALL | re.IGNORECASE):
        heading = _strip_html(match.group(1)).strip()
        body = _strip_html(match.group(2)).strip()
        if heading:
            sections[heading.lower()] = body
    return sections


def _extract_html_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return _strip_html(m.group(1)).strip()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return _strip_html(m.group(1)).strip()
    return ""


def _extract_abstract(text: str, sections: dict) -> str:
    """Procura a seção 'abstract' / 'resumo' / 'resumen'."""
    for key in ("abstract", "resumo", "resumen"):
        for sec_key, content in sections.items():
            if key in sec_key:
                return content
    # Fallback heurístico: primeiro parágrafo após título
    return ""


def _extract_declarations(text: str) -> dict[str, str]:
    """Procura declarações comuns em qualquer lugar do texto."""
    declarations: dict[str, str] = {}
    text_lower = text.lower()

    patterns = {
        "conflicts_of_interest": [
            r"(?:conflict[s]? of interest|competing interest[s]?|conflito[s]? de interesse)[\s\S]{0,500}",
            r"(?:declaration of (?:competing )?interest)[\s\S]{0,500}",
        ],
        "funding": [
            r"(?:funding|financiamento)[\s\S]{0,500}",
            r"(?:supported by|grant)[\s\S]{0,300}",
        ],
        "ai_usage": [
            r"(?:declaração de uso de ia[sg]?|declaration of ai use|generative ai|ai-assisted|chatgpt|gpt-?[345]|claude(?:[\s\-]\d)?|gemini)[\s\S]{0,500}",
        ],
        "ethics_approval": [
            r"(?:ethics committee|comitê de ética|cep[/\s]conep|irb|institutional review board|ethics approval|aprovação ética)[\s\S]{0,500}",
        ],
        "data_availability": [
            r"(?:data availability|disponibilidade de dados|code availability|materials availability|supplementary materials?)[\s\S]{0,500}",
        ],
        "prospero_registration": [
            r"crd\d{6,9}",
            r"prospero",
        ],
        "trial_registration": [
            r"nct\d{8}",
            r"isrctn\d+",
            r"chictr\d+",
        ],
        "orcid": [
            r"\d{4}-\d{4}-\d{4}-\d{3}[\dx]",
        ],
        "preregistration_link": [
            r"osf\.io/\w+",
            r"doi\.org/[\w./]+protocol",
        ],
    }

    for decl_id, patterns_list in patterns.items():
        matches = []
        for p in patterns_list:
            for m in re.finditer(p, text_lower, flags=re.IGNORECASE):
                matches.append(m.group(0)[:200])
        if matches:
            declarations[decl_id] = " | ".join(matches[:3])
    return declarations


def _count_words_chars(text: str) -> tuple[int, int]:
    words = len(re.findall(r"\b\w+\b", text))
    chars = len(text)
    return words, chars


# ---------- Public API ----------

def parse_manuscript(source: str | Path | None = None, raw_text: str | None = None,
                     source_format: str = "auto") -> ManuscriptDocument:
    """Parse manuscript into ManuscriptDocument.

    Args:
        source: caminho de arquivo (HTML, TXT, DOCX, JATS XML)
        raw_text: ou conteúdo bruto direto
        source_format: 'auto' detecta pela extensão; ou 'html', 'txt', 'jats'
    """
    if raw_text is None and source is None:
        raise ValueError("Either source or raw_text must be provided")

    if raw_text is None:
        path = Path(source)
        raw = path.read_text(encoding="utf-8", errors="replace")
        if source_format == "auto":
            ext = path.suffix.lower()
            if ext in {".html", ".htm"}:
                source_format = "html"
            elif ext == ".xml":
                source_format = "jats"
            elif ext == ".txt":
                source_format = "txt"
            else:
                source_format = "txt"
        source_path = str(path)
    else:
        raw = raw_text
        source_path = None
        if source_format == "auto":
            source_format = "html" if "<html" in raw[:500].lower() or "<body" in raw[:500].lower() else "txt"

    doc = ManuscriptDocument(source_path=source_path, source_format=source_format)

    if source_format == "html":
        doc.title = _extract_html_title(raw)
        doc.sections = _extract_html_sections(raw)
        text = _strip_html(raw)
        doc.raw_text = text
        doc.abstract = _extract_abstract(text, doc.sections)
    else:
        # txt fallback / jats minimal
        doc.raw_text = raw
        # heurística: primeira linha não-vazia é título
        for line in raw.splitlines():
            if line.strip():
                doc.title = line.strip()[:300]
                break
        # seções por linhas em maiúsculo-like
        sec_pattern = re.compile(r"^\s*(?:\d+\.?\s+)?([A-Z][A-Za-zçãõéáíóú\s]{2,60})\s*$", re.MULTILINE)
        # parsing simplificado para txt
        doc.sections = {}

    doc.word_count, doc.char_count_with_spaces = _count_words_chars(doc.raw_text)
    doc.detected_language = _detect_language(doc.raw_text)
    doc.declarations = _extract_declarations(doc.raw_text)

    if not doc.title:
        doc.parse_warnings.append("Title not extracted; document may be malformed")
    if doc.word_count < 200:
        doc.parse_warnings.append(f"Very short document: {doc.word_count} words")

    return doc
