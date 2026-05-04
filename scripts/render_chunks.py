#!/usr/bin/env python3
"""
render_chunks.py — Renderização do manuscrito HTML em chunks/append (Decisão 18).

A renderização anterior (`render_v2.py`, `render_manuscript.py`) faz uma única passada
com substituição de placeholders {{TITLE}}, {{SECTIONS_HTML}}, etc. Falha em qualquer
seção invalidava todo o trabalho, e debug ficava difícil porque o HTML só existe ao
final.

Esta v2.10.0 introduz renderização incremental:

1. Inicia o HTML com o boilerplate (head, topbar, abertura do <main>).
2. Renderiza cada seção em chunk independente (§00, §01, ..., §N) e faz append.
3. Cada chunk é gravado em arquivo intermediário (`<output>.chunk-NN.html`) para
   permitir checkpoint/recovery.
4. Após todas as seções, fecha o HTML (footer + scripts).
5. Se uma seção falha, o usuário pode reprocessar só aquela seção sem perder as
   demais (`--resume-from-chunk N`).

Modelo de chunk:

    section_id    : "01"  (mapeia para §01 — Introdução)
    section_title : "Introdução"
    content_html  : "<p>...</p>" (gerado pelo LLM ou montado a partir de templates)
    annotations   : [{anchor, text}, ...]  (camada lateral)
    deps          : ["00"]  (chunks que precisam estar prontos antes — seções anteriores)

A primeira seção (§00) tem `deps: []` e contém o resumo executivo + abstract; pode
ser revisitada após as demais (re-render do §00 com base no conteúdo agregado).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_HEAD = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{title} — v{version}</title>
<meta name="generator" content="algoritmo particular do autor + Claude (Anthropic)">
<style>{css}</style>
</head>
<body>
<header class="topbar"><div class="brand">{title_short} <span class="brand-version">v{version}</span></div></header>
<main id="manuscript" role="main">
"""

DEFAULT_TAIL = """
</main>
<footer><p>v{version} · <code>SHA-256: {hash}</code> · {license} · {date_iso}</p></footer>
</body>
</html>
"""

MINIMAL_CSS = """body{font-family:Georgia,serif;max-width:760px;margin:2em auto;padding:0 1em;line-height:1.6}
.topbar{position:sticky;top:0;background:#fff;border-bottom:1px solid #ccc;padding:0.5em 0;margin-bottom:1em}
.brand{font-weight:700}.brand-version{color:#888;font-weight:normal;margin-left:0.5em}
section.chunk{margin:2em 0;padding-top:1em;border-top:1px solid #eee}
section.chunk h2{font-size:1.4em}
.annotations{font-style:italic;color:#666;border-left:3px solid #ccc;padding-left:1em;margin:1em 0}
footer{margin-top:3em;padding-top:1em;border-top:1px solid #ccc;font-size:0.9em;color:#666}
"""


@dataclass
class Chunk:
    """Um chunk corresponde a uma seção do manuscrito."""
    section_id: str  # "00", "01", ...
    section_title: str
    content_html: str = ""
    annotations: list[dict] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)
    rendered: bool = False
    rendered_html: str = ""


@dataclass
class ChunkRenderResult:
    output_path: Path
    chunks_processed: list[str] = field(default_factory=list)
    chunks_skipped: list[str] = field(default_factory=list)
    intermediate_dir: Path | None = None
    final_size_bytes: int = 0


def render_chunk_to_html(chunk: Chunk) -> str:
    """Renderiza um chunk individual em HTML."""
    annotations_html = ""
    if chunk.annotations:
        items = "".join(
            f'<li><strong>{ann.get("anchor", "?")}:</strong> {ann.get("text", "")}</li>'
            for ann in chunk.annotations
        )
        annotations_html = f'<aside class="annotations"><ul>{items}</ul></aside>'
    return (
        f'<section id="sec-{chunk.section_id}" class="chunk" '
        f'data-section-id="{chunk.section_id}">'
        f'<h2>§{chunk.section_id} — {chunk.section_title}</h2>'
        f'{chunk.content_html}'
        f'{annotations_html}'
        f'</section>\n'
    )


