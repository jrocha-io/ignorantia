"""Tests v2.23.3 (Fix 19 of RS-42 dogfood remediation, third wave) —
expanded Decisão 19 vocabulary check.

Fix 10 (v2.23.1) catches SemVer rhetoric, ``Decisão N``, ``Categoria A/B``,
metadata field names and the ``ignorantia`` brand. RS-42 Mark 4
(v2.23.2 dogfood) showed two new failure classes that slipped through:

1. Skill-internal taxonomy literal in deposited artifacts: ``Tier 1/2``,
   ``FALLBACK_MD``, ``KEY → PROXY``, ``DD-6``, ``design_foundational``.
2. Meta-project bleed-through: ``projeto subjacente``,
   ``as outras 41 revisões``, ``função declaratória / função instrumental``.

Plus the gate now scans **the whole deposit directory** (manuscript +
protocol + README + auxiliary Markdown), not only the manuscript file —
the worst leakage in RS-42 Mark 4 was in ``RS-42_protocol-v1.0.0.md``,
which the previous gate never inspected.

These tests pin both contracts: the new patterns and the directory walk.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_decision_19_vocabulary import (  # noqa: E402  — sys.path injection
    find_violations,
    find_violations_in_directory,
)

CLI = ROOT / "scripts" / "check_decision_19_vocabulary.py"


# ── new patterns: skill-internal taxonomy ──────────────────────────────


def test_dd_dash_n_design_decision_caught() -> None:
    text = "DD-6: Termos de Serviço proíbem scraping automatizado."
    labels = [v.label for v in find_violations(text)]
    assert "design-decision-reference" in labels


def test_tier_label_caught_with_or_without_space() -> None:
    """Skill-internal database tiering — both ``Tier 1`` and ``Tier1``."""
    for variant in ["Tier 1 OA", "Tier 2 paywall", "cascata Tier 0"]:
        labels = [v.label for v in find_violations(variant)]
        assert "tier-tiering-label" in labels, (
            f"variant {variant!r} did not flag tier-tiering-label"
        )


def test_fallback_md_mode_caught() -> None:
    text = "Bases sem credencial entram em FALLBACK_MD com instruções acionáveis."
    labels = [v.label for v in find_violations(text)]
    assert "fallback-mode-label" in labels


def test_key_proxy_cascade_caught() -> None:
    text = "Cascata KEY → PROXY → FALLBACK_MD ativada por base."
    labels = [v.label for v in find_violations(text)]
    assert "key-proxy-cascade" in labels
    # FALLBACK_MD should also fire — both labels in the same string.
    assert "fallback-mode-label" in labels


def test_review_purpose_enum_value_caught() -> None:
    """``design_foundational`` is a review_purpose enum value, not prose."""
    text = "A revisão foi categorizada como design_foundational pelo autor."
    labels = [v.label for v in find_violations(text)]
    assert "review-purpose-enum" in labels


def test_review_purpose_enum_with_hyphen_variant_caught() -> None:
    text = "design-foundational e design-validation são categorias internas."
    labels = [v.label for v in find_violations(text)]
    assert labels.count("review-purpose-enum") == 2


# ── new patterns: meta-project bleed-through ───────────────────────────


def test_projeto_subjacente_caught() -> None:
    text = "Esta revisão fundamenta as decisões do projeto subjacente do autor."
    labels = [v.label for v in find_violations(text)]
    assert "meta-project-reference" in labels


def test_outras_n_revisoes_caught() -> None:
    """The hallmark RS-42 Mark 4 leak: 'as outras 41 revisões'."""
    text = "como a presente revisão e as outras 41 revisões do projeto subjacente"
    labels = [v.label for v in find_violations(text)]
    assert "sibling-reviews-count" in labels
    assert "meta-project-reference" in labels


def test_outras_n_estudos_caught() -> None:
    text = "Os outros 12 estudos do mesmo autor seguiram protocolo análogo."
    labels = [v.label for v in find_violations(text)]
    assert "sibling-reviews-count" in labels


def test_funcao_declaratoria_taxonomy_caught() -> None:
    """The skill's CoI taxonomy split between declaratory and instrumental."""
    text = "Há tensão entre função declaratória e função instrumental do trabalho."
    labels = [v.label for v in find_violations(text)]
    assert labels.count("coi-function-split") == 2


def test_funcao_with_cedilla_variant_caught() -> None:
    """ASCII fallback ``funcao`` (no cedilla) must also fire."""
    text = "Conflito entre funcao declaratoria e funcao instrumental."
    labels = [v.label for v in find_violations(text)]
    assert "coi-function-split" in labels


# ── RS-42 Mark 4 regression: phrases verbatim from the bad protocol ───


