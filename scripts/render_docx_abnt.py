#!/usr/bin/env python3
"""
render_docx_abnt.py — Render do manuscrito como .docx no padrão ABNT (Decisão 31).

Padrões ABNT aplicados:
- Papel A4, margens superior/esquerda 3cm, inferior/direita 2cm (NBR 14724:2011 §5.1)
- Fonte Times New Roman 12pt para corpo; 10pt para citações longas e notas (§5.2)
- Espaçamento 1,5 entre linhas no corpo; simples em citações longas, notas, referências (§5.3)
- Recuo de parágrafo 1,25cm
- Títulos: §N em negrito, sem pontuação ao final (§5.2.2)
- Citações longas (≥4 linhas): recuo 4cm, fonte 10pt, espaçamento simples, sem aspas
- Referências: alinhadas à esquerda, espaçamento simples, em ordem alfabética por sobrenome
- Numeração de páginas: canto superior direito, a partir da introdução (§5.4)

Para conformidade plena com NBR 14724:2011 (Trabalhos acadêmicos — Apresentação),
NBR 6023:2018 (Referências) e NBR 10520:2023 (Citações), este módulo coopera com
`scripts/format_abnt.py` (que já formata referências e citações como strings).

Aqui aplicamos a formatação tipográfica e estrutural; o conteúdo textual e as
referências formatadas vêm do `content.json` produzido pela Fase 7 do skill.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Cm, Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


@dataclass
class DocxRenderResult:
    output_path: Path
    n_sections: int = 0
    n_references: int = 0
    n_long_quotes: int = 0
    file_size_bytes: int = 0


def _set_abnt_margins(section) -> None:
    """Margens ABNT NBR 14724:2011 §5.1."""
    section.top_margin = Cm(3)
    section.left_margin = Cm(3)
    section.bottom_margin = Cm(2)
    section.right_margin = Cm(2)


def _set_paragraph_abnt_body(paragraph) -> None:
    """Corpo de texto: TNR 12pt, espaçamento 1.5, recuo 1.25cm, justificado."""
    pf = paragraph.paragraph_format
    pf.first_line_indent = Cm(1.25)
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def _set_paragraph_abnt_long_quote(paragraph) -> None:
    """Citação longa: recuo 4cm da margem esquerda, TNR 10pt, espaçamento simples, sem aspas."""
    pf = paragraph.paragraph_format
    pf.left_indent = Cm(4)
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)


def _set_paragraph_abnt_reference(paragraph) -> None:
    """Referência bibliográfica: alinhada à esquerda, TNR 12pt, espaçamento simples, sem recuo."""
    pf = paragraph.paragraph_format
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)  # 6pt entre referências para legibilidade
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def _set_paragraph_abnt_heading(paragraph) -> None:
    """Título de seção: TNR 12pt, negrito, alinhado à esquerda, sem pontuação ao final."""
    pf = paragraph.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.bold = True


def _add_page_numbers(document) -> None:
    """Adiciona numeração de página no canto superior direito (NBR 14724:2011 §5.4)."""
    section = document.sections[0]
    header = section.header
    p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run.font.name = "Times New Roman"
    run.font.size = Pt(10)


def render_docx_abnt(content: dict, output_path: Path,
                     *, title: str, authors: list[str] | None = None,
                     abstract: str | None = None,
                     keywords: list[str] | None = None,
                     contextual_preamble_markdown: str | None = None
                     ) -> DocxRenderResult:
    """Renderiza o manuscrito completo como .docx ABNT.

    Args:
        content: dict com chaves esperadas:
            - "sections": [{"id", "title", "paragraphs": [{"text", "type"?: "body"|"long_quote"}]}]
            - "references": [str já formatadas em ABNT NBR 6023:2018]
            - opcionalmente "abstract", "keywords", "authors"
        contextual_preamble_markdown: F4 (v2.18.1, DD-11) — se fornecido, gera seção
            "O campo onde este artigo vive" antes da Introdução. String em Markdown
            (formato gerado por `ContextualPreamble.render_markdown()`).
    """
    if not DOCX_AVAILABLE:
        raise RuntimeError(
            "python-docx não instalado. Instale com `pip install python-docx`."
        )

    doc = Document()
    section = doc.sections[0]
    _set_abnt_margins(section)
    _add_page_numbers(doc)

    # Título
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    run.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)

    # Autores
    authors = authors or content.get("authors", [])
    if authors:
        p = doc.add_paragraph(); run = p.add_run("; ".join(authors))
        run.font.name = "Times New Roman"; run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(24)

    # Abstract / Resumo
    abstract = abstract or content.get("abstract")
    if abstract:
        p = doc.add_paragraph(); run = p.add_run("Resumo")
        _set_paragraph_abnt_heading(p)
        for run in p.runs:
            run.bold = True
        p2 = doc.add_paragraph(abstract)
        _set_paragraph_abnt_body(p2)
        p2.paragraph_format.first_line_indent = Cm(0)  # resumo sem recuo de primeira linha
        # Palavras-chave
        kws = keywords or content.get("keywords", [])
        if kws:
            p3 = doc.add_paragraph()
            r = p3.add_run("Palavras-chave: ")
            r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(12)
            r2 = p3.add_run("; ".join(kws) + ".")
            r2.font.name = "Times New Roman"; r2.font.size = Pt(12)
            p3.paragraph_format.space_after = Pt(18)

    # Seções
    n_long_quotes = 0

    # F4 (v2.18.1, DD-11): preâmbulo contextual ANTES das seções principais
    if contextual_preamble_markdown:
        # Renderizar markdown do preâmbulo como seção docx
        # Estrutura esperada do markdown: "## Título\n\n*nota*\n\nparágrafos..."
        preamble_lines = contextual_preamble_markdown.strip().split("\n")
        preamble_title = "O campo onde este artigo vive"
        for line in preamble_lines:
            if line.startswith("## "):
                preamble_title = line[3:].strip()
                break
        # Heading do preâmbulo
        heading = doc.add_paragraph()
        heading.add_run(preamble_title)
        _set_paragraph_abnt_heading(heading)
        for r in heading.runs:
            r.bold = True
        # Corpo: pega tudo após o ## inicial, até "### Referências contextuais"
        body_started = False
        in_refs = False
        for line in preamble_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("## "):
                if stripped.startswith("## "):
                    body_started = True
                continue
            if stripped.startswith("### Referências"):
                in_refs = True
                # Sub-heading
                p = doc.add_paragraph()
                p.add_run(stripped.lstrip("# ").strip())
                _set_paragraph_abnt_heading(p)
                for r in p.runs:
                    r.italic = True
                continue
            if stripped.startswith("### "):
                p = doc.add_paragraph()
                p.add_run(stripped.lstrip("# ").strip())
                _set_paragraph_abnt_heading(p)
                continue
            if not body_started:
                continue
            # Parágrafo normal
            p = doc.add_paragraph(stripped)
            _set_paragraph_abnt_body(p)
        # Espaço após preâmbulo
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(18)

    sections = content.get("sections", [])
    for s in sections:
        sec_id = s.get("id", "")
        sec_title = s.get("title", "")
        heading = doc.add_paragraph()
        heading.add_run(f"§{sec_id} {sec_title}".strip())
        _set_paragraph_abnt_heading(heading)

        paragraphs = s.get("paragraphs", [])
        # Compat: se a seção vier com "content_html" (formato render_chunks), extrair texto
        if not paragraphs and s.get("content_html"):
            paragraphs = [{"text": _strip_html(s["content_html"]), "type": "body"}]

        for para in paragraphs:
            text = para.get("text", "")
            ptype = para.get("type", "body")
            if not text.strip():
                continue
            p = doc.add_paragraph(text)
            if ptype == "long_quote":
                _set_paragraph_abnt_long_quote(p)
                n_long_quotes += 1
            elif ptype == "reference":
                _set_paragraph_abnt_reference(p)
            else:
                _set_paragraph_abnt_body(p)

    # Referências
    refs = content.get("references", [])
    if refs:
        h = doc.add_paragraph(); h.add_run("Referências")
        _set_paragraph_abnt_heading(h)
        for r in refs:
            p = doc.add_paragraph(r)
            _set_paragraph_abnt_reference(p)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))

    return DocxRenderResult(
        output_path=output_path,
        n_sections=len(sections),
        n_references=len(refs),
        n_long_quotes=n_long_quotes,
        file_size_bytes=output_path.stat().st_size,
    )


def _strip_html(html: str) -> str:
    """Remove tags HTML básicas para extrair texto plano."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>\s*<p[^>]*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _cli() -> int:
    p = argparse.ArgumentParser(description="Render manuscrito como .docx ABNT (Decisão 31).")
    p.add_argument("--content-json", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--title", required=True)
    # F4 (v2.18.1, DD-11)
    p.add_argument("--contextual-preamble", action="store_true",
                   help="Inclui seção 'O campo onde este artigo vive' (Wikipedia + Wikidata) "
                        "antes da Introdução.")
    p.add_argument("--preamble-topic", default=None)
    p.add_argument("--preamble-area", default="multi")
    p.add_argument("--preamble-language", default="pt-BR")
    p.add_argument("--preamble-mock", action="store_true")
    args = p.parse_args()
    content = json.loads(Path(args.content_json).read_text(encoding="utf-8"))

    preamble_md = None
    if args.contextual_preamble:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from contextual_preamble import ContextualPreamble, _mock_preamble
            topic = args.preamble_topic or args.title
            if args.preamble_mock:
                cp = _mock_preamble(topic, args.preamble_area, args.preamble_language)
            else:
                cp = ContextualPreamble(language=args.preamble_language)
                cp.set_topic(topic, area=args.preamble_area)
                try:
                    cp.fetch_wikipedia_context()
                    cp.fetch_wikidata_entities()
                except Exception:
                    pass
            preamble_md = cp.render_markdown()
        except ImportError:
            print("[render_docx_abnt] WARN: contextual_preamble não disponível; "
                  "renderizando sem preâmbulo.", file=sys.stderr)

    result = render_docx_abnt(content, Path(args.output), title=args.title,
                                contextual_preamble_markdown=preamble_md)
    print(f"[render_docx_abnt] {result.n_sections} seções, "
          f"{result.n_references} refs, {result.n_long_quotes} citações longas, "
          f"{result.file_size_bytes} bytes → {result.output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