def render_incremental(chunks: list[Chunk], output_path: Path,
                       *,
                       title: str, title_short: str, version: str,
                       lang: str = "pt-BR", license_str: str = "CC-BY-4.0",
                       date_iso: str = "2026-05-03", file_hash: str = "—",
                       intermediate_dir: Path | None = None,
                       resume_from_chunk: str | None = None,
                       css: str = MINIMAL_CSS,
                       contextual_preamble_html: str | None = None
                       ) -> ChunkRenderResult:
    """Renderiza chunks em modo incremental (append).

    Args:
        chunks: lista ordenada (por section_id) de chunks já preenchidos.
        output_path: caminho do HTML final consolidado.
        intermediate_dir: se fornecido, grava cada chunk em arquivo separado para checkpoint.
        resume_from_chunk: se fornecido, pula chunks anteriores (eles devem estar em
            intermediate_dir como `chunk-NN.html` já gerados em execução prévia).
        contextual_preamble_html: B2 (v2.21.0, DD-11) — se fornecido, injeta o bloco
            HTML do preâmbulo contextual antes da Introdução, distinto da Introdução.
            Formato esperado: `<section id="contextual-preamble">...</section>`.
    """
    result = ChunkRenderResult(output_path=output_path,
                               intermediate_dir=intermediate_dir)
    if intermediate_dir:
        intermediate_dir.mkdir(parents=True, exist_ok=True)

    # Ordena por section_id
    sorted_chunks = sorted(chunks, key=lambda c: c.section_id)

    # Decide quais processar
    skip_until = resume_from_chunk

    # Renderização incremental — escreve em arquivo aberto em modo append
    output_path.parent.mkdir(parents=True, exist_ok=True)
    head_text = DEFAULT_HEAD.format(
        lang=lang, title=title, title_short=title_short,
        version=version, css=css,
    )
    output_path.write_text(head_text, encoding="utf-8")

    # B2 (v2.21.0): Preâmbulo contextual ANTES dos chunks (introdução).
    # Se preâmbulo presente, escreve antes do primeiro chunk.
    if contextual_preamble_html:
        with output_path.open("a", encoding="utf-8") as f:
            f.write(contextual_preamble_html)
            f.write("\n")

    # Para cada chunk: render → append ao arquivo final E grava em intermediate_dir
    for chunk in sorted_chunks:
        if skip_until and chunk.section_id < skip_until:
            # Procura chunk pré-renderizado em intermediate_dir
            cached_path = (intermediate_dir / f"chunk-{chunk.section_id}.html"
                           if intermediate_dir else None)
            if cached_path and cached_path.exists():
                cached_html = cached_path.read_text(encoding="utf-8")
                with output_path.open("a", encoding="utf-8") as f:
                    f.write(cached_html)
                chunk.rendered = True
                chunk.rendered_html = cached_html
                result.chunks_skipped.append(chunk.section_id)
                continue
            # Sem cache, processa mesmo assim
        rendered_html = render_chunk_to_html(chunk)
        chunk.rendered_html = rendered_html
        chunk.rendered = True
        with output_path.open("a", encoding="utf-8") as f:
            f.write(rendered_html)
        if intermediate_dir:
            (intermediate_dir / f"chunk-{chunk.section_id}.html").write_text(
                rendered_html, encoding="utf-8"
            )
        result.chunks_processed.append(chunk.section_id)

    # Tail
    tail_text = DEFAULT_TAIL.format(
        version=version, hash=file_hash, license=license_str, date_iso=date_iso,
    )
    with output_path.open("a", encoding="utf-8") as f:
        f.write(tail_text)

    result.final_size_bytes = output_path.stat().st_size
    return result


def chunks_from_content_json(content: dict) -> list[Chunk]:
    """Extrai chunks de um content.json no formato esperado pelo skill.

    Espera estrutura:
        {
          "sections": [
            {"id": "00", "title": "Resumo", "content_html": "...", "annotations": [...]},
            ...
          ]
        }
    """
    out = []
    for s in content.get("sections", []):
        out.append(Chunk(
            section_id=str(s.get("id", "")).zfill(2),
            section_title=s.get("title", ""),
            content_html=s.get("content_html", ""),
            annotations=s.get("annotations", []),
            deps=s.get("deps", []),
        ))
    return out


def _cli() -> int:
    p = argparse.ArgumentParser(description="Render incremental do manuscrito (Decisão 18).")
    p.add_argument("--content-json", required=True,
                   help="Caminho para content.json com sections[].")
    p.add_argument("--output", required=True, help="Caminho do HTML final.")
    p.add_argument("--intermediate-dir", default=None,
                   help="Diretório para chunks intermediários (checkpoint/recovery).")
    p.add_argument("--resume-from-chunk", default=None,
                   help="ID do chunk a partir do qual processar (anteriores lidos do intermediate-dir).")
    p.add_argument("--title", required=True)
    p.add_argument("--title-short", default=None)
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--lang", default="pt-BR")
    p.add_argument("--date-iso", default="2026-05-03")
    p.add_argument("--license", dest="license_str", default="CC-BY-4.0")
    p.add_argument("--hash", dest="file_hash", default="—")
    args = p.parse_args()

    content = json.loads(Path(args.content_json).read_text(encoding="utf-8"))
    chunks = chunks_from_content_json(content)
    result = render_incremental(
        chunks, Path(args.output),
        title=args.title,
        title_short=args.title_short or args.title,
        version=args.version, lang=args.lang,
        date_iso=args.date_iso, license_str=args.license_str,
        file_hash=args.file_hash,
        intermediate_dir=Path(args.intermediate_dir) if args.intermediate_dir else None,
        resume_from_chunk=args.resume_from_chunk,
    )
    print(f"[render_chunks] {len(result.chunks_processed)} chunks renderizados, "
          f"{len(result.chunks_skipped)} pulados (cache); "
          f"final {result.final_size_bytes} bytes → {result.output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
