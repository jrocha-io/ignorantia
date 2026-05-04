#!/usr/bin/env python3
"""
pipeline_finalize.py — Encadeia os 6 outputs obrigatórios da Fase 7 em uma execução.

Antes da v2.10.1, o usuário precisava rodar 5 comandos manualmente para gerar o
pacote final do paper. Este orquestrador unifica:

    1. cross_tabulation.py     → cross_tab.md (Decisão 29)
    2. format_abnt.py          → references_abnt.md (Decisão 28)
    3. render_chunks.py        → manuscript.html (Decisão 18)
    4. render_docx_abnt.py     → manuscript.docx (Decisão 31)
    5. render_latex.py         → manuscript.tex + manuscript.pdf (Decisão 32)
    6. screening_pipeline.py   → screening_log.csv (DD-10 Camada 2, v2.19.0)

Filosofia de design (alinhada às decisões editoriais 19, 30, 33):

- Operação legal + resolve problema = default, não opção (princípio v2.6.1).
  Logo, todos os 6 outputs rodam por default. Para pular algum, use flags `--skip-*`.

- Falha em uma etapa não invalida as anteriores. Cada etapa grava seu artefato em
  disco antes da próxima começar. Erros são reportados ao final em pipeline_summary.json.

v2.21.0 (B1, B3): preâmbulo contextual via flag `--contextual-preamble` propaga
a seção 'O campo onde este artigo vive' (DD-11) aos 3 renderers (chunks, docx,
latex). Antes da v2.21.0, integração existia nos renderers individuais mas
pipeline_finalize não passava — agora propaga.

- Pacote final fica em `<output-dir>/`. Comando único; relatório consolidado.

Inputs esperados em `<output-dir>/`:
    content.json              — produzido pela Fase 7 (sections, references, abstract...)
    extraction.csv            — produzido pela Fase 5 (uma linha por estudo)

Inputs opcionais:
    references_canonical.json — referências em formato dataclass para format_abnt.py
                                (se ausente, usa content.references como já formatadas)

Uso:
    python3 scripts/pipeline_finalize.py \\
        --output-dir search_results/ \\
        --title "Letramento digital de idosos" \\
        --version 1.0.0 \\
        --cross-tab-x model --cross-tab-y task

    # Pular .pdf (sem TeX Live):
    python3 scripts/pipeline_finalize.py [...] --skip-pdf

    # Pular .docx (sem python-docx):
    python3 scripts/pipeline_finalize.py [...] --skip-docx
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Adicionar parents path para imports relativos
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


@dataclass
class StepResult:
    name: str
    status: str  # "ok" | "skipped" | "error"
    artifact: str | None = None
    message: str | None = None
    elapsed_s: float | None = None


@dataclass
class PipelineResult:
    output_dir: Path
    steps: list[StepResult] = field(default_factory=list)
    final_artifacts: list[Path] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    summary_path: Path | None = None

    @property
    def n_ok(self) -> int:
        return sum(1 for s in self.steps if s.status == "ok")

    @property
    def n_errors(self) -> int:
        return sum(1 for s in self.steps if s.status == "error")

    @property
    def n_skipped(self) -> int:
        return sum(1 for s in self.steps if s.status == "skipped")


def _load_content(output_dir: Path) -> dict[str, Any]:
    p = output_dir / "content.json"
    if not p.exists():
        raise FileNotFoundError(
            f"Esperado {p} (output da Fase 7) não encontrado. "
            f"Execute a Fase 7 do skill antes do pipeline_finalize."
        )
    return json.loads(p.read_text(encoding="utf-8"))


def _step_cross_tab(output_dir: Path, content: dict, args) -> StepResult:
    import time
    t0 = time.time()
    if args.skip_cross_tab:
        return StepResult("cross_tabulation", "skipped",
                          message="--skip-cross-tab")
    extraction_csv = output_dir / "extraction.csv"
    if not extraction_csv.exists():
        return StepResult("cross_tabulation", "skipped",
                          message=f"{extraction_csv} não encontrado (sem extração tabulada)")
    if not args.cross_tab_x or not args.cross_tab_y:
        return StepResult("cross_tabulation", "skipped",
                          message="--cross-tab-x e --cross-tab-y não fornecidos")
    try:
        import cross_tabulation
        out_md = output_dir / "cross_tab.md"
        out_html = output_dir / "cross_tab.html"
        out_prose = output_dir / "cross_tab_prose.txt"
        # Recarregar extração
        extraction = cross_tabulation._load_extraction(extraction_csv)
        result = cross_tabulation.cross_tabulate(
            extraction, args.cross_tab_x, args.cross_tab_y, args.cross_tab_z,
        )
        out_md.write_text(result.markdown, encoding="utf-8")
        out_html.write_text(result.html, encoding="utf-8")
        out_prose.write_text(result.prose_summary, encoding="utf-8")
        return StepResult(
            "cross_tabulation", "ok", artifact=str(out_md),
            message=f"{result.n_with_all_dims}/{result.n_studies} estudos cruzados; "
                    f"{len(result.counts)} células",
            elapsed_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        return StepResult("cross_tabulation", "error",
                          message=f"{type(exc).__name__}: {exc}",
                          elapsed_s=round(time.time() - t0, 2))


def _step_format_abnt(output_dir: Path, content: dict, args) -> StepResult:
    """Formata referências canônicas em ABNT se houver references_canonical.json.

    Se o content.json já trouxer referências como strings formatadas (campo
    'references': ['SILVA, J... 2023.', ...]), pula este passo silenciosamente.
    """
    import time
    t0 = time.time()
    if args.skip_format_abnt:
        return StepResult("format_abnt", "skipped",
                          message="--skip-format-abnt")
    canonical_path = output_dir / "references_canonical.json"
    if not canonical_path.exists():
        n_refs = len(content.get("references", []))
        return StepResult(
            "format_abnt", "skipped",
            message=f"references_canonical.json não fornecido; usando "
                    f"{n_refs} refs já formatadas em content.json",
        )
    try:
        import format_abnt
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        refs = [format_abnt.Reference(**d) for d in canonical]
        out = format_abnt.format_bibliography(refs)
        out_md = output_dir / "references_abnt.md"
        out_md.write_text(out, encoding="utf-8")
        # Também substituir content.references com versão formatada para os renderers
        content["references"] = [format_abnt.format_reference_abnt(r) for r in refs]
        return StepResult(
            "format_abnt", "ok", artifact=str(out_md),
            message=f"{len(refs)} referências canônicas formatadas em ABNT",
            elapsed_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        return StepResult("format_abnt", "error",
                          message=f"{type(exc).__name__}: {exc}",
                          elapsed_s=round(time.time() - t0, 2))


def _step_render_html_chunks(output_dir: Path, content: dict, args) -> StepResult:
    import time
    t0 = time.time()
    if args.skip_html:
        return StepResult("render_html_chunks", "skipped",
                          message="--skip-html")
    try:
        import render_chunks
        out = output_dir / "manuscript.html"
        inter = output_dir / "_chunks_intermediate"
        chunks = render_chunks.chunks_from_content_json(content)
        if not chunks:
            # Compat: aceitar `sections` direto sem `content_html` (formato simples)
            return StepResult("render_html_chunks", "skipped",
                              message="content.json sem 'sections[]' processáveis")
        result = render_chunks.render_incremental(
            chunks, out,
            title=args.title, title_short=args.title_short or args.title,
            version=args.version, lang=args.lang,
            date_iso=args.date_iso, license_str=args.license_str,
            file_hash=args.file_hash,
            intermediate_dir=inter,
            resume_from_chunk=args.resume_from_chunk,
            # B1 (v2.21.0): propaga preâmbulo contextual ao render_chunks
            contextual_preamble_html=getattr(args, "_preamble_html", None),
        )
        return StepResult(
            "render_html_chunks", "ok", artifact=str(out),
            message=f"{len(result.chunks_processed)} chunks processados, "
                    f"{len(result.chunks_skipped)} pulados (cache); "
                    f"{result.final_size_bytes} bytes",
            elapsed_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        return StepResult("render_html_chunks", "error",
                          message=f"{type(exc).__name__}: {exc}",
                          elapsed_s=round(time.time() - t0, 2))


def _step_screening_pipeline(output_dir: Path, content: dict, args) -> StepResult:
    """F5 (v2.18.1, DD-10 Camada 2): integra screening_pipeline ao final pipeline.

    Roda a Camada 2 do screening (Fase 4 PRISMA-2020): 3 estágios sequenciais
    (title → abstract → full_text) com saída CSV PRISMA-compatible.

    Espera arquivo `<output_dir>/screening_decisions.json` com schema:
        {"decisions": [
            {"study_id": "S001", "doi": "...", "stage": "title",
             "decision": "kept", "reason": "...", "reviewer": "human"},
            ...
        ]}
    Se ausente e --screening-demo passado, aplica decisão demo (todos kept).
    Caso contrário, pula honestamente.
    """
    import time
    t0 = time.time()
    if args.skip_screening:
        return StepResult("screening_pipeline", "skipped",
                            message="--skip-screening")

    decisions_path = output_dir / "screening_decisions.json"
    studies_path = output_dir / "deduplicated_studies.json"

    if not studies_path.exists():
        return StepResult("screening_pipeline", "skipped",
                            message=f"deduplicated_studies.json ausente em {output_dir}; "
                                     "screening pipeline (Camada 2) requer estudos consolidados.")

    if not decisions_path.exists() and not args.screening_demo:
        return StepResult("screening_pipeline", "skipped",
                            message=f"screening_decisions.json ausente em {output_dir} "
                                     "e --screening-demo não passado. Para registrar "
                                     "Fase 4 PRISMA, forneça um JSON de decisões ou use "
                                     "--screening-demo (todos kept).")

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from screening_pipeline import ScreeningPipeline

        sp = ScreeningPipeline(output_dir)
        n = sp.load_studies(studies_path)

        if args.screening_demo:
            # Modo demo: aplica kept a todos em todos os 3 estágios
            for sid in sp.studies:
                sp.decide(sid, "title", "kept", "demo_relevant", "human")
                sp.decide(sid, "abstract", "kept", "demo_relevant", "human")
                sp.decide(sid, "full_text", "kept", "demo_relevant", "human")
        else:
            # Modo real: lê decisões de arquivo
            decisions_data = json.loads(decisions_path.read_text(encoding="utf-8"))
            for dec in decisions_data.get("decisions", []):
                try:
                    sp.decide(
                        dec["study_id"], dec["stage"], dec["decision"],
                        dec.get("reason", ""), dec.get("reviewer", "human"),
                    )
                except (ValueError, KeyError) as e:
                    # Não falha o pipeline por uma decisão malformada
                    continue

        log_path = sp.export_csv()
        counts_path = sp.export_prisma_counts()

        # Registrar em manifest reproducibility (DD-10 + Decisão 22)
        try:
            from manifest_helpers import load_manifest, save_manifest
            manifest_path = output_dir / "reproducibility_manifest.yaml"
            manifest = load_manifest(manifest_path)
            screening_runs = manifest.setdefault("screening_runs", [])
            screening_runs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "studies_loaded": n,
                "decisions_recorded": len(sp.events),
                "log_csv": str(log_path.relative_to(output_dir)),
                "counts_json": str(counts_path.relative_to(output_dir)),
                "demo_mode": bool(args.screening_demo),
            })
            save_manifest(manifest, manifest_path)
        except Exception:
            # Manifest é opcional; não bloqueia screening
            pass

        return StepResult(
            "screening_pipeline", "ok",
            artifact=str(log_path),
            message=f"{n} estudos carregados; {len(sp.events)} decisões registradas; "
                     f"CSV: {log_path.name}; counts: {counts_path.name}",
            elapsed_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        return StepResult("screening_pipeline", "error",
                            message=f"{type(exc).__name__}: {exc}",
                            elapsed_s=round(time.time() - t0, 2))


def _step_render_docx_abnt(output_dir: Path, content: dict, args) -> StepResult:
    import time
    t0 = time.time()
    if args.skip_docx:
        return StepResult("render_docx_abnt", "skipped", message="--skip-docx")
    try:
        import render_docx_abnt
        if not render_docx_abnt.DOCX_AVAILABLE:
            return StepResult("render_docx_abnt", "skipped",
                              message="python-docx não disponível "
                                      "(instale com `pip install python-docx`)")
        out = output_dir / "manuscript.docx"
        result = render_docx_abnt.render_docx_abnt(
            content, out,
            title=args.title,
            authors=content.get("authors", []),
            abstract=content.get("abstract"),
            keywords=content.get("keywords", []),
            # B1 (v2.21.0): propaga preâmbulo contextual ao render_docx_abnt
            contextual_preamble_markdown=getattr(args, "_preamble_markdown", None),
        )
        return StepResult(
            "render_docx_abnt", "ok", artifact=str(out),
            message=f"{result.n_sections} seções, {result.n_references} refs, "
                    f"{result.n_long_quotes} citações longas; {result.file_size_bytes} bytes",
            elapsed_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        return StepResult("render_docx_abnt", "error",
                          message=f"{type(exc).__name__}: {exc}",
                          elapsed_s=round(time.time() - t0, 2))


def _step_render_latex(output_dir: Path, content: dict, args) -> StepResult:
    import time
    t0 = time.time()
    if args.skip_tex:
        return StepResult("render_latex", "skipped", message="--skip-tex")
    try:
        import render_latex
        out_tex = output_dir / "manuscript.tex"
        compile_pdf = not args.skip_pdf
        result = render_latex.render_tex_and_pdf(
            content, out_tex,
            title=args.title,
            authors=content.get("authors", []),
            abstract=content.get("abstract"),
            keywords=content.get("keywords", []),
            compile_to_pdf=compile_pdf,
            engine=args.latex_engine,
            # B1 (v2.21.0): propaga preâmbulo contextual ao render_latex
            contextual_preamble_markdown=getattr(args, "_preamble_markdown", None),
        )
        artifacts = [str(out_tex)]
        msg_bits = [f"{result.n_sections} seções, {result.n_references} refs"]
        if result.pdf_compiled and result.pdf_path:
            artifacts.append(str(result.pdf_path))
            msg_bits.append(f"PDF: {result.pdf_path.name} ({result.pdf_path.stat().st_size} bytes)")
        elif compile_pdf and result.error:
            msg_bits.append(f"PDF não compilado: {result.error}")
        return StepResult(
            "render_latex", "ok",
            artifact=" + ".join(artifacts),
            message="; ".join(msg_bits),
            elapsed_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        return StepResult("render_latex", "error",
                          message=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                          elapsed_s=round(time.time() - t0, 2))


def _generate_contextual_preamble(args) -> tuple[str | None, str | None]:
    """B1 (v2.21.0, DD-11): gera preâmbulo contextual uma única vez e retorna
    (html, markdown) para propagação aos renderers.

    Retorna (None, None) se `--contextual-preamble` não foi passado ou se
    o módulo `contextual_preamble` não está disponível. Falha graciosamente.
    """
    if not getattr(args, "contextual_preamble", False):
        return (None, None)

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from contextual_preamble import ContextualPreamble, _mock_preamble
    except ImportError:
        print("[pipeline_finalize] WARN: contextual_preamble módulo ausente; "
              "preâmbulo desabilitado.", file=sys.stderr)
        return (None, None)

    topic = args.preamble_topic or args.title
    area = args.preamble_area or "multi"
    language = args.preamble_language or args.lang or "pt-BR"

    if args.preamble_mock:
        cp = _mock_preamble(topic, area, language)
    else:
        cp = ContextualPreamble(language=language)
        cp.set_topic(topic, area=area)
        try:
            cp.fetch_wikipedia_context()
            cp.fetch_wikidata_entities()
        except Exception as exc:
            # Erros emitem warnings via WikimediaFetchWarning;
            # render_html já mostra <p class="contextual-warning"> se vazio.
            print(f"[pipeline_finalize] WARN: preâmbulo fetch error: {exc}",
                  file=sys.stderr)

    return (cp.render_html(), cp.render_markdown())


@dataclass(frozen=True)
class PipelineStep:
    """E10 (v2.23.0, auditoria #5): descritor declarativo de uma etapa do pipeline.

    Antes da v2.23.0, run_pipeline tinha 6 chamadas hardcoded a _step_*.
    Adicionar nova etapa requeria editar o core. Open/Closed violation.

    Agora, PIPELINE_STEPS = [PipelineStep(...), ...] — adicionar etapa = adicionar
    tupla. run_pipeline itera o registry.
    """
    name: str
    label: str
    fn: "callable"  # signature: (output_dir, content, args) -> StepResult


# E10: registry declarativo das 6 etapas. Adicionar nova etapa = adicionar
# entrada nesta lista (Open/Closed).
PIPELINE_STEPS: list[PipelineStep] = [
    PipelineStep(name="cross_tab", label="cross_tabulation", fn=_step_cross_tab),
    PipelineStep(name="format_abnt", label="format_abnt", fn=_step_format_abnt),
    PipelineStep(name="render_html_chunks", label="render_html_chunks",
                 fn=_step_render_html_chunks),
    PipelineStep(name="render_docx_abnt", label="render_docx_abnt",
                 fn=_step_render_docx_abnt),
    PipelineStep(name="render_latex", label="render_latex", fn=_step_render_latex),
    PipelineStep(name="screening_pipeline", label="screening_pipeline",
                 fn=_step_screening_pipeline),
]


def run_pipeline(output_dir: Path, args) -> PipelineResult:
    """Executa todas as etapas em sequência. Falha em uma etapa não interrompe as demais.

    E10 (v2.23.0): itera PIPELINE_STEPS em vez de hardcoded.
    """
    result = PipelineResult(output_dir=output_dir)
    result.started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = _load_content(output_dir)

    # B1 (v2.21.0): gera preâmbulo contextual uma única vez para propagar
    # aos 3 renderers (chunks/HTML, docx, latex). Se desabilitado, ambos None.
    preamble_html, preamble_md = _generate_contextual_preamble(args)
    args._preamble_html = preamble_html
    args._preamble_markdown = preamble_md

    total = len(PIPELINE_STEPS)
    for i, step in enumerate(PIPELINE_STEPS, 1):
        sr = step.fn(output_dir, content, args)
        result.steps.append(sr)
        msg = sr.message or "—"
        print(f"  [{i}/{total}] {step.label:24} : {sr.status:8} — {msg}")
        if sr.artifact and sr.status == "ok":
            # Etapa render_latex pode produzir múltiplos artifacts separados por " + "
            for a in sr.artifact.split(" + "):
                result.final_artifacts.append(Path(a))

    result.finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Gravar pipeline_summary.json
    summary = {
        "schema_version": "1.0.0",
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "n_ok": result.n_ok,
        "n_skipped": result.n_skipped,
        "n_errors": result.n_errors,
        "steps": [s.__dict__ for s in result.steps],
        "final_artifacts": [str(p) for p in result.final_artifacts],
    }
    summary_path = output_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    result.summary_path = summary_path
    return result


def _cli() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output-dir", required=True,
                   help="Diretório com content.json (Fase 7) e extraction.csv (Fase 5).")
    p.add_argument("--title", required=True, help="Título do paper.")
    p.add_argument("--title-short", default=None, help="Título curto para topbar do HTML.")
    p.add_argument("--version", default="1.0.0", help="Versão SemVer.")
    p.add_argument("--lang", default="pt-BR")
    p.add_argument("--date-iso", default=None,
                   help="Data ISO no rodapé. Default: hoje (UTC).")
    p.add_argument("--license", dest="license_str", default="CC-BY-4.0")
    p.add_argument("--hash", dest="file_hash", default="—",
                   help="SHA-256 do pacote (preenchido após gerar; placeholder default).")

    # Cross-tabulação
    p.add_argument("--cross-tab-x", default=None, help="Coluna X da cross-tabulação (Decisão 29).")
    p.add_argument("--cross-tab-y", default=None, help="Coluna Y.")
    p.add_argument("--cross-tab-z", default=None, help="Coluna Z (estratificação opcional).")

    # LaTeX
    p.add_argument("--latex-engine", default="pdflatex", choices=["pdflatex", "xelatex"])

    # Resume HTML chunks
    p.add_argument("--resume-from-chunk", default=None,
                   help="ID do chunk a partir do qual processar (anteriores do cache).")

    # Skips
    p.add_argument("--skip-cross-tab", action="store_true")
    p.add_argument("--skip-format-abnt", action="store_true")
    p.add_argument("--skip-html", action="store_true")
    p.add_argument("--skip-docx", action="store_true",
                   help="Pula geração .docx (modo offline ou sem python-docx).")
    p.add_argument("--skip-tex", action="store_true",
                   help="Pula geração .tex e .pdf.")
    p.add_argument("--skip-pdf", action="store_true",
                   help="Gera .tex mas não compila .pdf (sem TeX Live).")
    p.add_argument("--skip-screening", action="store_true",
                   help="Pula etapa screening_pipeline (Camada 2 PRISMA-2020).")
    p.add_argument("--screening-demo", action="store_true",
                   help="Aplica screening demo (todos kept) na ausência de "
                         "screening_decisions.json. Útil para smoke test.")

    # B1 (v2.21.0, DD-11): preâmbulo contextual via pipeline.
    # Quando ativado, gera UMA seção 'O campo onde este artigo vive' propagada
    # aos 3 renderers (HTML, docx, latex). Antes da v2.21.0, integração existia
    # nos renderers individuais mas pipeline_finalize não passava.
    p.add_argument("--contextual-preamble", action="store_true",
                   help="Inclui seção 'O campo onde este artigo vive' "
                         "(Wikipedia + Wikidata) antes da Introdução nos 3 "
                         "renderers. DD-11.")
    p.add_argument("--preamble-topic", default=None,
                   help="Tópico do preâmbulo contextual (default: usa --title).")
    p.add_argument("--preamble-area", default="multi",
                   choices=["saude", "educacao", "cs_se", "ciencias_sociais",
                            "humanidades", "business", "multi"],
                   help="Área para mapeamento de disciplinas-mãe.")
    p.add_argument("--preamble-language", default=None,
                   help="Idioma do preâmbulo (default: usa --lang).")
    p.add_argument("--preamble-mock", action="store_true",
                   help="Usa fixtures determinísticas (CI/offline).")

    args = p.parse_args()
    args.date_iso = args.date_iso or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"ERRO: --output-dir não existe: {output_dir}", file=sys.stderr)
        return 2

    print("=" * 70)
    print(f"PIPELINE_FINALIZE — {args.title!r} v{args.version}")
    print(f"Output: {output_dir}")
    print("=" * 70)

    try:
        result = run_pipeline(output_dir, args)
    except FileNotFoundError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 2

    print()
    print("=" * 70)
    print(f"RESUMO — {result.n_ok} ok / {result.n_skipped} pulados / {result.n_errors} erros")
    print("=" * 70)
    for s in result.steps:
        symbol = {"ok": "✓", "skipped": "·", "error": "✗"}[s.status]
        elapsed = f"  ({s.elapsed_s}s)" if s.elapsed_s else ""
        print(f"  {symbol} {s.name:<22}{elapsed}")
    print()
    if result.final_artifacts:
        print("Artefatos gerados:")
        for a in result.final_artifacts:
            if a.exists():
                print(f"  • {a} ({a.stat().st_size} bytes)")
    print()
    print(f"Resumo completo: {result.summary_path}")

    return 0 if result.n_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(_cli())
