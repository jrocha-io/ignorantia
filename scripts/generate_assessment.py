#!/usr/bin/env python3
"""
generate_assessment.py — Generate the avaliacao_v<X.Y.Z>.md report.

Inspects the package artifacts and produces a graded assessment per
references/quality-rubric.md. The score is an internal estimate that
helps the human author know how far they are from elite-venue submission.

It does NOT replace peer review. It DOES catch missing artifacts,
incomplete declarations, and structural deficiencies that would block
submission to top-tier publishers.

Usage:
    python generate_assessment.py \\
        --package-dir /path/to/package \\
        --content manuscript-content.json \\
        --extraction extraction.csv \\
        --qa quality-appraisal.csv \\
        --searches searches.json \\
        --html manuscript.html \\
        --version 1.0.0 \\
        --topic-slug bnce-gamificacao \\
        --area "Educação" \\
        --lang pt-BR \\
        --out avaliacao_v1.0.0.md
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _reference_helpers import extract_doi, extract_url  # noqa: E402

# ── gate (Fix 9, RS-42 dogfood remediation) ──────────────────────────────────
#
# The assessor used to always exit 0, even when reporting eliminatórios or
# scores far below submission threshold. RS-42 v1.0.0 was packaged and shipped
# with a 4.0/10.0 grade and three eliminatórios because nothing programmatic
# blocked it. Fix 9 turns the assessor into a gate: it still always writes the
# Markdown report, but it also writes a machine-readable `assessment_gate.json`
# sidecar and exits non-zero (code 2) when the gate fails, so any wrapper that
# chains "assess && package" short-circuits correctly.

_DEFAULT_GATE_MIN_SCORE = 7.0
_GATE_EXIT_CODE = 2
_GATE_SIDECAR_FILENAME = "assessment_gate.json"


# ── helpers ─────────────────────────────────────────────────────────────────

def sha256_short(path):
    if not Path(path).exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def file_text(path):
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_csv(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── per-dimension assessment ────────────────────────────────────────────────

def assess_d1_methodology(args, ctx):
    """D1 — Rigor metodológico (peso 3.0)."""
    points = 0.0
    notes = []
    crit = []

    # 0.6 — protocol exists with PICO/PICOC, CI/CE numbered, booleans per base
    protocol = file_text(Path(args.package_dir) / "protocol.md")
    has_pico = bool(re.search(r"PICO|PICOC", protocol, re.I))
    has_ci = bool(re.search(r"CI[1-9]|critéri[oa]s?\s+de\s+inclus", protocol, re.I))
    has_ce = bool(re.search(r"CE[1-9]|critéri[oa]s?\s+de\s+exclus", protocol, re.I))
    has_strings = bool(re.search(r"TITLE-ABS|abs:|all:|TS=|search_query", protocol, re.I))
    if has_pico and has_ci and has_ce and has_strings:
        points += 0.6
        crit.append(("0.6/0.6", "Protocolo pré-registrado com PICO/PICOC, CI/CE, strings booleanas"))
    elif protocol:
        points += 0.3
        crit.append(("0.3/0.6", "Protocolo presente mas incompleto (faltam PICO ou CI/CE numerados ou strings booleanas explícitas)"))
        notes.append("Completar protocolo com PICO/PICOC explícito, critérios CI1...CIn e CE1...CEn, e strings booleanas literais por base.")
    else:
        crit.append(("0.0/0.6", "Protocolo ausente (protocol.md não encontrado)"))
        notes.append("Gerar protocol.md a partir de assets/templates/protocol.md.")

    # 0.5 — PRISMA flow with coherent numbers
    prisma_path = Path(args.package_dir) / "prisma-flow.svg"
    flow_data = load_json(Path(args.package_dir) / "prisma-flow.json")
    coherent = False
    if flow_data:
        try:
            n_id = sum(d["n"] for d in flow_data["identification"]["from_databases"])
            n_dedup = flow_data.get("after_dedup", 0)
            n_screened = flow_data["screening"]["screened"]
            n_assessed = flow_data["eligibility"]["assessed"]
            n_inc = flow_data["included"]["studies"]
            coherent = (n_id >= n_dedup >= n_screened >= n_assessed >= n_inc)
        except (KeyError, TypeError):
            coherent = False
    if prisma_path.exists() and coherent:
        points += 0.5
        crit.append(("0.5/0.5", "PRISMA flow presente, números coerentes"))
    elif prisma_path.exists():
        points += 0.25
        crit.append(("0.25/0.5", "PRISMA flow presente mas coerência não verificável (ou prisma-flow.json ausente)"))
        notes.append("Garantir que identified ≥ deduplicated ≥ screened ≥ assessed ≥ included nos contadores do flow.")
    else:
        crit.append(("0.0/0.5", "PRISMA flow ausente"))
        notes.append("Gerar prisma-flow.svg via scripts/prisma_flow.py.")

    # 0.4 — searches in ≥ 5 distinct bases, with date and string per base
    searches = load_json(args.searches) if args.searches else None
    n_bases = 0
    if searches:
        per_db = searches.get("per_database", searches if isinstance(searches, list) else [])
        n_bases = len(per_db) if isinstance(per_db, list) else 0
    if n_bases >= 5:
        points += 0.4
        crit.append((f"0.4/0.4", f"{n_bases} bases consultadas (≥5)"))
    elif n_bases >= 3:
        points += 0.2
        crit.append((f"0.2/0.4", f"Apenas {n_bases} bases (recomendado ≥5)"))
        notes.append(f"Adicionar buscas em mais bases (atual: {n_bases}). Para SE/CS, garantir IEEE Xplore + ACM DL + dblp; para saúde, PubMed/MEDLINE; para pt-BR, SciELO + BDTD + CAPES.")
    else:
        crit.append((f"0.0/0.4", f"Cobertura insuficiente: {n_bases} bases"))
        notes.append("CRÍTICO — buscar em pelo menos 5 bases. Cobertura atual viola PRISMA.")

    # 0.3 — snowballing
    has_snowball = bool(re.search(r"snowball|wohlin|forward|backward.*citation", protocol, re.I))
    if has_snowball:
        points += 0.3
        crit.append(("0.3/0.3", "Snowballing documentado"))
    else:
        crit.append(("0.0/0.3", "Snowballing não documentado"))
        notes.append("Executar e documentar snowballing forward + backward (Wohlin 2014) a partir dos seed papers.")

    # 0.4 — QA applied to all included
    qa_rows = load_csv(args.qa)
    extr_rows = load_csv(args.extraction)
    if qa_rows and extr_rows and len(qa_rows) >= len(extr_rows):
        points += 0.4
        crit.append((f"0.4/0.4", f"QA aplicada a {len(qa_rows)}/{len(extr_rows)} estudos"))
    elif qa_rows:
        partial = 0.4 * (len(qa_rows) / max(len(extr_rows), 1))
        points += partial
        crit.append((f"{partial:.2f}/0.4", f"QA parcial: {len(qa_rows)}/{len(extr_rows)} estudos"))
        notes.append(f"Aplicar QA aos {len(extr_rows) - len(qa_rows)} estudos restantes.")
    else:
        crit.append(("0.0/0.4", "Quality appraisal ausente"))
        notes.append("CRÍTICO — gerar quality-appraisal.csv com pontuação CASP/DARE/Kitchenham por estudo.")

    # 0.3 — explicit threshold + transparent treatment
    threshold_explicit = bool(re.search(r"threshold|corte|≥\s*\d|>=\s*\d", protocol, re.I))
    if threshold_explicit:
        points += 0.3
        crit.append(("0.3/0.3", "Threshold de QA explícito no protocolo"))
    else:
        crit.append(("0.0/0.3", "Threshold de QA não declarado"))
        notes.append("Declarar threshold de QA no protocolo (e.g., ≥ 50% do máximo) e tratar transparentemente os abaixo.")

    # 0.3 — Cohen's kappa mentioned as pending for human review
    has_kappa_note = bool(re.search(r"kappa|Cohen", protocol + " " + file_text(Path(args.package_dir) / "README.md"), re.I))
    if has_kappa_note:
        points += 0.3
        crit.append(("0.3/0.3", "Cohen's kappa documentado como pendente para revisão humana"))
    else:
        crit.append(("0.0/0.3", "Cohen's kappa não mencionado"))
        notes.append("Adicionar nota no protocol.md e README.md: Cohen's kappa será calculado pelos dois revisores humanos no Zenodo após upload; o skill não simula segundo revisor.")

    # 0.2 — Kitchenham QA1-QA8 if SE/CS
    is_se_cs = ctx.get("is_se_cs", False)
    has_kitchenham = bool(re.search(r"Kitchenham|QA1.*QA8|Dyba", protocol, re.I))
    if is_se_cs and has_kitchenham:
        points += 0.2
        crit.append(("0.2/0.2", "Kitchenham QA aplicado (SE/CS)"))
    elif is_se_cs:
        crit.append(("0.0/0.2", "Tema é SE/CS mas Kitchenham QA1-QA8 não aplicado"))
        notes.append("Tema SE/CS — adicionar Kitchenham QA1–QA8 ou Dyba-Dingsoyr 11Q como complemento ao DARE.")
    else:
        # Not SE/CS — give the points by default (criterion not applicable)
        points += 0.2
        crit.append(("0.2/0.2", "N/A (não é SE/CS)"))

    return min(points, 3.0), crit, notes


def assess_d2_compliance(args, ctx):
    """D2 — Compliance ético-legal (peso 2.0)."""
    points = 0.0
    notes = []
    crit = []
    is_ptbr = ctx.get("is_ptbr", True)
    html = file_text(args.html) if args.html else ""
    content = ctx.get("content") or {}
    ai_decl = content.get("ai_declaration") or {}

    # 0.5 — declaration with all required fields
    required_fields = ["tool", "provider", "interface", "stages",
                       "purpose_per_stage", "human_oversight", "authors_responsible"]
    filled = sum(1 for f in required_fields if ai_decl.get(f))
    decl_score = 0.5 * (filled / len(required_fields))
    points += decl_score
    if filled == len(required_fields):
        label = "Declaração completa (todos 8 campos)" if is_ptbr else "Declaration complete (all fields)"
        crit.append((f"0.5/0.5", label))
    else:
        crit.append((f"{decl_score:.2f}/0.5", f"Declaração de IA incompleta: {filled}/{len(required_fields)} campos"))
        missing = [f for f in required_fields if not ai_decl.get(f)]
        notes.append(f"Preencher campos faltantes na declaração de IA: {', '.join(missing)}.")

    # 0.3 (or 0.4 EN) — IA NOT listed as author
    ia_as_author_pattern = re.compile(
        r"(?:autor|author).{0,40}?(claude|gpt|gemini|chatgpt|llm|copilot|llama|bard)",
        re.I)
    ia_in_author = bool(ia_as_author_pattern.search(html)) if html else False
    weight = 0.3 if is_ptbr else 0.4
    if not ia_in_author:
        points += weight
        crit.append((f"{weight}/{weight}", "IA NÃO listada como autora"))
    else:
        crit.append((f"0.0/{weight}", "ATENÇÃO: IA possivelmente listada como autora"))
        notes.append("CRÍTICO/ELIMINATÓRIO — verificar se IA está listada como autora; remover se estiver.")

    if is_ptbr:
        # 0.3 — CAPES area documents referenced
        readme = file_text(Path(args.package_dir) / "README.md")
        compliance_check = file_text(Path(args.package_dir) / "compliance-checklist.md")
        text_blob = readme + compliance_check
        has_capes_doc = bool(re.search(r"Documento\s+de\s+Área|CAPES.*área|área-mãe", text_blob, re.I))
        if has_capes_doc:
            points += 0.3
            crit.append(("0.3/0.3", "Documento de Área CAPES referenciado"))
        else:
            crit.append(("0.0/0.3", "Documento de Área CAPES não referenciado"))
            notes.append("Consultar e referenciar o Documento de Área CAPES da disciplina; identificar periódicos prioritários da área.")

        # 0.2 — CEP/CONEP status declared
        has_cep = bool(re.search(r"CEP|CONEP|CNS\s*466|CNS\s*510", text_blob + protocol_text(args), re.I))
        if has_cep:
            points += 0.2
            crit.append(("0.2/0.2", "Status CEP/CONEP declarado"))
        else:
            crit.append(("0.0/0.2", "Status CEP/CONEP não declarado"))
            notes.append("Declarar no protocolo se SLR requer CEP/CONEP (geralmente N/A para SLR de literatura publicada, mas declarar explicitamente).")

        # 0.2 — LGPD
        has_lgpd = bool(re.search(r"LGPD|13\.709|dados\s+pessoa", text_blob + protocol_text(args), re.I))
        if has_lgpd:
            points += 0.2
            crit.append(("0.2/0.2", "LGPD considerada"))
        else:
            crit.append(("0.0/0.2", "LGPD não mencionada"))
            notes.append("Adicionar nota LGPD no compliance-checklist.md, especialmente para temas com dados sensíveis.")

        # 0.2 — copyright (LDA)
        has_lda = bool(re.search(r"9\.610|direitos\s+autorais|CC-BY|CC-BY-4|creative\s*commons",
                                 text_blob + html, re.I))
        if has_lda:
            points += 0.2
            crit.append(("0.2/0.2", "Lei de Direitos Autorais respeitada (licença declarada)"))
        else:
            crit.append(("0.0/0.2", "Licença / LDA não explícita"))
            notes.append("Declarar licença CC-BY-4.0 e citação com atribuição (já automático via DOI clicáveis).")

        # 0.2 — vedação projetos terceiros (verificável apenas se há atestação no checklist)
        has_vedacao = bool(re.search(r"projeto.*terceir|veda(ção|do).*IAG|art\.?\s*9.*IAG", text_blob, re.I))
        if has_vedacao:
            points += 0.2
            crit.append(("0.2/0.2", "Vedação a projetos de terceiros em IAG atestada"))
        else:
            points += 0.1  # benefit of the doubt
            crit.append(("0.1/0.2", "Vedação a projetos de terceiros não atestada explicitamente"))
            notes.append("Adicionar atestação no compliance-checklist.md: 'Nenhum projeto de pesquisa de terceiro foi inserido em IAG (Portaria CNPq art. 9).'")

        # 0.1 — fomento declared
        has_fomento = bool(re.search(r"CNPq|CAPES|FAPESP|FAPERJ|FAPEMIG|fomento|funding",
                                     text_blob + html, re.I))
        if has_fomento:
            points += 0.1
            crit.append(("0.1/0.1", "Fomento declarado quando aplicável"))
        else:
            points += 0.1  # might be no funding
            crit.append(("0.1/0.1", "Sem fomento ou declarado N/A"))

    else:
        # English manuscript checklist
        readme = file_text(Path(args.package_dir) / "README.md")
        compliance_check = file_text(Path(args.package_dir) / "compliance-checklist.md")
        text_blob = readme + compliance_check + html

        # 0.3 — publisher policy followed
        has_publisher_policy = bool(re.search(r"COPE|ICMJE|publisher.*policy", text_blob, re.I))
        if has_publisher_policy:
            points += 0.3
            crit.append(("0.3/0.3", "Publisher policy (COPE/ICMJE) referenced"))
        else:
            crit.append(("0.0/0.3", "Publisher policy not referenced"))
            notes.append("Reference COPE/ICMJE in compliance-checklist.md; align with target publisher's specific AI policy.")

        # 0.2 — no AI-generated images, or declared
        has_ai_imgs_decl = bool(re.search(r"image.*generated by AI|no AI-generated", text_blob, re.I))
        points += 0.2  # default assume no AI images
        crit.append(("0.2/0.2", "AI-generated images: none, or declared"))

        # 0.2 — Conflict of Interest + Funding statements
        has_coi = bool(re.search(r"conflict of interest|competing interests", text_blob + html, re.I))
        has_funding = bool(re.search(r"funding|grant|fellowship", text_blob + html, re.I))
        if has_coi and has_funding:
            points += 0.2
            crit.append(("0.2/0.2", "CoI + Funding statements present"))
        elif has_coi or has_funding:
            points += 0.1
            crit.append(("0.1/0.2", f"Only {'CoI' if has_coi else 'Funding'} present"))
            notes.append("Add both Conflict of Interest and Funding statements.")
        else:
            crit.append(("0.0/0.2", "CoI and Funding statements missing"))
            notes.append("Add Conflict of Interest and Funding statements (required by ICMJE).")

        # 0.2 — confidentiality of peer review acknowledged
        has_confid = bool(re.search(r"confidentiality|do not upload|peer review.*AI", text_blob, re.I))
        if has_confid:
            points += 0.2
            crit.append(("0.2/0.2", "Peer-review confidentiality acknowledged"))
        else:
            points += 0.1
            crit.append(("0.1/0.2", "Confidentiality not explicitly acknowledged"))
            notes.append("Add a note in compliance-checklist.md: manuscripts under peer review will not be uploaded to LLMs (ICMJE Section II.C.2.a).")

        # 0.2 — citations have DOI
        refs = content.get("references", [])
        with_doi = sum(1 for r in refs if extract_doi(r) or extract_url(r))
        if refs and with_doi / len(refs) >= 0.9:
            points += 0.2
            crit.append((f"0.2/0.2", f"Citations with DOI/URL: {with_doi}/{len(refs)}"))
        elif refs:
            partial = 0.2 * (with_doi / len(refs))
            points += partial
            crit.append((f"{partial:.2f}/0.2", f"Only {with_doi}/{len(refs)} refs have DOI/URL"))
            notes.append("Ensure ≥ 90% of references have DOI or canonical URL.")
        else:
            crit.append(("0.0/0.2", "No references found"))

    return min(points, 2.0), crit, notes


def protocol_text(args):
    return file_text(Path(args.package_dir) / "protocol.md")


def assess_d3_corpus(args, ctx):
    """D3 — Qualidade do corpus (peso 2.0)."""
    points = 0.0
    notes = []
    crit = []
    extr_rows = load_csv(args.extraction)
    qa_rows = load_csv(args.qa)
    n_inc = len(extr_rows)

    # 0.4 — number sufficient
    is_se_cs = ctx.get("is_se_cs", False)
    is_health = ctx.get("is_health", False)
    if is_se_cs:
        threshold = 30
    elif is_health:
        threshold = 20
    else:
        threshold = 15
    if n_inc >= threshold:
        points += 0.4
        crit.append((f"0.4/0.4", f"{n_inc} estudos incluídos (≥ {threshold} para a área)"))
    elif n_inc >= threshold * 0.5:
        partial = 0.4 * (n_inc / threshold)
        points += partial
        crit.append((f"{partial:.2f}/0.4", f"{n_inc} estudos (abaixo do esperado {threshold} para a área)"))
        notes.append(f"Considerar relaxar critérios ou ampliar busca para chegar a ≥ {threshold} estudos. Ou justificar explicitamente no protocolo.")
    else:
        crit.append((f"0.0/0.4", f"Apenas {n_inc} estudos — corpus muito pequeno"))
        notes.append(f"CRÍTICO — corpus de {n_inc} estudos é insuficiente. Mínimo recomendado: {threshold}.")

    # 0.4 — venues of elite present (≥30% intl, ≥20% Qualis A1-A2 for pt-BR)
    elite_venues_intl = re.compile(
        r"IEEE\s+Trans|ACM\s+Trans|TVCG|TPAMI|TSE|CSUR|TOCHI|TOIS|TOG|"
        r"Nature(?:\s|$)|Science(?:\s|$)|PNAS|Cell|Lancet|NEJM|JAMA|BMJ|"
        r"NeurIPS|ICML|ICLR|CHI|SIGGRAPH|ICSE|UIST|CVPR|ICCV|ACL|EMNLP|"
        r"ASME|APS|RSC|JACS|Angewandte|"
        r"Cambridge|Oxford\s+University|MIT\s+Press|"
        r"PLOS|eLife|Royal\s+Society", re.I)
    elite_count = sum(
        1 for r in extr_rows
        if elite_venues_intl.search((r.get("venue", "") or "") + " " + (r.get("citation", "") or ""))
    )
    pct_elite = (elite_count / n_inc * 100) if n_inc else 0
    threshold_pct = 20 if ctx.get("is_ptbr", True) else 30
    if pct_elite >= threshold_pct:
        points += 0.4
        crit.append((f"0.4/0.4", f"{pct_elite:.0f}% dos estudos vêm de venues de elite (≥{threshold_pct}%)"))
    elif pct_elite >= threshold_pct / 2:
        partial = 0.4 * (pct_elite / threshold_pct)
        points += partial
        crit.append((f"{partial:.2f}/0.4", f"Apenas {pct_elite:.0f}% de venues de elite"))
        notes.append(f"Buscar mais ativamente em IEEE Xplore, ACM DL, Nature/Springer, Elsevier flagship, Wiley flagship, etc. Atual: {elite_count}/{n_inc} = {pct_elite:.0f}% (alvo: ≥{threshold_pct}%).")
    else:
        crit.append((f"0.0/0.4", f"Quase nenhum venue de elite ({pct_elite:.0f}%)"))
        notes.append(f"CRÍTICO — apenas {elite_count}/{n_inc} estudos de venues de elite. Para nota 10, buscar mais nas bases dos publishers de elite (`references/compliance-international.md`).")

    # 0.3 — temporal window respected (proxy: years vary)
    years = [r.get("year") for r in extr_rows if r.get("year")]
    if years:
        try:
            yrs = sorted(set(int(y) for y in years if str(y).isdigit()))
            span = yrs[-1] - yrs[0] if len(yrs) > 1 else 0
            if span >= 3:
                points += 0.3
                crit.append((f"0.3/0.3", f"Corpus cobre {yrs[0]}-{yrs[-1]} (span de {span} anos)"))
            else:
                points += 0.15
                crit.append((f"0.15/0.3", f"Corpus muito concentrado temporalmente ({yrs[0]}-{yrs[-1]})"))
                notes.append("Considerar ampliar janela temporal ou incluir estudos seminais fora da janela com justificativa.")
        except ValueError:
            crit.append(("0.0/0.3", "Anos malformados na extração"))
    else:
        crit.append(("0.0/0.3", "Anos ausentes na extração"))
        notes.append("Garantir que cada linha de extraction.csv tem o campo year preenchido.")

    # 0.3 — diversity of study types
    types = [r.get("study_type", "") or r.get("methods", "") for r in extr_rows]
    distinct_types = len(set(t.lower().split(",")[0].strip() for t in types if t))
    if distinct_types >= 3:
        points += 0.3
        crit.append((f"0.3/0.3", f"Diversidade de tipos de estudo: {distinct_types}"))
    elif distinct_types >= 2:
        points += 0.15
        crit.append((f"0.15/0.3", f"Apenas {distinct_types} tipos distintos"))
        notes.append("Buscar diversidade entre teóricos, empíricos quantitativos, qualitativos, mistos.")
    else:
        crit.append(("0.0/0.3", "Pouca diversidade de tipos"))
        notes.append("Corpus monolítico — diversificar tipos de estudo se possível.")

    # 0.3 — QA scores good
    if qa_rows:
        totals = []
        for r in qa_rows:
            v = r.get("consensus_total") or r.get("reviewer1_total") or "0"
            try:
                totals.append(float(v))
            except ValueError:
                pass
        if totals:
            mx = max(totals) or 1
            avg_pct = (sum(totals) / len(totals)) / mx * 100
            if avg_pct >= 70:
                points += 0.3
                crit.append((f"0.3/0.3", f"QA score médio: {avg_pct:.0f}% (≥70%)"))
            elif avg_pct >= 60:
                points += 0.15
                crit.append((f"0.15/0.3", f"QA médio: {avg_pct:.0f}% (limítrofe)"))
                notes.append("QA scores baixos — considerar excluir estudos abaixo do threshold.")
            else:
                crit.append((f"0.0/0.3", f"QA médio: {avg_pct:.0f}% (insuficiente)"))
                notes.append("CRÍTICO — qualidade do corpus é baixa. Aplicar threshold mais rigoroso ou buscar literatura de melhor qualidade.")

    # 0.3 — RQ saturation (proxy: every RQ is referenced by at least 3 studies)
    content = ctx.get("content") or {}
    rqs = content.get("rqs", [])
    if rqs and extr_rows:
        rq_coverage = {}
        for r in extr_rows:
            for rq in re.split(r"[,;]\s*", r.get("rq_addressed", "")):
                rq = rq.strip()
                if rq:
                    rq_coverage[rq] = rq_coverage.get(rq, 0) + 1
        unsatured = [rq for rq in rq_coverage if rq_coverage[rq] < 3]
        if not unsatured and rq_coverage:
            points += 0.3
            crit.append(("0.3/0.3", "Todas RQs com saturação suficiente (≥3 estudos cada)"))
        elif rq_coverage:
            points += 0.15
            crit.append((f"0.15/0.3", f"RQs com baixa saturação: {unsatured}"))
            notes.append(f"Aprofundar busca para RQs com poucos estudos: {', '.join(unsatured)}.")
        else:
            crit.append(("0.0/0.3", "Nenhuma RQ é mapeada a estudos no extraction.csv"))
            notes.append("Preencher coluna rq_addressed em extraction.csv para cada estudo.")

    return min(points, 2.0), crit, notes


def assess_d4_textual(args, ctx):
    """D4 — Qualidade textual e estrutural (peso 1.5)."""
    points = 0.0
    notes = []
    crit = []
    content = ctx.get("content") or {}
    sections = {
        "abstract_html": (0.2, "Abstract"),
        "introduction_html": (0.2, "Introdução"),
        "background_html": (0.2, "Background"),
        "methodology_html": (0.0, "Método"),  # already weighted in D1
        "synthesis_html": (0.2, "Síntese"),
        "discussion_html": (0.2, "Discussão"),
        "threats_html": (0.2, "Threats to validity"),
        "conclusion_html": (0.0, "Conclusão"),  # weighted with structure
    }

    # 0.3 — all §00–§10 present (count non-empty)
    nonempty = sum(1 for k in sections if (content.get(k) or "").strip())
    structural = 0.3 * (nonempty / len(sections))
    points += structural
    if nonempty == len(sections):
        crit.append(("0.3/0.3", f"Todas as seções narrativas presentes ({nonempty}/{len(sections)})"))
    else:
        crit.append((f"{structural:.2f}/0.3", f"Apenas {nonempty}/{len(sections)} seções preenchidas"))
        empty_keys = [v[1] for k, v in sections.items() if not (content.get(k) or "").strip()]
        notes.append(f"Preencher seções vazias: {', '.join(empty_keys)}.")

    # 0.2 — abstract length 200-300 words
    abstract = re.sub(r"<[^>]+>", " ", content.get("abstract_html", "") or "")
    n_words = len(abstract.split())
    if 200 <= n_words <= 320:
        points += 0.2
        crit.append((f"0.2/0.2", f"Abstract com {n_words} palavras (faixa ideal)"))
    elif 150 <= n_words < 200:
        points += 0.1
        crit.append((f"0.1/0.2", f"Abstract com {n_words} palavras (curto)"))
        notes.append(f"Expandir abstract para 200-300 palavras (atual: {n_words}).")
    elif n_words > 320:
        points += 0.1
        crit.append((f"0.1/0.2", f"Abstract com {n_words} palavras (longo)"))
        notes.append(f"Reduzir abstract para 200-300 palavras (atual: {n_words}).")
    else:
        crit.append((f"0.0/0.2", f"Abstract muito curto ou ausente: {n_words} palavras"))
        notes.append("Escrever abstract estruturado de 200-300 palavras: contexto, objetivo, método, resultados, conclusão.")

    # 0.2 — introduction has explicit RQs declared
    intro = content.get("introduction_html", "") or ""
    has_rq_decl = bool(re.search(r"RQ\d|pergunta de pesquisa|research question", intro, re.I))
    if has_rq_decl:
        points += 0.2
        crit.append(("0.2/0.2", "RQs explicitadas na introdução"))
    else:
        crit.append(("0.0/0.2", "RQs não explicitadas na introdução"))
        notes.append("Declarar explicitamente as RQs no final da introdução.")

    # 0.2 — references in background (canonical authors cited)
    bg = content.get("background_html", "") or ""
    n_refs_bg = len(re.findall(r"\[\d+", bg))
    if n_refs_bg >= 5:
        points += 0.2
        crit.append((f"0.2/0.2", f"Background cita {n_refs_bg} referências"))
    elif n_refs_bg >= 2:
        points += 0.1
        crit.append((f"0.1/0.2", f"Background cita apenas {n_refs_bg} referências"))
        notes.append("Ampliar referencial teórico no background (≥5 citações de autores canônicos da área).")
    else:
        crit.append((f"0.0/0.2", "Background pouco fundamentado"))
        notes.append("Adicionar referencial teórico mais robusto no background.")

    # 0.2 — synthesis is narrative-thematic
    synthesis = content.get("synthesis_html", "") or ""
    n_synth_words = len(re.sub(r"<[^>]+>", " ", synthesis).split())
    if n_synth_words >= 800:
        points += 0.2
        crit.append((f"0.2/0.2", f"Síntese substantiva ({n_synth_words} palavras)"))
    elif n_synth_words >= 400:
        points += 0.1
        crit.append((f"0.1/0.2", f"Síntese moderada ({n_synth_words} palavras)"))
        notes.append("Aprofundar síntese narrativa-temática por RQ. Cross-tabulação por dimensão deveria ser explícita.")
    else:
        crit.append((f"0.0/0.2", f"Síntese curta demais ({n_synth_words} palavras)"))
        notes.append("CRÍTICO — síntese precisa de aprofundamento substantivo. Listar achados por RQ não basta; é preciso interpretar e cross-tabular.")

    # 0.2 — discussion has guidelines (≥5 numbered)
    disc = content.get("discussion_html", "") or ""
    n_guidelines = len(re.findall(r"\bG\d|guideline\s*\d|diretriz\s*\d", disc, re.I))
    if n_guidelines >= 5:
        points += 0.2
        crit.append((f"0.2/0.2", f"{n_guidelines} guidelines numeradas na discussão"))
    elif n_guidelines >= 3:
        points += 0.1
        crit.append((f"0.1/0.2", f"Apenas {n_guidelines} guidelines"))
        notes.append("Adicionar mais guidelines/insights acionáveis na discussão (alvo: ≥5).")
    else:
        crit.append((f"0.0/0.2", "Sem guidelines numeradas"))
        notes.append("Estruturar discussão em torno de guidelines numeradas (G1, G2, ...) com base no corpus.")

    # 0.2 — threats discussion covers 4 validity types
    threats = content.get("threats_html", "") or ""
    types_validity = sum(1 for t in ["construct", "internal", "external", "conclusion"]
                          if re.search(t + r"\s+validity", threats, re.I))
    if types_validity >= 3:
        points += 0.2
        crit.append((f"0.2/0.2", f"{types_validity}/4 tipos de validade discutidos"))
    elif types_validity >= 1:
        points += 0.1
        crit.append((f"0.1/0.2", f"Apenas {types_validity}/4 tipos discutidos"))
        notes.append("Cobrir os 4 tipos de validade (construct, internal, external, conclusion) per Kitchenham et al. 2022.")
    else:
        crit.append((f"0.0/0.2", "Threats to validity superficial"))
        notes.append("Discutir explicitamente os 4 tipos de validade.")

    return min(points, 1.5), crit, notes


def assess_d5_presentation(args, ctx):
    """D5 — Apresentação e auditabilidade (peso 1.5)."""
    points = 0.0
    notes = []
    crit = []
    pkg = Path(args.package_dir)

    # 0.3 — HTML loads + has all toggles
    html = file_text(args.html) if args.html else ""
    has_toggles = all(t in html for t in
                       ["toggle-annotations", "toggle-fun", "toggle-dark", "toggle-collapse-all"])
    has_search = "id=\"q\"" in html
    has_d3 = "d3@7" in html or "d3.v7" in html
    if has_toggles and has_search and has_d3:
        points += 0.3
        crit.append(("0.3/0.3", "HTML interativo: 4 toggles + busca + D3.js"))
    else:
        miss = []
        if not has_toggles: miss.append("toggles")
        if not has_search: miss.append("busca")
        if not has_d3: miss.append("D3.js")
        crit.append((f"0.0/0.3", f"HTML interativo faltando: {', '.join(miss)}"))
        notes.append(f"Verificar template — {', '.join(miss)} ausente(s).")

    # 0.2 — all refs clickable with DOI/URL
    content = ctx.get("content") or {}
    refs = content.get("references", [])
    if refs:
        with_link = sum(1 for r in refs if r.get("doi") or r.get("url"))
        if with_link == len(refs):
            points += 0.2
            crit.append((f"0.2/0.2", f"Todas {len(refs)} referências com link"))
        else:
            partial = 0.2 * (with_link / len(refs))
            points += partial
            crit.append((f"{partial:.2f}/0.2", f"{with_link}/{len(refs)} refs com link"))
            notes.append(f"Adicionar DOI ou URL às {len(refs)-with_link} referências sem link.")

    # 0.2 — D3 charts: temporal + heatmap + PRISMA inline
    has_temporal = "chart-temporal" in html
    has_heatmap = "chart-qa-heatmap" in html
    has_prisma_inline = "<svg" in html and "PRISMA" in html
    score = 0.2 * sum([has_temporal, has_heatmap, has_prisma_inline]) / 3
    points += score
    miss = []
    if not has_temporal: miss.append("chart-temporal")
    if not has_heatmap: miss.append("chart-qa-heatmap")
    if not has_prisma_inline: miss.append("PRISMA inline")
    if not miss:
        crit.append(("0.2/0.2", "Gráficos D3 + PRISMA inline OK"))
    else:
        crit.append((f"{score:.2f}/0.2", f"Gráficos faltando: {', '.join(miss)}"))

    # 0.2 — package complete
    expected = ["manuscript.html", "protocol.md", "searches.json", "screening.csv",
                "quality-appraisal.csv", "extraction.csv", "prisma-flow.svg",
                "references.bib", "README.md", "ai-declaration.md",
                "venue-suggestions.md", "compliance-checklist.md"]
    present = [f for f in expected if (pkg / f).exists()]
    pct = len(present) / len(expected)
    score_pkg = 0.2 * pct
    points += score_pkg
    if pct == 1.0:
        crit.append((f"0.2/0.2", f"Pacote completo ({len(present)}/{len(expected)} artefatos)"))
    else:
        crit.append((f"{score_pkg:.2f}/0.2", f"Pacote incompleto: {len(present)}/{len(expected)}"))
        missing = [f for f in expected if not (pkg / f).exists()]
        notes.append(f"Gerar artefatos faltantes: {', '.join(missing)}.")

    # 0.2 — README has hashes + changelog
    readme = file_text(pkg / "README.md")
    has_hashes = "sha256" in readme.lower()
    has_changelog = bool(re.search(r"changelog|mudanças|changes", readme, re.I))
    if has_hashes and has_changelog:
        points += 0.2
        crit.append(("0.2/0.2", "README com hashes + changelog"))
    elif has_hashes or has_changelog:
        points += 0.1
        crit.append((f"0.1/0.2", f"README com {'hashes' if has_hashes else 'changelog'} apenas"))
        notes.append("Completar README.md com hashes SHA-256 e changelog.")
    else:
        crit.append(("0.0/0.2", "README incompleto"))
        notes.append("README.md precisa de hashes SHA-256 e changelog desde versão anterior.")

    # 0.2 — SemVer correct + visible in header AND footer
    version = ctx.get("version", "")
    if version:
        in_header = f"v{version}" in html[:8000]  # crude: top of HTML
        in_footer = f"v{version}" in html[-3000:]
        if in_header and in_footer:
            points += 0.2
            crit.append((f"0.2/0.2", f"v{version} no header e footer"))
        elif in_header or in_footer:
            points += 0.1
            crit.append((f"0.1/0.2", f"v{version} apenas em {'header' if in_header else 'footer'}"))
            notes.append("Versão SemVer deve aparecer tanto no header quanto no footer do HTML.")
        else:
            crit.append((f"0.0/0.2", "Versão não encontrada no HTML"))

    # 0.2 — "What this version is NOT" has ≥3 items
    not_items = content.get("not_this_version_items", [])
    if len(not_items) >= 3:
        points += 0.2
        crit.append((f"0.2/0.2", f"§09 com {len(not_items)} itens declarados"))
    elif len(not_items) >= 1:
        points += 0.1
        crit.append((f"0.1/0.2", f"§09 com apenas {len(not_items)} item(ns)"))
        notes.append(f"Adicionar mais itens em 'O que esta versão NÃO é' (alvo: ≥3, atual: {len(not_items)}).")
    else:
        crit.append(("0.0/0.2", "§09 vazia"))
        notes.append("Preencher 'O que esta versão NÃO é' com ≥3 limites declarados.")

    return min(points, 1.5), crit, notes


def check_eliminatorios(args, ctx):
    """Returns list of failed eliminatory criteria. Empty list = pass."""
    failed = []
    html = file_text(args.html) if args.html else ""
    content = ctx.get("content") or {}

    # IA listed as author?
    if re.search(r"(author|autor).{0,40}?(claude|gpt|gemini|chatgpt|llm)", html, re.I):
        failed.append("IA possivelmente listada como autora — verificação manual obrigatória.")

    # Declaration of AI use missing?
    if not (content.get("ai_declaration") or {}).get("tool"):
        failed.append("Declaração de uso de IA ausente ou sem ferramenta declarada.")

    # PRISMA flow absent
    if not (Path(args.package_dir) / "prisma-flow.svg").exists():
        failed.append("PRISMA flow diagram ausente.")

    # Quality appraisal absent
    qa = load_csv(args.qa)
    if not qa:
        failed.append("Quality appraisal ausente.")

    # < 3 bases searched
    searches = load_json(args.searches) if args.searches else None
    if searches:
        per_db = searches.get("per_database", searches if isinstance(searches, list) else [])
        if isinstance(per_db, list) and len(per_db) < 3:
            failed.append(f"Cobertura insuficiente: apenas {len(per_db)} bases consultadas (mínimo: 3).")

    return failed


def compute_bonus(args, ctx):
    """Up to +0.3 for bonifying criteria."""
    bonus = 0.0
    applied = []
    pkg = Path(args.package_dir)
    readme = file_text(pkg / "README.md")
    proto = file_text(pkg / "protocol.md")

    if re.search(r"zenodo.org/.{1,30}\d+", proto + readme):
        bonus += 0.1
        applied.append("Pré-registro Zenodo identificado (+0.1)")
    if re.search(r"snowball|wohlin", proto, re.I):
        bonus += 0.1
        applied.append("Snowballing executado (+0.1)")
    content = ctx.get("content") or {}
    venues = content.get("venues") or []
    if any("OA Diamond" in (v.get("access_model", "") or "") or
           "diamond" in (v.get("access_model", "") or "").lower() for v in venues):
        bonus += 0.1
        applied.append("Venue OA Diamond sugerido (+0.1)")

    return min(bonus, 0.3), applied


# ── main ────────────────────────────────────────────────────────────────────

def render_report(args, results, total, eliminatory, bonus_pts, bonus_applied,
                  recommendation):
    is_ptbr = (args.lang or "pt-BR").lower().startswith("pt")

    if is_ptbr:
        head = f"""# Avaliação automática — ignorantia v{args.version}

