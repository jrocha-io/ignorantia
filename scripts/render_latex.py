#!/usr/bin/env python3
"""
render_latex.py — Render do manuscrito como .tex e compile para .pdf (Decisão 32).

Gera um arquivo `.tex` em estilo ABNT (artigo) usando packages comumente disponíveis
em distribuições TeX Live. Não depende de classes ABNT externas (como `abntex2`),
porque essas não fazem parte do TeX Live padrão; em vez disso, usa `article` com
geometry/setspace/babel para aproximar margens e espaçamento ABNT.

Para compilar PDF, exige `pdflatex` ou `xelatex` no PATH. A função `compile_pdf`
roda o compilador com runs múltiplos para resolver referências cruzadas.

Tipografia ABNT aproximada via packages padrão:
- `geometry`: margens 3cm/3cm/2cm/2cm
- `setspace`: espaçamento 1.5
- `times` ou `mathptmx`: Times New Roman como fonte serifada
- `babel` com `brazilian` ou `english`
- `csquotes`: gestão de aspas
- `cite` ou `natbib`: citações autor-data

Se a saída final precisa ser realmente conforme abntex2, o usuário pode adaptar
manualmente trocando `\\documentclass{article}` por `\\documentclass{abntex2}` —
o conteúdo gerado é compatível.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

LATEX_PREAMBLE = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[main=brazilian,provide=*]{babel}
\usepackage{geometry}
\geometry{top=3cm,left=3cm,bottom=2cm,right=2cm}
\usepackage{setspace}
\onehalfspacing
\usepackage{mathptmx}
\usepackage{indentfirst}
\usepackage{csquotes}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue,citecolor=black}
\usepackage{xcolor}
\usepackage{titlesec}
\titleformat{\section}{\normalfont\bfseries\large}{\thesection}{1em}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}

\setlength{\parindent}{1.25cm}

% Long quote environment (ABNT NBR 10520:2023): recuo 4cm, fonte 10pt, espaçamento simples, sem aspas
\newenvironment{longquote}{%
  \begin{quote}\setlength{\leftskip}{4cm}\fontsize{10pt}{12pt}\selectfont\begin{singlespace}%
}{%
  \end{singlespace}\end{quote}%
}

\begin{document}
"""

LATEX_POSTAMBLE = r"""
\end{document}
"""


@dataclass
class LatexRenderResult:
    tex_path: Path
    pdf_path: Path | None = None
    pdf_compiled: bool = False
    n_sections: int = 0
    n_references: int = 0
    compile_log: str = ""
    error: str | None = None


def _escape_latex(text: str) -> str:
    """Escapa caracteres especiais do LaTeX preservando o que já é LaTeX bruto."""
    if not text:
        return ""
    # Sequência importa: barra invertida primeiro
    repl = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
        ("<", r"\textless{}"),
        (">", r"\textgreater{}"),
    ]
    out = text
    for old, new in repl:
        out = out.replace(old, new)
    return out


