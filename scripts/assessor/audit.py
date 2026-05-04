"""
ignorantia.assessor.audit — Detectores forenses automáticos (Rodada F).

Sete detectores que rodam offline sobre o conteúdo + referências do manuscrito,
identificando problemas de integridade verificáveis:

  A1 — DOI malformado            (formato 10.NNNN/...)
  A2 — Citações órfãs            ([N] no texto sem ref correspondente)
  A3 — Referências nunca citadas (refs no .bib que não aparecem como [N])
  A4 — IDs com gaps              (numeração não-sequencial 1..N)
  A5 — DOIs duplicados           (mesmo DOI em refs diferentes)
  A6 — DOI/venue inconsistente   (prefixo DOI vs venue declarado)
  A7 — Refs sem rastreabilidade  (sem doi/url/isbn)

Cada detector retorna lista de AuditFinding com severidade
(info/warning/error). Findings agregados são renderizados na seção
"Auditoria forense" do tab Auditoria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .helpers import strip_html


# ── Estruturas de dados ──────────────────────────────────────────────


@dataclass
class AuditFinding:
    """Achado de auditoria automática."""

    detector: str  # 'A1' .. 'A7'
    severity: str  # 'info' | 'warning' | 'error'
    message: str  # mensagem curta para humano
    evidence: str = ""  # trecho/ref problemática


# ── Detectores ───────────────────────────────────────────────────────


# Mapeamento prefixo DOI → publisher/venue conhecido. Lista incompleta —
# adicionar conforme necessário. Casos óbvios apenas (sem ambiguidade).
DOI_PREFIX_TO_PUBLISHER = {
    "10.1136": "BMJ",
    "10.1056": "NEJM",
    "10.1001": "JAMA Network",
    "10.1016": "Elsevier",
    "10.1145": "ACM",
    "10.1109": "IEEE",
    "10.1080": "Taylor & Francis",
    "10.1037": "APA",
    "10.1038": "Nature",
    "10.1126": "Science / AAAS",
    "10.1007": "Springer",
    "10.1002": "Wiley",
    "10.1017": "Cambridge",
    "10.1093": "Oxford",
    "10.1146": "Annual Reviews",
    "10.1590": "SciELO Brazil",
    "10.21813": "DBLP / SBC",
    "10.5753": "SBC",
}

# Imprints conhecidos: venues publicados pelo publisher mas sob outro nome.
# Usado pelo detector A6 para evitar falsos positivos. Cada entrada mapeia
# (prefixo_doi → conjunto de palavras-chave de venues legítimos do publisher).
# Exemplo: 10.1093 (Oxford) também publica para Gerontological Society of America
# (Innovation in Aging, The Gerontologist, etc.). Não é mismatch.
KNOWN_IMPRINTS: dict[str, set[str]] = {
    "10.1093": {  # Oxford UP — também publica para sociedades:
        "innovation", "aging", "gerontologist", "geront",  # GSA (Gerontology)
        "monthly notices",  # Royal Astronomical
        "icesjms", "ices journal", "marine science",  # ICES
        "european heart", "europace",  # Society of Cardiology
        "sleep", "schizophrenia",
        "brain", "human reproduction",
    },
    "10.1038": {  # Nature Portfolio — múltiplos imprints:
        "scientific reports", "nature communications", "nature physics",
        "nature medicine", "nature human behaviour", "nature genetics",
        "communications biology", "nature methods", "nature climate",
    },
    "10.1007": {  # Springer — diversos imprints:
        "computational statistics", "methodology", "soft computing",
        "ai & society", "minds and machines", "neural processing",
        "psychometrika", "behavior research methods",
    },
    "10.1002": {  # Wiley — diversos imprints:
        "journal of biomedical informatics", "advanced", "human brain mapping",
        "cochrane database",  # Wiley publica Cochrane
    },
    "10.1080": {  # Taylor & Francis — diversos:
        "educational gerontology", "clinical gerontologist",
        "behaviour & information technology",
    },
    "10.3389": {  # Frontiers — flagship + ~80 imprints temáticos:
        "frontiers in",  # qualquer "Frontiers in X"
    },
    "10.2196": {  # JMIR Publications — flagship + JMIR-prefixed:
        "jmir", "j med internet res", "iproc",
    },
    "10.1177": {  # SAGE — diversos imprints:
        "digital health", "journal of aging", "research on aging",
    },
}


def detect_doi_malformed(refs: list[dict]) -> list[AuditFinding]:
    """A1 — DOI no formato `10.NNNN/...` (4-9 dígitos no prefixo).

    DOI válido: 10.1145/3290605.3300456
    DOI inválido: 10.x/foo, 10/abc, 10.1145, http://..., etc.
    """
    findings = []
    doi_re = re.compile(r"^10\.\d{4,9}/[^\s]+$")
    for ref in refs:
        doi = (ref.get("doi") or "").strip()
        if not doi:
            continue  # ausência de DOI é tratada por A7
        if not doi_re.match(doi):
            findings.append(
                AuditFinding(
                    detector="A1",
                    severity="error",
                    message=f"Ref [{ref.get('id', '?')}]: DOI malformado.",
                    evidence=f"DOI declarado: '{doi}' (esperado: '10.NNNN/...')",
                )
            )
    return findings


def detect_orphan_citations(content: dict, refs: list[dict]) -> list[AuditFinding]:
    """A2 — Citações [N] no texto onde N não existe na lista de refs.

    Exemplo: texto cita [17] mas só há 16 refs → órfão.
    """
    findings = []
    valid_ids = {ref.get("id") for ref in refs if ref.get("id") is not None}
    if not valid_ids:
        return findings  # nada a verificar

    # Coletar todo o texto narrativo
    sections = [
        "abstract_html",
        "introduction_html",
        "background_html",
        "methodology_html",
        "synthesis_html",
        "discussion_html",
        "threats_html",
        "conclusion_html",
    ]
    full_text = " ".join(strip_html(content.get(s) or "") for s in sections)

    # Match [N] simples (e [N,M] com vírgula+espaço)
    cited = set()
    for m in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", full_text):
        for n in m.group(1).split(","):
            try:
                cited.add(int(n.strip()))
            except ValueError:
                pass

    for cit in sorted(cited):
        if cit not in valid_ids:
            findings.append(
                AuditFinding(
                    detector="A2",
                    severity="error",
                    message=f"Citação [{cit}] aparece no texto mas não existe na lista de referências.",
                    evidence=f"Refs disponíveis: 1..{max(valid_ids) if valid_ids else '?'}",
                )
            )
    return findings


def detect_uncited_references(content: dict, refs: list[dict]) -> list[AuditFinding]:
    """A3 — Referências da bibliografia que nunca aparecem como [N] no texto.

    Reportado como warning (não error): refs decorativas são comuns mas devem
    ser revisadas — pode ser ref esquecida após corte de seção.
    """
    findings = []
    sections = [
        "abstract_html",
        "introduction_html",
        "background_html",
        "methodology_html",
        "synthesis_html",
        "discussion_html",
        "threats_html",
        "conclusion_html",
    ]
    full_text = " ".join(strip_html(content.get(s) or "") for s in sections)

    cited = set()
    for m in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", full_text):
        for n in m.group(1).split(","):
            try:
                cited.add(int(n.strip()))
            except ValueError:
                pass

    for ref in refs:
        rid = ref.get("id")
        if rid is None:
            continue
        if rid not in cited:
            doi = ref.get("doi", "—")
            venue = ref.get("venue", "—")
            findings.append(
                AuditFinding(
                    detector="A3",
                    severity="warning",
                    message=f"Ref [{rid}] está na bibliografia mas nunca é citada no texto.",
                    evidence=f"Venue: {venue} · DOI: {doi}",
                )
            )
    return findings


def detect_id_gaps(refs: list[dict]) -> list[AuditFinding]:
    """A4 — IDs de referência devem ser sequenciais 1..N sem gaps."""
    findings = []
    ids = [ref.get("id") for ref in refs if ref.get("id") is not None]
    if not ids:
        return findings

    sorted_ids = sorted(ids)
    expected = list(range(1, len(sorted_ids) + 1))
    if sorted_ids != expected:
        # Identificar onde está o gap
        missing = sorted(set(expected) - set(sorted_ids))
        extra = sorted(set(sorted_ids) - set(expected))
        msg_parts = []
        if missing:
            msg_parts.append(f"IDs ausentes: {missing}")
        if extra:
            msg_parts.append(f"IDs inesperados: {extra}")
        findings.append(
            AuditFinding(
                detector="A4",
                severity="warning",
                message=f"Numeração de refs não-sequencial (esperado: 1..{len(sorted_ids)}).",
                evidence="; ".join(msg_parts) if msg_parts else f"IDs: {sorted_ids}",
            )
        )
    return findings


def detect_duplicate_dois(refs: list[dict]) -> list[AuditFinding]:
    """A5 — DOIs idênticos em refs diferentes."""
    findings = []
    seen: dict[str, list[Any]] = {}
    for ref in refs:
        doi = (ref.get("doi") or "").strip().lower()
        if not doi:
            continue
        seen.setdefault(doi, []).append(ref.get("id", "?"))

    for doi, ids in seen.items():
        if len(ids) > 1:
            findings.append(
                AuditFinding(
                    detector="A5",
                    severity="error",
                    message=f"DOI duplicado: aparece em refs {ids}.",
                    evidence=f"DOI: {doi}",
                )
            )
    return findings


def detect_doi_venue_mismatch(refs: list[dict]) -> list[AuditFinding]:
    """A6 — Prefixo DOI conhecido conflita com venue declarado.

    Exemplo: DOI '10.1136/bmj.n71' (BMJ) com venue declarado 'ACM CHI'
    é uma inconsistência clara.

    Refinamento (Rodada I): considera imprints conhecidos do publisher
    (Oxford ↔ GSA Innovation in Aging, Springer ↔ vários imprints, etc.)
    para evitar falsos positivos.
    """
    findings = []
    for ref in refs:
        doi = (ref.get("doi") or "").strip()
        venue = (ref.get("venue") or "").strip()
        if not doi or not venue:
            continue
        m = re.match(r"^(10\.\d{4,9})/", doi)
        if not m:
            continue
        prefix = m.group(1)
        expected_publisher = DOI_PREFIX_TO_PUBLISHER.get(prefix)
        if not expected_publisher:
            continue

        venue_lower = venue.lower()

        # Primeiro: verificar se venue é um imprint conhecido do publisher
        imprint_keywords = KNOWN_IMPRINTS.get(prefix, set())
        if any(kw in venue_lower for kw in imprint_keywords):
            continue  # imprint legítimo, não é mismatch

        # Verificar match com publisher direto
        publisher_words = {
            w.lower()
            for w in re.split(r"\s+|/|&", expected_publisher)
            if len(w) >= 3
        }
        if any(w in venue_lower for w in publisher_words):
            continue  # publisher direto match

        # Caso contrário, é mismatch real
        findings.append(
            AuditFinding(
                detector="A6",
                severity="warning",
                message=(
                    f"Ref [{ref.get('id', '?')}]: prefixo DOI '{prefix}' "
                    f"associado a {expected_publisher}, mas venue declarado é '{venue}'."
                ),
                evidence=f"DOI: {doi} · Venue: {venue}",
            )
        )
    return findings


def detect_untraceable_refs(refs: list[dict]) -> list[AuditFinding]:
    """A7 — Refs sem qualquer identificador rastreável (doi/url/isbn).

    Sem DOI/URL/ISBN, leitor não tem como localizar a fonte. É um ponto de
    fragilidade epistêmica — reportado como warning.
    """
    findings = []
    for ref in refs:
        doi = ref.get("doi")
        url = ref.get("url")
        isbn = ref.get("isbn")
        if not (doi or url or isbn):
            findings.append(
                AuditFinding(
                    detector="A7",
                    severity="warning",
                    message=f"Ref [{ref.get('id', '?')}]: sem DOI, URL ou ISBN — não rastreável.",
                    evidence=f"Venue: {ref.get('venue', '—')}",
                )
            )
    return findings


# ── Orquestrador ─────────────────────────────────────────────────────


def run_audit(content: dict, is_minimal_package: bool = False) -> list[AuditFinding]:
    """Roda todos os 7 detectores e retorna findings agregados.

    Ordem de severidade: error primeiro, depois warning, depois info.

    Args:
        content: dict do content.json
        is_minimal_package: se True, A7 (refs sem DOI/URL/ISBN) é rebaixado
            para severidade 'info' com mensagem "esperado em modo pacote
            mínimo". Outros detectores permanecem inalterados.
    """
    refs = content.get("references", []) or []
    findings = []
    findings.extend(detect_doi_malformed(refs))
    findings.extend(detect_orphan_citations(content, refs))
    findings.extend(detect_uncited_references(content, refs))
    findings.extend(detect_id_gaps(refs))
    findings.extend(detect_duplicate_dois(refs))
    findings.extend(detect_doi_venue_mismatch(refs))

    a7_findings = detect_untraceable_refs(refs)
    if is_minimal_package and a7_findings:
        # Em modo pacote mínimo, refs sem DOI são esperadas (placeholders
        # genéricos do conversor SLR→pacote). Rebaixar para info com nota.
        for f in a7_findings:
            f.severity = "info"
            f.message = (
                "[modo pacote mínimo] " + f.message
                + " — esperado em modo pacote mínimo (placeholders do conversor)."
            )
    findings.extend(a7_findings)

    # Ordenar por severidade (error > warning > info), depois por detector
    sev_order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (sev_order.get(f.severity, 9), f.detector))
    return findings


def summarize_audit(findings: list[AuditFinding]) -> dict:
    """Resumo agregado para uso no relatório."""
    counts = {"error": 0, "warning": 0, "info": 0}
    by_detector: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
        by_detector[f.detector] = by_detector.get(f.detector, 0) + 1
    return {
        "total": len(findings),
        "by_severity": counts,
        "by_detector": by_detector,
        "findings": [
            {
                "detector": f.detector,
                "severity": f.severity,
                "message": f.message,
                "evidence": f.evidence,
            }
            for f in findings
        ],
    }
