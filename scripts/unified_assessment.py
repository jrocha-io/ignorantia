#!/usr/bin/env python3
"""
unified_assessment.py — Phase 8 unified report (assessor v1 + compliance engine v2).

Invokes both layers and produces a single combined JSON report:

  - assessor v1 layer (eliminators E1-E16, content rubric C1-C7, form F1-F4,
    forensic audit A1-A7, editorial temperature T1-T4, sprint badge — experimental)
  - compliance engine v2 layer (venue-specific compliance, multi-dimensional score,
    prioritized gaps, alternative venues ranked)

Usage:
    python3 unified_assessment.py \\
        --package-dir /path/to/package \\
        --venue-id csp_fiocruz \\
        --review-type scoping_review \\
        --review-purpose design_foundational \\
        --out unified_report.json
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _setup_paths():
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))


def run_assessor_v1(package_dir: Path, version: str = "1.0.0") -> dict:
    """Invoke the v1 assessor pipeline (eliminators + rubric + audit + temperature)."""
    _setup_paths()
    try:
        # Reuses the legacy main module
        from assessor import main as assessor_main
        # The legacy main is CLI-driven; here we replicate its core logic
        from assessor.eliminators import run_all_eliminators
        from assessor import helpers
    except ImportError as e:
        return {"error": f"v1 assessor unavailable: {e}"}

    content_path = package_dir / "manuscript-content.json"
    if not content_path.exists():
        # Fallback: legacy scenarios usam content.json
        content_path = package_dir / "content.json"
    html_path = package_dir / "manuscript.html"
    qa_path = package_dir / "quality-appraisal.csv"
    searches_path = package_dir / "searches.json"

    if not content_path.exists() or not html_path.exists():
        return {"error": "missing required files for v1 assessor",
                "expected": ["manuscript-content.json or content.json", "manuscript.html"]}

    content = json.loads(content_path.read_text(encoding="utf-8"))
    html_content = html_path.read_text(encoding="utf-8")
    searches = None
    if searches_path.exists():
        try:
            searches = json.loads(searches_path.read_text(encoding="utf-8"))
        except Exception:
            searches = None

    elim_report = run_all_eliminators(
        package_dir=package_dir,
        content=content,
        html_content=html_content,
        qa_path=qa_path,
        searches=searches,
        version=version,
    )

    return {
        "layer": "assessor_v1",
        "version": "v1.x",
        "eliminators": [
            {
                "code": r.code,
                "name": r.name,
                "failed": r.failed,
                "severity": r.severity,
                "detail": r.detail,
            } for r in elim_report.results
        ],
        "any_blocking_failure": any(r.failed and r.severity in ("invalid_structural", "fraudulent")
                                    for r in elim_report.results),
        "any_content_invalid": any(r.failed and r.severity == "invalid_content"
                                    for r in elim_report.results),
    }


def run_compliance_v2(manuscript_html: str, venue_id: str | None,
                      review_type: str | None, review_purpose: str | None) -> dict:
    """Invoke v2 compliance engine."""
    _setup_paths()
    try:
        from compliance import VenueComplianceEngine
    except ImportError as e:
        return {"error": f"v2 compliance engine unavailable: {e}"}

    engine = VenueComplianceEngine()
    if venue_id and venue_id not in engine.list_known_venues():
        return {"error": f"venue_id '{venue_id}' not in known venues",
                "known_venues": engine.list_known_venues()}

    try:
        report = engine.assess(
            raw_text=manuscript_html,
            primary_venue_id=venue_id,
            review_type=review_type,
            include_alternatives=5,
        )
    except Exception as e:
        return {"error": f"compliance engine failure: {type(e).__name__}: {e}"}

    primary = report.primary_venue
    return {
        "layer": "compliance_v2",
        "version": "v2.0.0",
        "primary_venue": {
            "venue_id": primary.venue_id,
            "venue_name": primary.venue_name,
            "aggregate_score": primary.aggregate_score,
            "dimensions": {
                k: {"score": v.score, "label": v.label, "n_failed": len(v.failed_checks)}
                for k, v in primary.dimensions.items()
            },
            "top_5_gaps": [
                {
                    "rule_id": g.rule_id,
                    "description": g.description,
                    "severity": g.severity,
                    "fix_cost": g.fix_cost,
                    "priority": g.priority,
                    "suggested_action": g.suggested_action,
                } for g in primary.gaps_prioritized[:5]
            ],
            "needs_human_review": primary.needs_human_review[:10],
            "review_type_evaluated": primary.review_type_evaluated,
        } if primary else None,
        "alternative_venues": [
            {"venue_id": a.venue_id, "venue_name": a.venue_name,
             "aggregate_score": a.aggregate_score,
             "blocking_gaps_count": sum(1 for g in a.gaps_prioritized if g.severity == "blocking")}
            for a in report.alternative_venues
        ],
        "feedback_summary_pt": report.feedback_summary_pt,
        "feedback_summary_en": report.feedback_summary_en,
    }


def build_unified_report(package_dir: Path, venue_id: str | None,
                         review_type: str | None, review_purpose: str | None,
                         version: str = "1.0.0") -> dict:
    """Combine both layers into a single JSON report."""

    # Layer 1: assessor v1
    v1 = run_assessor_v1(package_dir, version=version)

    # Layer 2: compliance v2
    html_path = package_dir / "manuscript.html"
    html_content = ""
    if html_path.exists():
        html_content = html_path.read_text(encoding="utf-8")
    v2 = run_compliance_v2(html_content, venue_id, review_type, review_purpose)

    # Aggregate verdict
    blocking_in_v1 = v1.get("any_blocking_failure", False) or v1.get("any_content_invalid", False)
    primary = v2.get("primary_venue") or {}
    venue_score = primary.get("aggregate_score") if primary else None
    venue_below_threshold = (venue_score is not None and venue_score < 0.50)

    if v1.get("error"):
        verdict = "v1_error"
    elif v2.get("error"):
        verdict = "v2_error"
    elif blocking_in_v1:
        verdict = "blocked_by_assessor"
    elif venue_below_threshold:
        verdict = "below_venue_threshold"
    elif venue_score is not None and venue_score >= 0.85:
        verdict = "publishable_at_target_venue"
    elif venue_score is not None and venue_score >= 0.65:
        verdict = "needs_minor_revision"
    elif venue_score is not None:
        verdict = "needs_major_revision"
    else:
        verdict = "no_target_venue_assessed"

    return {
        "ignorantia_version": "2.0.0",
        "package_dir": str(package_dir),
        "metadata": {
            "venue_id_target": venue_id,
            "review_type": review_type,
            "review_purpose": review_purpose,
            "package_version": version,
            "report_timestamp_iso8601": datetime.now(timezone.utc).isoformat(),
        },
        "verdict": verdict,
        "layer_1_assessor_v1": v1,
        "layer_2_compliance_v2": v2,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--package-dir", required=True, type=Path)
    p.add_argument("--venue-id", default=None,
                   help="Target venue (e.g., csp_fiocruz, tse_ieee). Optional.")
    p.add_argument("--review-type", default=None,
                   choices=["systematic_review_with_2_reviewers", "scoping_review",
                            "rapid_review", "mapping_study", "narrative_review",
                            "umbrella_review", "living_review", "meta_analysis"],
                   help="Type of review.")
    p.add_argument("--review-purpose", default=None,
                   choices=["design_foundational", "design_validation",
                            "design_correction", "independent_inquiry"],
                   help="Purpose of the review (Decisão 8 v2.0).")
    p.add_argument("--version", default="1.0.0", help="Package SemVer.")
    p.add_argument("--out", type=Path,
                   help="Output JSON path. If not set, prints to stdout.")
    args = p.parse_args()

    report = build_unified_report(
        package_dir=args.package_dir.resolve(),
        venue_id=args.venue_id,
        review_type=args.review_type,
        review_purpose=args.review_purpose,
        version=args.version,
    )

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(output, encoding="utf-8")
        print(f"Wrote unified report to {args.out}", file=sys.stderr)
        print(f"Verdict: {report['verdict']}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