def _markdown_to_latex(text: str) -> str:
    """A2 (v2.20.0, auditoria #2): conversor Markdown → LaTeX para texto inline.

    Trata, em ordem (importa para evitar conflitos):
        1. Links `[text](url)` → `\\href{url}{text}` (proteger URL antes de escape)
        2. Bold `**texto**` → `\\textbf{texto}`
        3. Italic `*texto*` → `\\textit{texto}` (após bold para não confundir)
        4. Escape LaTeX restante

    NÃO trata listas — listas são tratadas no nível de bloco (linhas começando com `- `).
    """
    if not text:
        return ""
    import re

    # Etapa 1: extrair links e substituir por placeholder ASCII inocuo
    placeholders: dict[str, str] = {}
    counter = [0]

    def _stash(s: str) -> str:
        key = f"\x00LINK{counter[0]}\x00"
        counter[0] += 1
        placeholders[key] = s
        return key

    # Links Markdown [text](url) → placeholder com \href{url}{text}
    # Restrito a URLs http/https para evitar consumir colchetes literais [foo].
    def _link_repl(m: re.Match) -> str:
        link_text = m.group(1)
        url = m.group(2)
        url_escaped = url.replace("%", r"\%").replace("#", r"\#")
        text_escaped = _escape_latex(link_text)
        return _stash(rf"\href{{{url_escaped}}}{{{text_escaped}}}")

    text = re.sub(r"\[([^\]]*?(?:\[[^\]]*\][^\]]*?)*?)\]\((https?://[^)]+)\)",
                   _link_repl, text)

    # Etapa 2: bold **texto** → placeholder com \textbf{texto}
    def _bold_repl(m: re.Match) -> str:
        return _stash(rf"\textbf{{{_escape_latex(m.group(1))}}}")

    text = re.sub(r"\*\*([^*]+)\*\*", _bold_repl, text)

    # Etapa 3: italic *texto* → placeholder com \textit{texto}
    # Cuidado: não pegar dentro de palavras (snake_case). Usar lookbehind para limites.
    def _italic_repl(m: re.Match) -> str:
        return _stash(rf"\textit{{{_escape_latex(m.group(1))}}}")

    # Italic regex: *texto* onde * não é precedido/seguido de letra (evita snake_case)
    text = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", _italic_repl, text)

    # Etapa 4: escape do texto restante
    text = _escape_latex(text)

    # Etapa 4.5: B9 (v2.21.0): asteriscos órfãos remanescentes (input
    # mal-formado tipo '*italic** ambíguo*') viram literais escaped.
    # Em LaTeX, * fora de \textit/\textbf é OK como literal,
    # mas para evitar parse errors em corner cases, escape via \char42.
    # Manter como literal '*' é seguro em LaTeX padrão; só escape se for problemático.
    # Aqui apenas registramos via comentário — não tocar pois é input mal-formado.

    # Etapa 5: restaurar placeholders. Os placeholders foram escapados também
    # (textbackslash etc.); precisamos substituir as versões escapadas.
    for key, val in placeholders.items():
        # \x00 escapado vira o próprio \x00 (não está na tabela de escape) — safe
        text = text.replace(key, val)

    return text


