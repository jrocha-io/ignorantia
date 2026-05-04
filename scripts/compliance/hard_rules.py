"""
Stage 2: Hard Requirements Checking.

Verifica requisitos verificáveis automaticamente do perfil do venue
contra o ManuscriptDocument parseado. Cada rule class produz um CheckResult.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any

from .parse import ManuscriptDocument


@dataclass
class CheckResult:
    rule_id: str
    rule_name: str
    passed: bool
    severity: str = "minor"  # blocking | major | minor
    evidence: str = ""
    expected: str = ""
    actual: str = ""
    fix_cost_estimate: str = "low"  # low | medium | high
    extra: dict[str, Any] = field(default_factory=dict)


# ---------- Helpers ----------

def _resolve_length_max(length_cfg: dict, review_type: str | None) -> int | None:
    """Trata override por review_type_specific."""
    if not length_cfg:
        return None
    rts = length_cfg.get("review_type_specific")
    if rts and review_type and review_type in rts:
        return rts[review_type].get("max", length_cfg.get("max"))
    return length_cfg.get("max")


# ---------- Rule classes ----------

def check_length(doc: ManuscriptDocument, profile: dict, review_type: str | None = None) -> CheckResult:
    cfg = profile.get("hard_requirements", {}).get("length", {}) or {}
    if not cfg:
        return CheckResult("hard.length", "Length", True, "minor", "No length requirement",
                           expected="not_specified")
    unit = cfg.get("unit", "words")
    max_value = _resolve_length_max(cfg, review_type)
    min_value = cfg.get("min")
    if unit == "words":
        actual = doc.word_count
    elif unit == "characters_with_spaces":
        actual = doc.char_count_with_spaces
    else:
        actual = doc.word_count  # fallback for "pages" — pre-parse converted
    if max_value is not None and actual > max_value:
        return CheckResult(
            "hard.length", "Length within max", False, "blocking",
            evidence=f"actual {actual} {unit} > max {max_value}",
            expected=f"≤ {max_value} {unit}", actual=str(actual),
            fix_cost_estimate="high",
        )
    if min_value is not None and actual < min_value:
        return CheckResult(
            "hard.length", "Length above min", False, "blocking",
            evidence=f"actual {actual} {unit} < min {min_value}",
            expected=f"≥ {min_value} {unit}", actual=str(actual),
            fix_cost_estimate="high",
        )
    return CheckResult("hard.length", "Length", True, "minor",
                       evidence=f"{actual} {unit}", expected=f"min {min_value or 0}, max {max_value or '∞'}",
                       actual=str(actual))


def check_abstract(doc: ManuscriptDocument, profile: dict) -> CheckResult:
    cfg = profile.get("hard_requirements", {}).get("abstract", {}) or {}
    if not cfg:
        return CheckResult("hard.abstract", "Abstract", True, "minor", "Not specified")
    if not doc.abstract.strip():
        return CheckResult(
            "hard.abstract", "Abstract present", False, "blocking",
            evidence="No abstract section detected", expected="present",
            fix_cost_estimate="medium",
        )
    abs_words = len(re.findall(r"\b\w+\b", doc.abstract))
    abs_chars = len(doc.abstract)
    max_w = cfg.get("max_words")
    max_c = cfg.get("max_chars")
    if max_w and abs_words > max_w:
        return CheckResult("hard.abstract", "Abstract length (words)", False, "major",
                           evidence=f"{abs_words} > {max_w}", expected=f"≤ {max_w} words",
                           actual=str(abs_words), fix_cost_estimate="medium")
    if max_c and abs_chars > max_c:
        return CheckResult("hard.abstract", "Abstract length (chars)", False, "major",
                           evidence=f"{abs_chars} > {max_c}", expected=f"≤ {max_c} chars",
                           actual=str(abs_chars), fix_cost_estimate="medium")
    if cfg.get("structured"):
        headings = cfg.get("structure_headings", [])
        text_low = doc.abstract.lower()
        missing = [h for h in headings if h.lower() not in text_low]
        if missing:
            return CheckResult("hard.abstract", "Abstract structured", False, "major",
                               evidence=f"missing structured headings: {missing}",
                               expected=str(headings), fix_cost_estimate="low")
    return CheckResult("hard.abstract", "Abstract", True, "minor",
                       evidence=f"{abs_words} words / {abs_chars} chars")


def check_title(doc: ManuscriptDocument, profile: dict) -> CheckResult:
    cfg = profile.get("hard_requirements", {}).get("title", {}) or {}
    if not cfg or not cfg.get("max_words"):
        return CheckResult("hard.title", "Title", True, "minor", "Not specified")
    title_words = len(re.findall(r"\b\w+\b", doc.title))
    if title_words > cfg["max_words"]:
        return CheckResult("hard.title", "Title length", False, "major",
                           evidence=f"{title_words} > {cfg['max_words']}",
                           expected=f"≤ {cfg['max_words']} words", actual=str(title_words),
                           fix_cost_estimate="low")
    return CheckResult("hard.title", "Title", True, "minor",
                       evidence=f"{title_words} words")


def check_citation_style(doc: ManuscriptDocument, profile: dict) -> CheckResult:
    cfg = profile.get("hard_requirements", {}).get("citation_style", {}) or {}
    expected_format = cfg.get("format")
    if not expected_format:
        return CheckResult("hard.citation_style", "Citation style", True, "minor", "Not specified")
    text = doc.raw_text
    # Detecções heurísticas (mesmas de v1.x):
    #   IEEE/Vancouver: [1], [2-5]
    #   Vancouver superscript: marcadores especiais
    #   APA-7: (Author, 2023) ou (Author et al., 2023)
    #   ABNT: (AUTOR, 2023) (autor caixa-alta)
    detected = "unknown"
    if re.search(r"\[\d+(?:[\-\u2013,\s\d]*)\]", text):
        detected = "ieee_or_vancouver"
    if re.search(r"\([A-Z][a-zçãõéáíóú]+,\s+\d{4}", text):
        detected = "apa-7"
    if re.search(r"\([A-Z]{2,}[A-Z\s,]*,\s+\d{4}", text):
        detected = "abnt-nbr-6023"
    # Mapeamento simples — falso negativo aceitável (rule não pode falsificar pass):
    style_groups = {
        "ieee": {"ieee_or_vancouver"},
        "vancouver": {"ieee_or_vancouver"},
        "vancouver_superscript": {"ieee_or_vancouver"},
        "ama": {"ieee_or_vancouver"},
        "apa-7": {"apa-7"},
        "abnt-nbr-6023": {"abnt-nbr-6023"},
        "harvard": {"apa-7"},
        "chicago": {"apa-7"},
    }
    accepted = style_groups.get(expected_format, set())
    passed = detected in accepted
    return CheckResult(
        "hard.citation_style",
        f"Citation style ({expected_format})",
        passed,
        "major" if not passed else "minor",
        evidence=f"detected={detected}",
        expected=expected_format, actual=detected,
        fix_cost_estimate="medium",
    )


def check_mandatory_declarations(doc: ManuscriptDocument, profile: dict) -> list[CheckResult]:
    decls_cfg = profile.get("hard_requirements", {}).get("mandatory_declarations", []) or []
    results: list[CheckResult] = []
    for d in decls_cfg:
        decl_id = d["id"]
        severity = d.get("severity", "major")
        anchors = d.get("detection_anchors", [])
        # Procurar primeiro nas declarations já parseadas
        if decl_id in doc.declarations:
            results.append(CheckResult(
                f"hard.declaration.{decl_id}", f"Declaration: {decl_id}",
                True, severity,
                evidence=doc.declarations[decl_id][:120],
            ))
            continue
        # Procurar via âncoras adicionais
        if anchors:
            text_low = doc.raw_text.lower()
            found = any(re.search(a, text_low, flags=re.IGNORECASE) for a in anchors)
            if found:
                results.append(CheckResult(
                    f"hard.declaration.{decl_id}", f"Declaration: {decl_id}",
                    True, severity,
                    evidence="anchor matched",
                ))
                continue
        # Não encontrada
        results.append(CheckResult(
            f"hard.declaration.{decl_id}", f"Declaration: {decl_id}",
            False, severity,
            evidence="missing", expected="present",
            fix_cost_estimate="low",
        ))
    return results


def check_orcid(doc: ManuscriptDocument, profile: dict) -> CheckResult:
    auth = profile.get("hard_requirements", {}).get("authorship", {}) or {}
    requirement = auth.get("orcid_required", "none")
    if requirement == "none":
        return CheckResult("hard.orcid", "ORCID", True, "minor", "Not required")
    orcid_count = len(re.findall(r"\d{4}-\d{4}-\d{4}-\d{3}[\dXx]", doc.raw_text))
    if requirement in ("all", "corresponding_only"):
        passed = orcid_count >= 1
        sev = "major" if requirement == "corresponding_only" else "blocking"
        if not passed:
            sev = "blocking"
        return CheckResult(
            "hard.orcid", f"ORCID ({requirement})",
            passed, sev,
            evidence=f"orcid_ids_found={orcid_count}",
            expected=requirement, actual=str(orcid_count),
            fix_cost_estimate="low",
        )
    return CheckResult("hard.orcid", "ORCID", True, "minor", "")


def check_registration(doc: ManuscriptDocument, profile: dict) -> CheckResult:
    reg = profile.get("hard_requirements", {}).get("registration", {}) or {}
    prospero_required = reg.get("prospero_required", False)
    osf_acceptable = reg.get("osf_acceptable", False)
    has_prospero = "prospero_registration" in doc.declarations
    has_osf = "preregistration_link" in doc.declarations
    if prospero_required:
        if has_prospero:
            return CheckResult("hard.registration", "Pre-registration (PROSPERO)", True, "blocking",
                               evidence=doc.declarations.get("prospero_registration", ""))
        if osf_acceptable and has_osf:
            return CheckResult("hard.registration", "Pre-registration (OSF accepted)", True, "blocking",
                               evidence=doc.declarations.get("preregistration_link", ""))
        return CheckResult("hard.registration", "Pre-registration", False, "blocking",
                           evidence="No PROSPERO/OSF id found", expected="PROSPERO or OSF",
                           fix_cost_estimate="high")
    # not strictly required
    if has_prospero or has_osf:
        return CheckResult("hard.registration", "Pre-registration (optional)", True, "minor",
                           evidence="present")
    return CheckResult("hard.registration", "Pre-registration (optional)", True, "minor",
                       evidence="not required")


def check_language(doc: ManuscriptDocument, profile: dict) -> CheckResult:
    accepted = profile.get("metadata", {}).get("language_acceptance", []) or []
    if not accepted:
        return CheckResult("hard.language", "Language", True, "minor", "Not specified")
    detected = doc.detected_language
    if detected == "unknown":
        return CheckResult("hard.language", "Language", True, "minor",
                           evidence="detection inconclusive")
    if detected not in accepted:
        return CheckResult(
            "hard.language", "Language match", False, "blocking",
            evidence=f"detected={detected}", expected=str(accepted), actual=detected,
            fix_cost_estimate="high",
        )
    return CheckResult("hard.language", "Language", True, "minor",
                       evidence=f"detected={detected}")


# ---------- Aggregator of Stage 2 ----------

def run_hard_requirements(doc: ManuscriptDocument, profile: dict,
                          review_type: str | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.append(check_length(doc, profile, review_type))
    results.append(check_abstract(doc, profile))
    results.append(check_title(doc, profile))
    results.append(check_citation_style(doc, profile))
    results.extend(check_mandatory_declarations(doc, profile))
    results.append(check_orcid(doc, profile))
    results.append(check_registration(doc, profile))
    results.append(check_language(doc, profile))
    return results
