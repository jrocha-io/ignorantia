#!/usr/bin/env python3
"""
access_gap_report.py — Relatório de gap de acesso (v2.7.0).

Após Tier 0 resolver os DOIs encontrados em Tier 1-3 contra Unpaywall + OAB,
sobram itens cujo full-text NÃO está disponível por nenhuma fonte OA. Esses
itens são listados em um relatório .md entregue ao usuário.

Princípio operacional (Decisão 17 atualizada em v2.7.0):
- O skill NÃO decide sobre como o usuário obterá esses itens.
- O skill NÃO recomenda nem proíbe nenhuma plataforma específica.
- O skill APENAS lista o gap e oferece um ponto de pausa, durante o qual o
  usuário pode adicionar material ao diretório de inputs do projeto.
- O usuário tem soberania completa sobre como resolve o gap (acesso institucional,
  empréstimo bibliotecário, plataformas alternativas, compra direta, contato com autor,
  ou exclusão do item da revisão com declaração no PRISMA flow diagram).

Estrutura do relatório:

    # Lista de itens com acesso pendente — <projeto>

    Os <N> itens abaixo foram identificados nas buscas Tier 1-3 mas seu full-text
    não pôde ser resolvido por fontes OA legítimas (Tier 0). Para concluir a
    revisão, providencie o full-text dos itens necessários e adicione-os ao
    diretório `<input_dir>` antes de prosseguir.

    Como o usuário obtém os itens é decisão do usuário.

    ## Artigos paywalled (N=<n>)
    | DOI | Título | Periódico | Ano | Status Tier 0 |
    |---|---|---|---|---|
    | ... | ... | ... | ... | ... |

    ## Livros e capítulos a comprar/emprestar (N=<n>)
    | ISBN/ID | Título | Editora | Ano | Notas |

    ## Outros itens inacessíveis (N=<n>)
    | Identificador | Tipo | Descrição |

    ## Próximo passo
    1. Avalie se cada item é necessário para a pergunta de revisão.
    2. Para os itens necessários, providencie o full-text e coloque em `<input_dir>`.
    3. Itens não providenciados serão listados como "excluídos por inacessibilidade"
       no PRISMA flow diagram, com motivo declarado.
    4. Quando estiver pronto, retome a execução com `--resume-after-gap-report`.

Uso programático:
    from access_gap_report import generate_gap_report
    md = generate_gap_report(tier0_records, books=[], output_path="gap_report.md")

Uso CLI:
    python access_gap_report.py --tier0-json tier0_oa_enrichment.json \
                                 --output-dir search_results/ \
                                 --input-dir search_results/user_provided/
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GapItem:
    """Item com acesso pendente."""
    identifier: str  # DOI, ISBN, URL, ou identificador interno
    item_type: str   # "article" | "book" | "chapter" | "thesis" | "report" | "other"
    title: str | None = None
    journal_or_publisher: str | None = None
    year: int | None = None
    status_note: str | None = None  # ex.: "closed em Unpaywall", "OAB sem OA"
    request_url_for_author: str | None = None


@dataclass
class GapReport:
    n_items: int = 0
    n_articles: int = 0
    n_books: int = 0
    n_other: int = 0
    items: list[GapItem] = field(default_factory=list)
    project_id: str | None = None
    input_dir: str | None = None
    md_text: str = ""


def _classify_oa_status(record: dict[str, Any]) -> str:
    """Decide nota de status legível a partir de um registro Tier 0."""
    if record.get("oa_status") == "closed":
        return "Unpaywall: closed (sem OA registrado)"
    if record.get("error"):
        return f"erro: {record['error']}"
    if not record.get("has_legitimate_oa"):
        sources = record.get("sources_tried", [])
        return f"sem OA via {' → '.join(sources) if sources else 'Tier 0'}"
    return "OA disponível (não deveria estar no gap report)"


def collect_gap_from_tier0(tier0_payload: dict[str, Any]) -> list[GapItem]:
    """Extrai itens sem OA do payload Tier 0."""
    gap_items = []
    for rec in tier0_payload.get("records", []):
        if rec.get("has_legitimate_oa"):
            continue
        gap_items.append(GapItem(
            identifier=rec.get("doi", "?"),
            item_type="article",
            title=rec.get("title"),
            journal_or_publisher=rec.get("journal_name") or rec.get("publisher"),
            year=rec.get("year"),
            status_note=_classify_oa_status(rec),
            request_url_for_author=rec.get("request_url_for_author"),
        ))
    return gap_items


def render_md(items: list[GapItem], project_id: str = "(não nomeado)",
              input_dir: str = "search_results/user_provided/") -> str:
    """Renderiza relatório em markdown.

    Linguagem deliberadamente neutra: descreve o gap, não o que fazer com ele.
    """
    articles = [i for i in items if i.item_type == "article"]
    books = [i for i in items if i.item_type in ("book", "chapter")]
    others = [i for i in items if i.item_type not in ("article", "book", "chapter")]

    lines = [
        f"# Lista de itens com acesso pendente — {project_id}",
        "",
        f"Os **{len(items)} itens** abaixo foram identificados nas buscas Tier 1-3 mas seu "
        "full-text **não pôde ser resolvido por fontes OA legítimas** (Tier 0).",
        "",
        "Para concluir a revisão, providencie o full-text dos itens necessários e "
        f"adicione-os ao diretório `{input_dir}` antes de prosseguir.",
        "",
        "**Como o usuário obtém os itens é decisão do usuário.** O `ignorantia` não recomenda "
        "nem desaconselha nenhuma plataforma, serviço ou método de obtenção. A ferramenta apenas "
        "declara o gap.",
        "",
    ]

    if articles:
        lines.append(f"## Artigos paywalled ou sem OA disponível (N={len(articles)})")
        lines.append("")
        lines.append("| # | DOI | Título | Periódico/Editora | Ano | Status Tier 0 | Solicitar ao autor |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, item in enumerate(articles, 1):
            req_url = item.request_url_for_author or "—"
            req_link = f"[link]({req_url})" if req_url != "—" else "—"
            title = (item.title or "—")[:80]
            journal = (item.journal_or_publisher or "—")[:40]
            lines.append(
                f"| {i} | `{item.identifier}` | {title} | {journal} | "
                f"{item.year or '—'} | {item.status_note or '—'} | {req_link} |"
            )
        lines.append("")

    if books:
        lines.append(f"## Livros, capítulos e outras monografias (N={len(books)})")
        lines.append("")
        lines.append("| # | ISBN/ID | Título | Editora | Ano | Notas |")
        lines.append("|---|---|---|---|---|---|")
        for i, item in enumerate(books, 1):
            title = (item.title or "—")[:80]
            lines.append(
                f"| {i} | `{item.identifier}` | {title} | "
                f"{item.journal_or_publisher or '—'} | {item.year or '—'} | "
                f"{item.status_note or '—'} |"
            )
        lines.append("")

    if others:
        lines.append(f"## Outros itens inacessíveis (N={len(others)})")
        lines.append("")
        lines.append("| # | Identificador | Tipo | Descrição |")
        lines.append("|---|---|---|---|")
        for i, item in enumerate(others, 1):
            desc = item.title or item.status_note or "—"
            lines.append(f"| {i} | `{item.identifier}` | {item.item_type} | {desc[:80]} |")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Próximo passo",
        "",
        "1. **Avalie a necessidade.** Nem todo item identificado precisa entrar na síntese final. "
        "Use os critérios de inclusão/exclusão do protocolo PRISMA-2020 para decidir quais itens "
        "merecem esforço de obtenção.",
        "",
        f"2. **Providencie o full-text dos itens necessários** e coloque os arquivos em "
        f"`{input_dir}`. Aceitos: `.pdf`, `.docx`, `.txt`. O `ignorantia` reconhecerá os arquivos "
        "pelo DOI ou ISBN no nome (ex.: `10.1000_xxxx.pdf`) ou por mapeamento manual em "
        f"`{input_dir}/manifest.json`.",
        "",
        "3. **Itens não providenciados** serão registrados como **excluídos por "
        "inacessibilidade** no PRISMA flow diagram, com motivo declarado para auditoria. "
        "Isso é prática padrão e não compromete a integridade da revisão — desde que o gap "
        "seja honestamente reportado.",
        "",
        "4. **Quando estiver pronto, retome a execução** com:",
        "   ```bash",
        "   python3 scripts/searches/search_orchestrator.py --resume-after-gap-report \\",
        f"       --output-dir <mesmo output-dir>",
        "   ```",
        "",
        "Se desejar prosseguir sem providenciar nenhum item adicional, use:",
        "```bash",
        "python3 scripts/searches/search_orchestrator.py --skip-gap-resolution \\",
        f"    --output-dir <mesmo output-dir>",
        "```",
        "",
    ])
    return "\n".join(lines)


def generate_gap_report(tier0_payload: dict[str, Any],
                         books: list[GapItem] | None = None,
                         others: list[GapItem] | None = None,
                         output_path: str | Path | None = None,
                         project_id: str = "(não nomeado)",
                         input_dir: str = "search_results/user_provided/") -> GapReport:
    """Gera relatório completo de gap de acesso."""
    items = collect_gap_from_tier0(tier0_payload)
    if books:
        items.extend(books)
    if others:
        items.extend(others)

    md = render_md(items, project_id=project_id, input_dir=input_dir)

    report = GapReport(
        n_items=len(items),
        n_articles=sum(1 for i in items if i.item_type == "article"),
        n_books=sum(1 for i in items if i.item_type in ("book", "chapter")),
        n_other=sum(1 for i in items if i.item_type not in ("article", "book", "chapter")),
        items=items,
        project_id=project_id,
        input_dir=input_dir,
        md_text=md,
    )

    if output_path:
        Path(output_path).write_text(md, encoding="utf-8")
    return report


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Gera relatório de gap de acesso a partir do payload Tier 0.")
    parser.add_argument("--tier0-json", required=True,
                        help="Caminho para tier0_oa_enrichment.json")
    parser.add_argument("--output-dir", required=True,
                        help="Diretório onde salvar gap_report.md")
    parser.add_argument("--input-dir", default=None,
                        help="Diretório onde usuário deve colocar full-texts providenciados. "
                             "Default: <output-dir>/user_provided/")
    parser.add_argument("--project-id", default="(não nomeado)")
    parser.add_argument("--books-json", default=None,
                        help="JSON opcional com livros/capítulos identificados manualmente.")
    args = parser.parse_args()

    tier0_path = Path(args.tier0_json)
    if not tier0_path.exists():
        print(f"[gap_report] arquivo não encontrado: {tier0_path}", file=sys.stderr)
        return 2
    tier0_payload = json.loads(tier0_path.read_text(encoding="utf-8"))

    books: list[GapItem] = []
    if args.books_json:
        bp = Path(args.books_json)
        if bp.exists():
            for d in json.loads(bp.read_text(encoding="utf-8")):
                books.append(GapItem(
                    identifier=d.get("isbn") or d.get("id", "?"),
                    item_type=d.get("type", "book"),
                    title=d.get("title"),
                    journal_or_publisher=d.get("publisher"),
                    year=d.get("year"),
                    status_note=d.get("note"),
                ))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dir = args.input_dir or str(output_dir / "user_provided")
    Path(input_dir).mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "gap_report.md"

    report = generate_gap_report(
        tier0_payload, books=books,
        output_path=report_path,
        project_id=args.project_id,
        input_dir=input_dir,
    )

    print(f"[gap_report] {report.n_items} itens em gap "
          f"({report.n_articles} artigos, {report.n_books} livros, {report.n_other} outros)")
    print(f"[gap_report] relatório: {report_path}")
    print(f"[gap_report] usuário deve adicionar full-texts em: {input_dir}")
    if report.n_items > 0:
        print(f"[gap_report] PAUSA: revise {report_path} e providencie o que for necessário.")
        print(f"[gap_report] Retome com --resume-after-gap-report ou --skip-gap-resolution.")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