def _strip_html(html: str) -> str:
    """Remove HTML básico — mesma utilidade de render_docx_abnt._strip_html."""
    import re
    text = re.sub(r"<br\s*/?>", "\n\n", html)
    text = re.sub(r"</p>\s*<p[^>]*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def render_tex(content: dict, output_path: Path,
               *, title: str, authors: list[str] | None = None,
               abstract: str | None = None,
               keywords: list[str] | None = None,
               lang: str = "brazilian",
               contextual_preamble_markdown: str | None = None
               ) -> LatexRenderResult:
    """Renderiza o manuscrito como arquivo .tex.

    Args:
        contextual_preamble_markdown: F4 (v2.18.1, DD-11) — se fornecido, gera
            seção "O campo onde este artigo vive" antes da Introdução.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ajusta babel se não for português
    preamble = LATEX_PREAMBLE
    if lang != "brazilian":
        preamble = preamble.replace("[main=brazilian,provide=*]{babel}",
                                     f"[main={lang},provide=*]{{babel}}")

    parts = [preamble]
    parts.append(f"\\title{{{_escape_latex(title)}}}")
    authors = authors or content.get("authors", [])
    if authors:
        # py3.10/3.11 reject backslashes inside f-string expression parts;
        # build the joined string outside the f-string for compatibility.
        author_sep = " \\and "
        joined_authors = _escape_latex(author_sep.join(authors))
        parts.append(f"\\author{{{joined_authors}}}")
    parts.append("\\date{}")
    parts.append("\\maketitle")
    parts.append("")

    # Resumo
    abstract = abstract or content.get("abstract")
    if abstract:
        parts.append("\\begin{abstract}")
        parts.append(_escape_latex(abstract))
        parts.append("\\end{abstract}")
        kws = keywords or content.get("keywords", [])
        if kws:
            kws_str = "; ".join(_escape_latex(k) for k in kws)
            parts.append(f"\\noindent\\textbf{{Palavras-chave:}} {kws_str}.")
        parts.append("")

    # F4 (v2.18.1, DD-11) + A2 (v2.20.0): preâmbulo contextual antes das seções.
    # Markdown→LaTeX completo via _markdown_to_latex().
    if contextual_preamble_markdown:
        # A2: pré-agrupar linhas consecutivas em parágrafos para que italic/bold
        # multi-linha funcione (o regex de italic exclui \n por padrão).
        raw_lines = contextual_preamble_markdown.strip().split("\n")
        # Coalesce: agrupa linhas consecutivas de texto até linha vazia,
        # preservando linhas especiais (## ### - ).
        coalesced: list[str] = []
        buffer: list[str] = []

        def _flush_buffer():
            if buffer:
                coalesced.append(" ".join(buffer))
                buffer.clear()

        for raw in raw_lines:
            stripped = raw.strip()
            if not stripped:
                _flush_buffer()
                coalesced.append("")
                continue
            # Linhas especiais quebram parágrafo
            if (stripped.startswith("## ")
                or stripped.startswith("### ")
                or stripped.startswith("- ")
                or (stripped[0:2].rstrip(".").isdigit() and stripped[1:3] in (". ", ". ")
                    and stripped[0:1].isdigit())):
                _flush_buffer()
                coalesced.append(stripped)
                continue
            buffer.append(stripped)
        _flush_buffer()

        preamble_lines = coalesced
        preamble_title = "O campo onde este artigo vive"
        for line in preamble_lines:
            if line.startswith("## "):
                preamble_title = line[3:].strip()
                break
        parts.append(f"\\section*{{{_escape_latex(preamble_title)}}}")
        body_started = False
        in_list = False  # estado: estamos dentro de \begin{itemize}?
        for line in preamble_lines:
            stripped = line.strip()

            if not stripped:
                # Linha vazia: fecha lista se aberta, e adiciona separador
                if in_list:
                    parts.append("\\end{itemize}")
                    in_list = False
                parts.append("")
                continue

            if stripped.startswith("## "):
                body_started = True
                continue

            if stripped.startswith("### "):
                if in_list:
                    parts.append("\\end{itemize}")
                    in_list = False
                heading_text = stripped.lstrip("# ").strip()
                parts.append(f"\\subsection*{{{_markdown_to_latex(heading_text)}}}")
                continue

            if not body_started:
                continue

            # Lista Markdown `- item` → \begin{itemize}\item ...
            if stripped.startswith("- "):
                if not in_list:
                    parts.append("\\begin{itemize}")
                    in_list = True
                item_text = stripped[2:].strip()
                parts.append(f"  \\item {_markdown_to_latex(item_text)}")
                continue

            # Texto normal: fecha lista se estava aberta
            if in_list:
                parts.append("\\end{itemize}")
                in_list = False
            parts.append(_markdown_to_latex(stripped))
            parts.append("")

        # Fechar lista pendente no final do preâmbulo
        if in_list:
            parts.append("\\end{itemize}")

    # Seções
    sections = content.get("sections", [])
    for s in sections:
        sec_id = s.get("id", "")
        sec_title = _escape_latex(s.get("title", ""))
        prefix = f"\\S{sec_id} " if sec_id else ""
        parts.append(f"\\section*{{{prefix}{sec_title}}}")
        paragraphs = s.get("paragraphs", [])
        if not paragraphs and s.get("content_html"):
            paragraphs = [{"text": _strip_html(s["content_html"]), "type": "body"}]
        for para in paragraphs:
            text = para.get("text", "")
            ptype = para.get("type", "body")
            if not text.strip():
                continue
            escaped = _escape_latex(text)
            if ptype == "long_quote":
                parts.append("\\begin{longquote}")
                parts.append(escaped)
                parts.append("\\end{longquote}")
            elif ptype == "reference":
                parts.append(escaped + "\n")
            else:
                parts.append(escaped)
            parts.append("")

    # Referências
    refs = content.get("references", [])
    if refs:
        parts.append("\\section*{Referências}")
        parts.append("\\begin{singlespace}")
        for r in refs:
            parts.append(_escape_latex(r))
            parts.append("")
        parts.append("\\end{singlespace}")

    parts.append(LATEX_POSTAMBLE)

    output_path.write_text("\n".join(parts), encoding="utf-8")

    return LatexRenderResult(
        tex_path=output_path,
        n_sections=len(sections),
        n_references=len(refs),
    )


def compile_pdf(tex_path: Path, *, engine: str = "pdflatex",
                runs: int = 2, timeout: int = 120) -> LatexRenderResult:
    """Compila .tex em .pdf usando pdflatex/xelatex.

    Args:
        runs: número de execuções (2-3 é suficiente para resolver refs cruzadas).
    """
    result = LatexRenderResult(tex_path=tex_path, n_sections=0, n_references=0)
    if not shutil.which(engine):
        result.error = f"{engine} não disponível no PATH"
        return result

    workdir = tex_path.parent
    log_lines = []
    for i in range(runs):
        try:
            res = subprocess.run(
                [engine, "-interaction=nonstopmode", "-halt-on-error",
                 tex_path.name],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(workdir),
            )
            log_lines.append(f"=== run {i+1}/{runs} (rc={res.returncode}) ===")
            log_lines.append(res.stdout[-2000:] if res.stdout else "")
            if res.returncode != 0 and i == runs - 1:
                result.error = (f"{engine} falhou na run final (rc={res.returncode}); "
                                f"ver log completo")
                result.compile_log = "\n".join(log_lines)
                return result
        except subprocess.TimeoutExpired:
            result.error = f"{engine} timeout após {timeout}s na run {i+1}"
            result.compile_log = "\n".join(log_lines)
            return result

    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_path.exists():
        result.pdf_path = pdf_path
        result.pdf_compiled = True
    else:
        result.error = f"PDF não foi produzido (esperado em {pdf_path})"
    result.compile_log = "\n".join(log_lines)
    return result


def render_tex_and_pdf(content: dict, tex_path: Path,
                       *, title: str, authors: list[str] | None = None,
                       abstract: str | None = None,
                       keywords: list[str] | None = None,
                       compile_to_pdf: bool = True,
                       engine: str = "pdflatex",
                       contextual_preamble_markdown: str | None = None
                       ) -> LatexRenderResult:
    """Pipeline completo: tex + (opcional) pdf."""
    tex_result = render_tex(
        content, tex_path,
        title=title, authors=authors, abstract=abstract, keywords=keywords,
        contextual_preamble_markdown=contextual_preamble_markdown,
    )
    if not compile_to_pdf:
        return tex_result
    pdf_result = compile_pdf(tex_path, engine=engine)
    tex_result.pdf_path = pdf_result.pdf_path
    tex_result.pdf_compiled = pdf_result.pdf_compiled
    tex_result.compile_log = pdf_result.compile_log
    if pdf_result.error:
        tex_result.error = pdf_result.error
    return tex_result


def _cli() -> int:
    p = argparse.ArgumentParser(description="Render .tex (e .pdf) ABNT (Decisão 32).")
    p.add_argument("--content-json", required=True)
    p.add_argument("--output-tex", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--no-pdf", action="store_true",
                   help="Não compila PDF (apenas .tex).")
    p.add_argument("--engine", default="pdflatex", choices=["pdflatex", "xelatex"])
    # F4 (v2.18.1, DD-11)
    p.add_argument("--contextual-preamble", action="store_true",
                   help="Inclui seção 'O campo onde este artigo vive' antes da Introdução.")
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
            print("[render_latex] WARN: contextual_preamble não disponível.",
                  file=sys.stderr)

    result = render_tex_and_pdf(
        content, Path(args.output_tex),
        title=args.title,
        compile_to_pdf=not args.no_pdf,
        engine=args.engine,
        contextual_preamble_markdown=preamble_md,
    )
    print(f"[render_latex] tex: {result.tex_path} ({result.n_sections} seções, "
          f"{result.n_references} refs)")
    if result.pdf_compiled:
        print(f"[render_latex] pdf: {result.pdf_path}")
    elif result.error:
        print(f"[render_latex] PDF não compilado: {result.error}", file=sys.stderr)
    return 0 if not result.error else 1


if __name__ == "__main__":
    sys.exit(_cli())