def test_rs42_mark4_protocol_leakage_phrases_all_caught() -> None:
    """The exact phrases the user flagged from ``RS-42_protocol-v1.0.0.md``
    and ``RS-42_manuscript-v1.0.0.tex`` must each fail the gate."""
    leaked_phrases = [
        # From the protocol body:
        "vide Decisão 27 v2.9.0 da skill: três idiomas como obrigação",
        "Decisão 25 v2.9.0 — bases ibero-americanas obrigatórias",
        "Cascata Tier 0 (Decisão 24)",
        "DD-6: Termos de Serviço proíbem scraping automatizado",
        "design_foundational — esta revisão metodológica fundamenta",
        # From the manuscript body:
        "como a presente revisão e as outras 41 do projeto subjacente",
        "prática adotada nas revisões deste projeto subjacente",
        "decisões de design adotadas pelo autor no projeto subjacente",
        "Há, portanto, conflito potencial entre a função declaratória",
        "função instrumental (validar a metodologia que o autor planeja usar)",
        # Tier rhetoric in the methods section:
        "organizadas em três camadas: Tier 1 de acesso aberto",
        "Tier 2 ibero-americano obrigatório",
    ]
    for phrase in leaked_phrases:
        violations = find_violations(phrase)
        assert violations, (
            f"Phrase passed unexpectedly through expanded Decisão 19 gate: "
            f"{phrase!r}"
        )


def test_clean_methods_section_with_oa_paywall_does_not_false_positive() -> None:
    """Plain academic-prose alternatives to the Tier rhetoric must pass.

    Sanity check: the new patterns must catch the skill's labels but not
    the natural-language equivalents a researcher would actually write.
    """
    clean = (
        "Twenty-three databases were searched, partitioned into open-access "
        "sources (arXiv, Crossref, PubMed Central, EuropePMC, OpenAlex) and "
        "subscription sources (Scopus, Web of Science, ScienceDirect, "
        "Springer, Wiley, IEEE Xplore, ACM Digital Library). For the latter, "
        "absent institutional credentials, an indexed citation list was "
        "produced for manual retrieval and reported as a coverage gap."
    )
    assert find_violations(clean) == []


# ── directory walk: the whole deposit, not just the manuscript ─────────


def test_find_violations_in_directory_returns_only_dirty_files(
    tmp_path: Path,
) -> None:
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "manuscript.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Clean academic prose. Future work follows.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    (deposit / "protocol.md").write_text(
        "# Protocol\n\nIC4. ... vide Decisão 27 v2.9.0 da skill.\n",
        encoding="utf-8",
    )
    (deposit / "README.md").write_text(
        "# README\n\nPackage v1.0.0 with hash 0abc.\n",
        encoding="utf-8",
    )

    findings = find_violations_in_directory(deposit)
    paths_dirty = {p.name for p in findings}
    assert "manuscript.tex" not in paths_dirty
    assert "protocol.md" in paths_dirty
    assert "README.md" in paths_dirty  # SemVer rhetoric in README


def test_find_violations_in_directory_walks_recursively(tmp_path: Path) -> None:
    deposit = tmp_path / "deposit"
    nested = deposit / "fallback_md"
    nested.mkdir(parents=True)
    (nested / "citations_to_obtain_scopus.md").write_text(
        "Decisão 8 lista os DOIs a obter.\n", encoding="utf-8"
    )
    findings = find_violations_in_directory(deposit)
    assert any(p.name == "citations_to_obtain_scopus.md" for p in findings)


def test_find_violations_in_directory_skips_non_prose_extensions(
    tmp_path: Path,
) -> None:
    """CSVs, JSON and SVG must NOT be scanned — they're data, not prose."""
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    # Each of these contains a phrase that WOULD trigger the gate if scanned.
    (deposit / "screening.csv").write_text(
        "id,decision,reason\nS01,include,Decisão 8 do protocolo\n",
        encoding="utf-8",
    )
    (deposit / "metadata.json").write_text(
        '{"review_purpose": "design_foundational"}\n', encoding="utf-8"
    )
    (deposit / "prisma-flow.svg").write_text(
        '<svg><text>Tier 1 OA</text></svg>', encoding="utf-8"
    )
    findings = find_violations_in_directory(deposit)
    assert findings == {}, (
        "The directory walk must skip data-file extensions; "
        f"unexpected findings: {findings}"
    )


# ── CLI: --all directory mode ──────────────────────────────────────────


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_all_returns_zero_on_clean_deposit(tmp_path: Path) -> None:
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "manuscript.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\nClean prose. Future work follows.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    (deposit / "protocol.md").write_text(
        "# Protocol\n\nClean methods description.\n", encoding="utf-8"
    )
    result = _run_cli("--all", str(deposit))
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "PASSED" in result.stdout


def test_cli_all_returns_two_on_any_dirty_file(tmp_path: Path) -> None:
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "manuscript.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\nClean.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    (deposit / "protocol.md").write_text(
        "Decisão 27 v2.9.0 da skill: três idiomas.\n", encoding="utf-8"
    )
    result = _run_cli("--all", str(deposit))
    assert result.returncode == 2
    assert "FAILED" in result.stderr
    assert "protocol.md" in result.stderr


def test_cli_all_errors_when_path_is_a_file(tmp_path: Path) -> None:
    f = tmp_path / "manuscript.md"
    f.write_text("Clean.\n", encoding="utf-8")
    result = _run_cli("--all", str(f))
    assert result.returncode == 1
    assert "is not a directory" in result.stderr


def test_cli_all_quiet_emits_summary_only(tmp_path: Path) -> None:
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "protocol.md").write_text("Decisão 8 aqui.\n", encoding="utf-8")
    result = _run_cli("--all", str(deposit), "--quiet")
    assert result.returncode == 2
    assert "FAILED" in result.stderr
    # In quiet mode, per-violation `why:` lines must be suppressed.
    assert "why:" not in result.stderr