**Pacote:** ignorantia-{args.area_slug}-{args.topic_slug}-v{args.version}.zip
**Data da avaliação:** {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
**Avaliador:** ignorantia skill (avaliação automática; NÃO substitui revisão humana)
**Nota final:** **{total:.1f} / 10.0**
**Veículo-alvo recomendado:** {recommendation}

## Resumo executivo
"""
        section_titles = ["Notas por dimensão", "Bonificadores aplicados",
                          "Eliminatórios", "O QUE FALTA PARA NOTA 10.0",
                          "Próxima versão sugerida", "Disclaimer"]
        crit_severities = ["Crítico (bloqueia submissão a venue de elite)",
                            "Importante (recomendado antes de submeter)",
                            "Polimento (eleva qualidade marginal)"]
        dim_names = ["Rigor metodológico", "Compliance ético-legal",
                     "Qualidade do corpus", "Qualidade textual",
                     "Apresentação"]
    else:
        head = f"""# Automated assessment — ignorantia v{args.version}

**Package:** ignorantia-{args.area_slug}-{args.topic_slug}-v{args.version}.zip
**Assessment date:** {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
**Assessor:** ignorantia skill (automated; does NOT replace human peer review)
**Final score:** **{total:.1f} / 10.0**
**Recommended target venue:** {recommendation}

## Executive summary
"""
        section_titles = ["Per-dimension scores", "Applied bonuses",
                          "Eliminatory criteria", "WHAT'S MISSING FOR A 10.0",
                          "Suggested next version", "Disclaimer"]
        crit_severities = ["Critical (blocks elite-venue submission)",
                            "Important (recommended before submission)",
                            "Polish (marginal quality improvement)"]
        dim_names = ["Methodological rigor", "Ethical/legal compliance",
                     "Corpus quality", "Textual quality",
                     "Presentation"]

    # Executive summary
    if total >= 9.5:
        exec_summary = ("Manuscrito pronto para submissão a venue de elite com revisão menor."
                        if is_ptbr else "Manuscript ready for elite venue submission with minor revision.")
    elif total >= 8.5:
        exec_summary = ("Manuscrito quase pronto — algumas melhorias antes de submeter."
                        if is_ptbr else "Manuscript nearly ready — some improvements before submission.")
    elif total >= 7.0:
        exec_summary = ("Manuscrito aceitável — várias melhorias necessárias para venue de elite."
                        if is_ptbr else "Acceptable — several improvements needed for elite venue.")
    elif total >= 5.0:
        exec_summary = ("Manuscrito requer revisão substancial antes de submissão."
                        if is_ptbr else "Manuscript requires substantial revision before submission.")
    else:
        exec_summary = ("INACEITÁVEL para submissão. Critérios eliminatórios falharam ou pontuação muito baixa."
                        if is_ptbr else "UNACCEPTABLE for submission. Eliminatory criteria failed or score too low.")

    parts = [head, exec_summary, "\n## " + section_titles[0] + "\n"]

    # Per-dimension table
    parts.append("| Dim | Nome | Peso | Pontos | % |")
    parts.append("|---|---|---|---|---|")
    weights = [3.0, 2.0, 2.0, 1.5, 1.5]
    for i, (dim_pts, dim_crit, dim_notes) in enumerate(results):
        pct = (dim_pts / weights[i]) * 100 if weights[i] else 0
        parts.append(f"| D{i+1} | {dim_names[i]} | {weights[i]} | {dim_pts:.2f} | {pct:.0f}% |")
    parts.append(f"| **Total** | | **10.0** | **{total:.2f}** | **{total*10:.0f}%** |\n")

    # Detail per dimension
    for i, (dim_pts, dim_crit, dim_notes) in enumerate(results):
        parts.append(f"### D{i+1} — {dim_names[i]} ({dim_pts:.2f}/{weights[i]})\n")
        for label, desc in dim_crit:
            mark = "✅" if label.split("/")[0] == label.split("/")[1] else (
                "⚠️" if float(label.split("/")[0]) > 0 else "❌")
            parts.append(f"- {mark} **{label}** — {desc}")
        parts.append("")

    # Bonuses
    parts.append(f"## {section_titles[1]}\n")
    if bonus_applied:
        for b in bonus_applied:
            parts.append(f"- ✨ {b}")
        parts.append(f"\nTotal de bonificadores: +{bonus_pts:.1f}\n")
    else:
        parts.append("Nenhum bonificador aplicado.\n" if is_ptbr
                     else "No bonuses applied.\n")

    # Eliminatory
    parts.append(f"## {section_titles[2]}\n")
    if not eliminatory:
        parts.append("✅ Todos os critérios eliminatórios passaram.\n" if is_ptbr
                     else "✅ All eliminatory criteria passed.\n")
    else:
        for e in eliminatory:
            parts.append(f"- 🚨 {e}")
        if is_ptbr:
            parts.append("\n**ATENÇÃO:** Critérios eliminatórios falharam — nota máxima 5.0 aplicada.\n")
        else:
            parts.append("\n**WARNING:** Eliminatory criteria failed — max score 5.0 applied.\n")

    # WHAT'S MISSING — the most important section
    parts.append(f"## {section_titles[3]}\n")
    if is_ptbr:
        parts.append("Esta é a parte mais importante deste relatório. Lista priorizada de ações.\n")
    else:
        parts.append("This is the most important section. Prioritized action list.\n")

    all_notes = []
    for _, _, notes in results:
        all_notes.extend(notes)

    critical = [n for n in all_notes if "CRÍTICO" in n or "CRITICAL" in n]
    important = [n for n in all_notes if n not in critical and "ELIMINATÓRIO" not in n]
    if not critical and not important:
        parts.append(("Nada crítico identificado. Pequenos polimentos abaixo.\n"
                      if is_ptbr else "Nothing critical. Minor polish below.\n"))

    parts.append(f"### {crit_severities[0]}\n")
    if critical:
        for i, n in enumerate(critical, 1):
            parts.append(f"{i}. {n}")
    else:
        parts.append("Nenhum.\n" if is_ptbr else "None.\n")

    parts.append(f"\n### {crit_severities[1]}\n")
    if important:
        for i, n in enumerate(important, 1):
            parts.append(f"{i}. {n}")
    else:
        parts.append("Nenhum.\n" if is_ptbr else "None.\n")

    # Next version
    parts.append(f"\n## {section_titles[4]}\n")
    if eliminatory or critical:
        bump = "MAJOR ou MINOR (depende das mudanças)"
    elif important:
        bump = "MINOR (inclusão/exclusão sugerida)"
    else:
        bump = "PATCH (apenas polimento formal)"
    parts.append(f"Recomendação: bump **{bump}**.\n")

    # Disclaimer
    parts.append(f"\n## {section_titles[5]}\n")
    if is_ptbr:
        parts.append("Esta avaliação é gerada automaticamente pelo skill `ignorantia` "
                     "com base na rubrica documentada em `references/quality-rubric.md`. "
                     "Serve como autocheck antes da submissão. A decisão editorial final "
                     "é dos revisores humanos do periódico-alvo. A nota 10.0 não garante "
                     "aceitação — significa apenas que o manuscrito atende aos requisitos "
                     "formais e metodológicos para ser ELEGÍVEL a um venue de elite.\n")
    else:
        parts.append("This assessment is generated automatically by the `ignorantia` skill "
                     "based on the rubric in `references/quality-rubric.md`. It serves as a "
                     "self-check before submission. Editorial decisions are made by human "
                     "reviewers at the target journal. A 10.0 does not guarantee acceptance — "
                     "it means the manuscript meets the formal and methodological requirements "
                     "to be ELIGIBLE for an elite venue.\n")

    return "\n".join(parts)


def map_to_venue(score, is_ptbr):
    if score >= 9.5:
        return ("Qualis A1 (Educ@, SciELO BR top); pronto para internacionalizar a Q1"
                if is_ptbr else
                "Top elite venue: Nature flagship, Lancet, Cell, IEEE Trans Q1, ACM Trans Q1, AAAS")
    if score >= 8.5:
        return ("Qualis A2 ou A3" if is_ptbr else "Q1-Q2 international, secondary elite venues")
    if score >= 7.5:
        return "Qualis A4 ou B1" if is_ptbr else "Q2-Q3 international"
    if score >= 6.5:
        return "Qualis B2-B3" if is_ptbr else "Q3-Q4 international"
    if score >= 5.0:
        return "Qualis B4-B5" if is_ptbr else "Generic OA journals"
    return ("NÃO submeter — revisar e gerar nova versão"
            if is_ptbr else "DO NOT submit — revise and generate new version")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-dir", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--searches", default=None)
    ap.add_argument("--html", default=None)
    ap.add_argument("--version", required=True)
    ap.add_argument("--topic-slug", required=True)
    ap.add_argument("--area-slug", default="area")
    ap.add_argument("--area", default="")
    ap.add_argument("--lang", default="pt-BR")
    ap.add_argument("--is-se-cs", action="store_true",
                    help="Tema é Software Engineering / Computer Science")
    ap.add_argument("--is-health", action="store_true",
                    help="Tema é saúde / medicina / enfermagem")
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--gate-min-score",
        type=float,
        default=_DEFAULT_GATE_MIN_SCORE,
        help=(
            f"Minimum score required to pass the gate (default: "
            f"{_DEFAULT_GATE_MIN_SCORE}). Below this, the script exits "
            f"non-zero. Eliminatórios always fail the gate regardless."
        ),
    )
    ap.add_argument(
        "--no-gate",
        action="store_true",
        help=(
            "Disable the exit-code gate. Report and JSON sidecar are still "
            "written, but the script exits 0 even on assessment failure. "
            "Use only for triage / partial-package debugging."
        ),
    )
    args = ap.parse_args()

    content = load_json(args.content) or {}
    ctx = {
        "content": content,
        "version": args.version,
        "is_ptbr": (args.lang or "pt-BR").lower().startswith("pt"),
        "is_se_cs": args.is_se_cs,
        "is_health": args.is_health,
    }

    d1 = assess_d1_methodology(args, ctx)
    d2 = assess_d2_compliance(args, ctx)
    d3 = assess_d3_corpus(args, ctx)
    d4 = assess_d4_textual(args, ctx)
    d5 = assess_d5_presentation(args, ctx)

    raw_total = d1[0] + d2[0] + d3[0] + d4[0] + d5[0]

    eliminatory = check_eliminatorios(args, ctx)
    bonus_pts, bonus_applied = compute_bonus(args, ctx)

    if eliminatory:
        total = min(raw_total + bonus_pts, 5.0)
    else:
        total = min(raw_total + bonus_pts, 10.0)

    # Round DOWN to one decimal — never round up
    total = int(total * 10) / 10.0

    recommendation = map_to_venue(total, ctx["is_ptbr"])

    report = render_report(args,
                           [d1, d2, d3, d4, d5],
                           total, eliminatory, bonus_pts, bonus_applied,
                           recommendation)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"Wrote {args.out}  (score: {total:.1f}/10.0)")

    # Gate evaluation (Fix 9): write JSON sidecar and decide exit code.
    gate_failed_eliminatory = bool(eliminatory)
    gate_failed_score = total < args.gate_min_score
    gate_passed = not (gate_failed_eliminatory or gate_failed_score)

    sidecar_path = Path(args.package_dir) / _GATE_SIDECAR_FILENAME
    sidecar_path.write_text(
        json.dumps(
            {
                "passed": gate_passed,
                "score": total,
                "min_score": args.gate_min_score,
                "eliminatory_count": len(eliminatory),
                "eliminatory_failed": gate_failed_eliminatory,
                "score_failed": gate_failed_score,
                "report_path": str(Path(args.out).resolve()),
                "version": args.version,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {sidecar_path}  (gate: {'PASS' if gate_passed else 'FAIL'})")

    if not gate_passed and not args.no_gate:
        reasons = []
        if gate_failed_eliminatory:
            reasons.append(f"{len(eliminatory)} eliminatório(s)")
        if gate_failed_score:
            reasons.append(f"score {total:.1f} < {args.gate_min_score:.1f}")
        print(
            f"GATE FAILED: {' + '.join(reasons)}. Pacote NÃO deve ser finalizado.",
            file=sys.stderr,
        )
        sys.exit(_GATE_EXIT_CODE)

    return total


if __name__ == "__main__":
    main()
