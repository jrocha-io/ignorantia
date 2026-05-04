#!/usr/bin/env python3
"""
cross_tabulation.py — Gerador de tabelas cross-tabulação na síntese.

Decisão 29 (v2.9.0): tabela cross-tabulação é OBRIGATÓRIA na síntese da Fase 6.
Para revisões em CS/SE: dimensões típicas são modelo × tarefa × métrica. Para saúde:
população × intervenção × desfecho. Para educação: nível × abordagem × resultado.

A tabela cross-tabulação é o instrumento mais elementar de síntese estruturada.
A v2.8.0 anterior tinha-a como "polimento" (opcional). A v2.9.0 eleva à obrigação:
sem tabela cross-tab gerada e referenciada na §05, a rubrica D4 perde 0.5 pontos.

Este módulo:
1. Recebe `extraction.csv` (uma linha por estudo incluído, com colunas extraídas).
2. Recebe especificação das 3 dimensões a cruzar (configurável por área).
3. Emite tabela markdown com contagens; valores ausentes como "—" (não "N/A").
4. Emite versão em HTML para inclusão direta no manuscrito.
5. Gera resumo em prosa: "X estudos cobrem A∩B; Y cobrem apenas A; Z cobrem apenas B."
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CrossTabResult:
    dim_x: str
    dim_y: str
    dim_z: str | None  # opcional: terceira dimensão para tabelas estratificadas
    counts: dict[tuple[str, ...], int] = field(default_factory=dict)
    x_values: list[str] = field(default_factory=list)
    y_values: list[str] = field(default_factory=list)
    z_values: list[str] = field(default_factory=list)
    n_studies: int = 0
    n_with_all_dims: int = 0  # estudos com todas as dimensões preenchidas
    markdown: str = ""
    html: str = ""
    prose_summary: str = ""


def _load_extraction(path: Path) -> list[dict]:
    """Lê extraction.csv (UTF-8, separador vírgula ou ponto-e-vírgula)."""
    text = path.read_text(encoding="utf-8")
    sample = text[:2048]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return list(reader)


def _split_multi_value(cell: str | None) -> list[str]:
    """Algumas colunas (ex.: 'tasks') trazem múltiplos valores por estudo, separados por ; ou |."""
    if not cell:
        return []
    s = str(cell).strip()
    if not s or s in ("—", "-", "N/A", "n/a", "nan"):
        return []
    for sep in ["|", ";"]:
        if sep in s:
            return [v.strip() for v in s.split(sep) if v.strip()]
    return [s]


def cross_tabulate(extraction: list[dict], dim_x: str, dim_y: str,
                   dim_z: str | None = None) -> CrossTabResult:
    """Constrói cross-tabulação 2D ou 3D sobre lista de dicts (uma linha por estudo)."""
    counts: Counter[tuple[str, ...]] = Counter()
    x_seen, y_seen, z_seen = set(), set(), set()
    n_complete = 0
    for row in extraction:
        xs = _split_multi_value(row.get(dim_x))
        ys = _split_multi_value(row.get(dim_y))
        zs = _split_multi_value(row.get(dim_z)) if dim_z else [None]
        if xs and ys and (zs or not dim_z):
            n_complete += 1
        for x in xs:
            x_seen.add(x)
            for y in ys:
                y_seen.add(y)
                for z in zs:
                    if z is not None:
                        z_seen.add(z)
                        counts[(x, y, z)] += 1
                    else:
                        counts[(x, y)] += 1

    result = CrossTabResult(
        dim_x=dim_x, dim_y=dim_y, dim_z=dim_z,
        counts=dict(counts),
        x_values=sorted(x_seen),
        y_values=sorted(y_seen),
        z_values=sorted(z_seen),
        n_studies=len(extraction),
        n_with_all_dims=n_complete,
    )
    result.markdown = _render_markdown(result)
    result.html = _render_html(result)
    result.prose_summary = _render_prose_summary(result)
    return result


def _render_markdown(r: CrossTabResult) -> str:
    """Renderiza a tabela em markdown. Para 3D, gera múltiplas tabelas estratificadas."""
    if not r.dim_z:
        # 2D: linhas = X, colunas = Y
        header = f"| {r.dim_x} \\ {r.dim_y} | " + " | ".join(r.y_values) + " | **Total** |"
        sep = "|---" * (len(r.y_values) + 2) + "|"
        lines = [f"### Cross-tabulação: {r.dim_x} × {r.dim_y}", "",
                 f"_{r.n_with_all_dims} estudos com ambas as dimensões preenchidas (de {r.n_studies} totais)._",
                 "", header, sep]
        for x in r.x_values:
            row_total = sum(r.counts.get((x, y), 0) for y in r.y_values)
            cells = [str(r.counts.get((x, y), 0)) if r.counts.get((x, y), 0) else "—"
                     for y in r.y_values]
            lines.append(f"| **{x}** | " + " | ".join(cells) + f" | **{row_total}** |")
        col_totals = [sum(r.counts.get((x, y), 0) for x in r.x_values) for y in r.y_values]
        grand = sum(col_totals)
        lines.append(f"| **Total** | " + " | ".join(f"**{t}**" for t in col_totals) +
                     f" | **{grand}** |")
        return "\n".join(lines)
    # 3D: estratificar por Z
    out = [f"### Cross-tabulação estratificada: {r.dim_x} × {r.dim_y} × {r.dim_z}", ""]
    for z in r.z_values:
        out.append(f"#### Estrato: {r.dim_z} = {z}")
        out.append("")
        header = f"| {r.dim_x} \\ {r.dim_y} | " + " | ".join(r.y_values) + " | **Total** |"
        sep = "|---" * (len(r.y_values) + 2) + "|"
        out.extend([header, sep])
        for x in r.x_values:
            cells = [str(r.counts.get((x, y, z), 0)) if r.counts.get((x, y, z), 0) else "—"
                     for y in r.y_values]
            row_total = sum(r.counts.get((x, y, z), 0) for y in r.y_values)
            out.append(f"| **{x}** | " + " | ".join(cells) + f" | **{row_total}** |")
        out.append("")
    return "\n".join(out)


def _render_html(r: CrossTabResult) -> str:
    """Renderiza a tabela como HTML pronto para o manuscrito."""
    if not r.dim_z:
        header = "<th>" + f"{r.dim_x} \\ {r.dim_y}" + "</th>" + \
                 "".join(f"<th>{y}</th>" for y in r.y_values) + "<th><strong>Total</strong></th>"
        body_rows = []
        for x in r.x_values:
            row_total = sum(r.counts.get((x, y), 0) for y in r.y_values)
            cells = "".join(
                f"<td>{r.counts.get((x, y), 0) or '—'}</td>" for y in r.y_values
            )
            body_rows.append(f"<tr><th scope='row'>{x}</th>{cells}<td><strong>{row_total}</strong></td></tr>")
        col_totals = [sum(r.counts.get((x, y), 0) for x in r.x_values) for y in r.y_values]
        grand = sum(col_totals)
        foot = "<tr><th scope='row'>Total</th>" + \
               "".join(f"<td><strong>{t}</strong></td>" for t in col_totals) + \
               f"<td><strong>{grand}</strong></td></tr>"
        return (f"<table class='cross-tab'><caption>Cross-tabulação: "
                f"{r.dim_x} × {r.dim_y} ({r.n_with_all_dims}/{r.n_studies} estudos)</caption>"
                f"<thead><tr>{header}</tr></thead>"
                f"<tbody>{''.join(body_rows)}{foot}</tbody></table>")
    # 3D: tabela única com hierarquia simples
    return f"<!-- 3D cross-tab; ver markdown estratificado -->{r.markdown}"


def _render_prose_summary(r: CrossTabResult) -> str:
    """Sumário em prosa para inserção na §05 da síntese."""
    if not r.counts:
        return (f"Nenhum estudo apresentou simultaneamente as dimensões "
                f"{r.dim_x} e {r.dim_y}{' e ' + r.dim_z if r.dim_z else ''}.")
    top3 = Counter(r.counts).most_common(3)
    bits = [
        f"Da extração ({r.n_with_all_dims} de {r.n_studies} estudos com dimensões "
        f"completas), a cross-tabulação revela que:",
    ]
    for combo, n in top3:
        if r.dim_z:
            x, y, z = combo
            bits.append(f"a combinação {r.dim_x}={x} ∩ {r.dim_y}={y} ∩ {r.dim_z}={z} "
                        f"é coberta por {n} estudo(s)")
        else:
            x, y = combo
            bits.append(f"a combinação {r.dim_x}={x} ∩ {r.dim_y}={y} "
                        f"é coberta por {n} estudo(s)")
    return "; ".join(bits) + "."


def _cli() -> int:
    p = argparse.ArgumentParser(description="Gerador de cross-tabulação obrigatório (Decisão 29).")
    p.add_argument("--extraction-csv", required=True,
                   help="Caminho para extraction.csv (uma linha por estudo).")
    p.add_argument("--dim-x", required=True, help="Nome da coluna para o eixo X.")
    p.add_argument("--dim-y", required=True, help="Nome da coluna para o eixo Y.")
    p.add_argument("--dim-z", default=None, help="Coluna opcional para estratificação Z.")
    p.add_argument("--output-md", required=True)
    p.add_argument("--output-html", default=None)
    p.add_argument("--output-prose", default=None)
    args = p.parse_args()

    extraction = _load_extraction(Path(args.extraction_csv))
    result = cross_tabulate(extraction, args.dim_x, args.dim_y, args.dim_z)

    Path(args.output_md).write_text(result.markdown, encoding="utf-8")
    if args.output_html:
        Path(args.output_html).write_text(result.html, encoding="utf-8")
    if args.output_prose:
        Path(args.output_prose).write_text(result.prose_summary, encoding="utf-8")

    print(f"[cross_tab] {result.n_with_all_dims}/{result.n_studies} estudos cruzados, "
          f"{len(result.counts)} células preenchidas → {args.output_md}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
