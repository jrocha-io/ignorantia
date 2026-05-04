#!/usr/bin/env python3
"""
format_abnt.py — Formatador de referências e citações ABNT.

Implementa as duas normas que regem trabalhos científicos em pt-BR:

- **NBR 6023:2018** (Referências) — formato canônico de listagem na seção §Referências.
- **NBR 10520:2023** (Citações) — formato de citação no corpo do texto (autor-data).

Decisão 28 (v2.9.0): formatação ABNT detalhada é OBRIGATÓRIA quando o idioma do
manuscrito é pt-BR. A v2.8.0 anterior usava "ABNT simplificada"; a v2.9.0 adota a
norma plena com casos cobertos: artigo de periódico, livro, capítulo de livro, tese,
dissertação, monografia, evento (anais), documento eletrônico (com DOI/URL), recurso
audiovisual, legislação, e referências sem autoria identificada.

Citações no texto seguem o sistema autor-data ABNT (NBR 10520:2023):
- Citação direta curta (até 3 linhas): integrada ao parágrafo, entre aspas, com (AUTOR, ano, p. N).
- Citação direta longa (≥ 4 linhas): destaque em parágrafo recuado 4cm, fonte 10pt, sem aspas.
- Citação indireta: paráfrase com (AUTOR, ano).
- Apud: citação de citação, formato (AUTOR ORIGINAL, ano apud AUTOR CITANTE, ano).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Reference:
    """Representação canônica de uma referência bibliográfica."""
    type: str  # article|book|book_chapter|thesis|dissertation|conference|electronic|legislation|av_resource|website
    authors: list[str] = field(default_factory=list)
    title: str = ""
    year: int | None = None
    venue: str = ""  # journal name | publisher | conference name | institution
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    accessed: str | None = None  # data ISO
    location: str | None = None  # cidade
    publisher: str | None = None
    chapter_title: str | None = None  # para book_chapter
    book_editors: list[str] | None = None  # para book_chapter
    program: str | None = None  # para tese/dissertação
    institution: str | None = None
    raw: dict | None = None


def _format_authors_abnt(authors: list[str]) -> str:
    """Formata lista de autores no padrão ABNT NBR 6023:2018.

    Padrão: SOBRENOME, Nome (todos em caixa-alta para sobrenome).
    1 autor: SILVA, J. P.
    2 autores: SILVA, J. P.; PEREIRA, A. R.
    3 autores: SILVA, J. P.; PEREIRA, A. R.; LIMA, M. C.
    4+ autores: SILVA, J. P. et al. (ou todos, conforme política do periódico).

    Esta implementação: até 3 autores listados; 4+ usa "et al." conforme
    NBR 6023:2018 §8.1.1.2.
    """
    if not authors:
        return "[s.a.]"  # sine auctore
    formatted = []
    for a in authors[:3]:
        a = a.strip()
        if "," in a:
            # já está como "Sobrenome, Nome"
            parts = a.split(",", 1)
            sobrenome = parts[0].strip().upper()
            nome = parts[1].strip()
            formatted.append(f"{sobrenome}, {_initials(nome)}")
        elif " " in a:
            # "Nome Sobrenome"
            tokens = a.rsplit(" ", 1)
            nome = tokens[0].strip()
            sobrenome = tokens[1].strip().upper()
            formatted.append(f"{sobrenome}, {_initials(nome)}")
        else:
            formatted.append(a.upper())
    out = "; ".join(formatted)
    if len(authors) > 3:
        out += " et al."
    return out


def _initials(full_name: str) -> str:
    """Converte 'João Paulo' em 'J. P.'."""
    parts = [p for p in full_name.replace(".", "").split() if p]
    return ". ".join(p[0].upper() for p in parts) + "." if parts else ""


def _format_doi_or_url(ref: Reference) -> str:
    """Componente final da referência: DOI > URL com data de acesso."""
    if ref.doi:
        return f"DOI: {ref.doi}."
    if ref.url:
        accessed = ref.accessed or ""
        if accessed:
            return f"Disponível em: {ref.url}. Acesso em: {accessed}."
        return f"Disponível em: {ref.url}."
    return ""


def format_reference_abnt(ref: Reference) -> str:
    """Formata uma referência no padrão ABNT NBR 6023:2018."""
    authors = _format_authors_abnt(ref.authors)
    end = _format_doi_or_url(ref)

    if ref.type == "article":
        # SILVA, J. P. Título do artigo. Nome do Periódico, v. X, n. Y, p. ZZ-ZZ, ano. DOI: ...
        parts = [authors + ".", f"{ref.title}.", f"**{ref.venue}**,"]
        loc_bits = []
        if ref.volume:
            loc_bits.append(f"v. {ref.volume}")
        if ref.issue:
            loc_bits.append(f"n. {ref.issue}")
        if ref.pages:
            loc_bits.append(f"p. {ref.pages}")
        if loc_bits:
            parts.append(", ".join(loc_bits) + ",")
        if ref.year:
            parts.append(f"{ref.year}.")
        if end:
            parts.append(end)
        return " ".join(parts)

    if ref.type == "book":
        # SILVA, J. P. Título do livro. Edição. Cidade: Editora, ano.
        parts = [authors + ".", f"**{ref.title}**."]
        if ref.location:
            parts.append(f"{ref.location}:")
        if ref.publisher:
            sep = "," if ref.location else ""
            parts.append(f"{ref.publisher}{sep}")
        if ref.year:
            parts.append(f"{ref.year}.")
        if end:
            parts.append(end)
        return " ".join(parts)

    if ref.type == "book_chapter":
        # SILVA, J. P. Título do capítulo. In: EDITOR (org.). Título do livro. Cidade: Editora, ano. p. ZZ-ZZ.
        parts = [authors + ".", f"{ref.chapter_title or ref.title}.", "In:"]
        if ref.book_editors:
            parts.append(_format_authors_abnt(ref.book_editors) + " (org.).")
        parts.append(f"**{ref.title}**.")
        if ref.location:
            parts.append(f"{ref.location}:")
        if ref.publisher:
            sep = "," if ref.location else ""
            parts.append(f"{ref.publisher}{sep}")
        if ref.year:
            parts.append(f"{ref.year}.")
        if ref.pages:
            parts.append(f"p. {ref.pages}.")
        if end:
            parts.append(end)
        return " ".join(parts)

    if ref.type in ("thesis", "dissertation"):
        # SILVA, J. P. Título. Ano. Tipo (Programa) — Instituição, Cidade, ano.
        thesis_label = "Tese (Doutorado em" if ref.type == "thesis" else "Dissertação (Mestrado em"
        program = f" {ref.program})" if ref.program else ")"
        parts = [authors + ".", f"**{ref.title}**.",
                 f"{ref.year}." if ref.year else "",
                 f"{thesis_label}{program}", "—",
                 f"{ref.institution}," if ref.institution else "",
                 f"{ref.location}," if ref.location else "",
                 f"{ref.year}." if ref.year else ""]
        return " ".join(p for p in parts if p)

    if ref.type == "conference":
        # SILVA, J. P. Título. In: NOME DO EVENTO, edição, ano, Cidade. Anais [...]. Cidade: Editora, ano. p. X-Y.
        parts = [authors + ".", f"{ref.title}.", "In:", f"**{ref.venue}**,",
                 f"{ref.year}," if ref.year else "",
                 f"{ref.location}." if ref.location else "",
                 f"**Anais** [...]."]
        if ref.publisher:
            parts.append(f"{ref.publisher},")
        if ref.year:
            parts.append(f"{ref.year}.")
        if ref.pages:
            parts.append(f"p. {ref.pages}.")
        if end:
            parts.append(end)
        return " ".join(p for p in parts if p)

    if ref.type == "electronic" or ref.type == "website":
        # SILVA, J. P. Título do documento. [Local], ano. Disponível em: URL. Acesso em: data.
        parts = [authors + ".", f"**{ref.title}**."]
        if ref.location:
            parts.append(f"{ref.location},")
        if ref.year:
            parts.append(f"{ref.year}.")
        if end:
            parts.append(end)
        return " ".join(parts)

    if ref.type == "legislation":
        # BRASIL. Lei nº ..., de DD de mês de ANO. Ementa. Diário Oficial...
        return f"{ref.title}. {ref.venue or ''}, {ref.year or ''}. {end}".strip()

    if ref.type == "av_resource":
        # TÍTULO. Direção: ... Cidade: Produtora, ano. Suporte (duração).
        return f"**{ref.title}**. {authors}. {ref.location or ''}: {ref.publisher or ''}, {ref.year or ''}. {end}".strip()

    # fallback
    return f"{authors}. {ref.title}. {ref.venue or ''}, {ref.year or ''}. {end}".strip()


def format_inline_citation(authors: list[str], year: int | None,
                           page: str | None = None,
                           direct_quote: bool = False) -> str:
    """Formata citação no corpo do texto conforme NBR 10520:2023.

    Padrão autor-data:
    - 1 autor: (SILVA, 2023) ou (SILVA, 2023, p. 45) para citação direta.
    - 2 autores: (SILVA; PEREIRA, 2023).
    - 3 autores: (SILVA; PEREIRA; LIMA, 2023).
    - 4+ autores: (SILVA et al., 2023).
    """
    if not authors:
        sn = "[s.a.]"
    elif len(authors) == 1:
        sn = _last_name_uppercase(authors[0])
    elif len(authors) == 2:
        sn = f"{_last_name_uppercase(authors[0])}; {_last_name_uppercase(authors[1])}"
    elif len(authors) == 3:
        sn = "; ".join(_last_name_uppercase(a) for a in authors[:3])
    else:
        sn = f"{_last_name_uppercase(authors[0])} et al."
    year_str = str(year) if year else "[s.d.]"
    if direct_quote and page:
        return f"({sn}, {year_str}, p. {page})"
    return f"({sn}, {year_str})"


def _last_name_uppercase(author: str) -> str:
    a = author.strip()
    if "," in a:
        return a.split(",", 1)[0].strip().upper()
    if " " in a:
        return a.rsplit(" ", 1)[1].strip().upper()
    return a.upper()


def format_long_quote(quote_text: str, citation: str) -> str:
    """Citação direta longa (≥ 4 linhas) — NBR 10520:2023 §6.1.

    Recuo de 4cm da margem esquerda, fonte 10pt, espaçamento simples, sem aspas.
    Renderização markdown: usar blockquote prefix '> ' como aproximação.
    """
    quoted_lines = "\n".join(f"> {ln}" for ln in quote_text.strip().split("\n"))
    return f"{quoted_lines}\n>\n> {citation}"


def format_apud(original_authors: list[str], original_year: int,
                citing_authors: list[str], citing_year: int,
                page: str | None = None) -> str:
    """Citação apud (citação de citação) — NBR 10520:2023 §6.4.

    Formato: (ORIGINAL, ano apud CITANTE, ano, p. X)
    """
    o = _last_name_uppercase(original_authors[0]) if original_authors else "[s.a.]"
    c = _last_name_uppercase(citing_authors[0]) if citing_authors else "[s.a.]"
    page_part = f", p. {page}" if page else ""
    return f"({o}, {original_year} apud {c}, {citing_year}{page_part})"


def format_bibliography(refs: list[Reference]) -> str:
    """Renderiza a seção §Referências em ABNT, ordem alfabética por autor."""
    sorted_refs = sorted(refs, key=lambda r: (
        (r.authors[0] if r.authors else "").upper(),
        r.year or 9999,
    ))
    return "\n\n".join(format_reference_abnt(r) for r in sorted_refs)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Formatador ABNT NBR 6023:2018 + NBR 10520:2023.")
    p.add_argument("--input-json", required=True,
                   help="JSON com lista de referências no formato Reference.")
    p.add_argument("--output", required=True)
    p.add_argument("--format", choices=["bibliography", "single"], default="bibliography")
    args = p.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    refs = [Reference(**d) for d in (data if isinstance(data, list) else [data])]

    if args.format == "bibliography":
        out = format_bibliography(refs)
    else:
        out = format_reference_abnt(refs[0]) if refs else ""

    Path(args.output).write_text(out, encoding="utf-8")
    print(f"[format_abnt] {len(refs)} referências formatadas → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
