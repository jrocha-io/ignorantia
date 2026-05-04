"""
ComplianceEngine — orquestrador dos 7 estágios.

Stage 5: Aggregation (pesos por dimensão).
Stage 6: Gap Prioritization.
Stage 7: Multi-Venue Ranking.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .parse import ManuscriptDocument, parse_manuscript
from .hard_rules import CheckResult, run_hard_requirements
from .guidelines import run_all_guidelines
from .scope import compute_scope_score, ScopeScore


PROFILES_DIR = Path(__file__).resolve().parent.parent.parent / "references" / "profiles"


# ---------- Pesos da Stage 5 ----------

DIMENSION_WEIGHTS = {
    "structural": 0.25,      # length, abstract, title, mandatory_sections
    "reporting": 0.30,       # guideline items
    "declarations": 0.15,    # mandatory_declarations
    "citation_style": 0.10,
    "registration": 0.10,
    "scope": 0.10,
}


@dataclass
class DimensionScore:
    name: str
    score: float
    label: str
    failed_checks: list[dict] = field(default_factory=list)


@dataclass
class Gap:
    rule_id: str
    description: str
    severity: str
    fix_cost: str
    priority: float
    suggested_action: str = ""


@dataclass
class VenueAssessment:
    venue_id: str
    venue_name: str
    aggregate_score: float
    dimensions: dict[str, DimensionScore]
    gaps_prioritized: list[Gap]
    needs_human_review: list[dict]
    review_type_evaluated: str
    fallback_tier: int = 1
    """Tier OA-first (1=diamond default, 2=APC modesto declarado, 3=hybrid alto-custo/subscription).
    Default 1 mantém compatibilidade com perfis pré-v2.2.2 que não declaram tier."""


@dataclass
class ComplianceReport:
    manuscript_id: str
    primary_venue: VenueAssessment
    alternative_venues: list[VenueAssessment]
    timestamp_iso8601: str
    feedback_summary_pt: str
    feedback_summary_en: str

    def to_json(self, **kwargs) -> str:
        def _ser(o: Any) -> Any:
            if hasattr(o, "__dict__"):
                return o.__dict__
            return str(o)
        return json.dumps(asdict(self), default=_ser, ensure_ascii=False, **kwargs)


# ---------- Helpers de classificação ----------

def _classify_check_dimension(rule_id: str) -> str:
    if rule_id.startswith("hard.length") or rule_id.startswith("hard.abstract") or \
       rule_id.startswith("hard.title"):
        return "structural"
    if rule_id.startswith("guideline."):
        return "reporting"
    if rule_id.startswith("hard.declaration") or rule_id.startswith("hard.orcid"):
        return "declarations"
    if rule_id.startswith("hard.citation_style"):
        return "citation_style"
    if rule_id.startswith("hard.registration"):
        return "registration"
    if rule_id.startswith("hard.language"):
        return "structural"
    return "structural"


def _score_for_dimension(checks: list[CheckResult], dim: str) -> tuple[float, list[dict]]:
    if not checks:
        return 1.0, []
    total = 0.0
    weight_sum = 0.0
    failed: list[dict] = []
    for c in checks:
        sev = c.severity
        weight = {"blocking": 4.0, "major": 2.0, "minor": 1.0}.get(sev, 1.0)
        weight_sum += weight
        if c.passed:
            total += weight
        else:
            failed.append({
                "rule_id": c.rule_id, "rule_name": c.rule_name, "severity": sev,
                "evidence": c.evidence, "expected": c.expected, "actual": c.actual,
            })
    score = total / weight_sum if weight_sum else 1.0
    return round(score, 4), failed


def _label_for_score(score: float) -> str:
    if score >= 0.95:
        return "Excelente"
    if score >= 0.80:
        return "Bom"
    if score >= 0.60:
        return "Aceitável"
    if score >= 0.40:
        return "Atenção"
    return "Bloqueante"


def _priority_score(check: CheckResult) -> float:
    sev_weight = {"blocking": 1.0, "major": 0.6, "minor": 0.2}.get(check.severity, 0.2)
    cost_weight = {"low": 1.0, "medium": 0.5, "high": 0.2}.get(check.fix_cost_estimate, 0.5)
    # Priority = 0.5 * severity + 0.3 * venue_weight (assumido 1.0) + 0.2 / fix_cost⁻¹
    priority = 0.5 * sev_weight + 0.3 * 1.0 + 0.2 * cost_weight
    return round(min(priority, 1.0), 3)


def _suggested_action(check: CheckResult) -> str:
    if "registration" in check.rule_id:
        return "Registrar protocolo no PROSPERO ou OSF antes de submeter."
    if "declaration" in check.rule_id:
        decl = check.rule_id.split(".")[-1]
        return f"Adicionar seção/declaração: {decl}."
    if "length" in check.rule_id:
        return f"Ajustar comprimento (atual {check.actual}, esperado {check.expected})."
    if "abstract" in check.rule_id:
        return "Revisar resumo conforme requisitos."
    if "citation_style" in check.rule_id:
        return f"Converter referências para o formato {check.expected}."
    if "guideline." in check.rule_id:
        return "Revisar item de reporting guideline (verificação humana recomendada)."
    if "language" in check.rule_id:
        return "Idioma do manuscrito não é aceito pelo venue; traduzir."
    return "Revisar conforme evidência."


# ---------- Engine principal ----------

class VenueComplianceEngine:
    """Engine de compliance editorial determinístico para SLRs.

    Uso típico:
        engine = VenueComplianceEngine()
        report = engine.assess(manuscript_html, "csp_fiocruz", review_type="systematic_review_strict")
    """

    def __init__(self, profiles_dir: Path | str | None = None):
        self.profiles_dir = Path(profiles_dir) if profiles_dir else PROFILES_DIR

    def _load_venue_profile(self, venue_id: str) -> dict | None:
        for sub in ("venues_a1_br", "venues_a3_br", "venues_b1_br", "venues_q1_int", "venues_q2_int", "venues_fallback_br"):
            path = self.profiles_dir / sub / f"{venue_id}.yaml"
            if path.exists():
                try:
                    import yaml  # type: ignore
                    return yaml.safe_load(path.read_text(encoding="utf-8"))
                except ImportError:
                    raise RuntimeError("PyYAML não disponível.")
        return None

    def list_known_venues(self) -> list[str]:
        venues: list[str] = []
        for sub in ("venues_a1_br", "venues_a3_br", "venues_b1_br", "venues_q1_int", "venues_q2_int", "venues_fallback_br"):
            d = self.profiles_dir / sub
            if d.exists():
                venues.extend(p.stem for p in d.glob("*.yaml"))
        return sorted(venues)

    def assess_one(self, doc: ManuscriptDocument, venue_id: str,
                   review_type: str | None = None,
                   is_meta_analysis: bool = False) -> VenueAssessment | None:
        profile = self._load_venue_profile(venue_id)
        if profile is None:
            return None

        # Stage 2 + Stage 3 + Stage 4
        hard_checks = run_hard_requirements(doc, profile, review_type)
        guideline_checks = run_all_guidelines(doc, profile, review_type, is_meta_analysis)
        scope_score = compute_scope_score(doc, profile)

        all_checks = hard_checks + guideline_checks

        # Stage 5: Aggregation
        dim_results: dict[str, list[CheckResult]] = {dim: [] for dim in DIMENSION_WEIGHTS}
        for c in all_checks:
            dim = _classify_check_dimension(c.rule_id)
            dim_results.setdefault(dim, []).append(c)

        dimensions: dict[str, DimensionScore] = {}
        agg = 0.0
        for dim, weight in DIMENSION_WEIGHTS.items():
            if dim == "scope":
                score = scope_score.aggregate
                failed = []
            else:
                score, failed = _score_for_dimension(dim_results.get(dim, []), dim)
            dimensions[dim] = DimensionScore(name=dim, score=score, label=_label_for_score(score), failed_checks=failed)
            agg += weight * score

        # Stage 6: Gap prioritization
        gaps: list[Gap] = []
        for c in all_checks:
            if not c.passed:
                gaps.append(Gap(
                    rule_id=c.rule_id, description=c.rule_name,
                    severity=c.severity, fix_cost=c.fix_cost_estimate,
                    priority=_priority_score(c),
                    suggested_action=_suggested_action(c),
                ))
        gaps.sort(key=lambda g: g.priority, reverse=True)

        # needs_human_review
        nhr: list[dict] = []
        for c in all_checks:
            if c.extra.get("needs_human_review") or c.extra.get("needs_human_verification"):
                nhr.append({"rule_id": c.rule_id, "rule_name": c.rule_name, "evidence": c.evidence})

        # Extrair fallback_tier do profile (default=1 = diamond, mantém compat)
        tier = profile.get("metadata", {}).get("fallback_tier")
        if tier is None:
            tier = 1

        return VenueAssessment(
            venue_id=venue_id,
            venue_name=profile.get("metadata", {}).get("name", venue_id),
            aggregate_score=round(agg, 4),
            dimensions=dimensions,
            gaps_prioritized=gaps[:30],
            needs_human_review=nhr[:30],
            review_type_evaluated=review_type or "unspecified",
            fallback_tier=tier,
        )

    def assess(self, manuscript_source: str | Path | None = None,
               primary_venue_id: str = None,
               raw_text: str | None = None,
               review_type: str | None = None,
               is_meta_analysis: bool = False,
               include_alternatives: int = 5) -> ComplianceReport:
        from datetime import datetime, timezone

        doc = parse_manuscript(source=manuscript_source, raw_text=raw_text)

        # Avalia venue primário
        primary = None
        if primary_venue_id:
            primary = self.assess_one(doc, primary_venue_id, review_type, is_meta_analysis)
            if primary is None:
                raise ValueError(f"Venue '{primary_venue_id}' não encontrado em {self.profiles_dir}")

        # Stage 7: Multi-venue ranking — avalia outros venues e ranqueia
        all_venues = self.list_known_venues()
        if primary_venue_id:
            others = [v for v in all_venues if v != primary_venue_id]
        else:
            others = all_venues
        alternatives: list[VenueAssessment] = []
        for v in others[:20]:  # limitar para evitar processamento longo
            a = self.assess_one(doc, v, review_type, is_meta_analysis)
            if a:
                alternatives.append(a)
        # Decisão 14 (v2.2.2): ranquear por (fallback_tier ASC, aggregate_score DESC).
        # Tier-1 (diamond OA) sempre antes de tier-2 (APC modesto) sempre antes de tier-3
        # (hybrid alto-custo/subscription); dentro de cada tier, score decrescente.
        alternatives.sort(key=lambda a: (a.fallback_tier, -a.aggregate_score))
        alternatives = alternatives[:include_alternatives]

        if primary is None and alternatives:
            primary = alternatives[0]
            alternatives = alternatives[1:]

        # Feedback summary
        if primary:
            summary_pt = self._build_summary(primary, "pt")
            summary_en = self._build_summary(primary, "en")
        else:
            summary_pt = "Sem venue primário avaliado."
            summary_en = "No primary venue assessed."

        return ComplianceReport(
            manuscript_id=str(getattr(doc, "source_path", "in_memory")),
            primary_venue=primary,
            alternative_venues=alternatives,
            timestamp_iso8601=datetime.now(timezone.utc).isoformat(),
            feedback_summary_pt=summary_pt,
            feedback_summary_en=summary_en,
        )

    def _build_summary(self, va: VenueAssessment, lang: str) -> str:
        pct = int(round(va.aggregate_score * 100))
        if lang == "pt":
            top_gaps = ", ".join(g.description for g in va.gaps_prioritized[:3]) or "nenhum gap detectado"
            return (f"Manuscrito atende ~{pct}% dos requisitos de '{va.venue_name}'. "
                    f"Principais gaps: {top_gaps}.")
        else:
            top_gaps = ", ".join(g.description for g in va.gaps_prioritized[:3]) or "no gaps detected"
            return (f"Manuscript satisfies ~{pct}% of requirements for '{va.venue_name}'. "
                    f"Top gaps: {top_gaps}.")
