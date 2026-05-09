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


# ── F19.3 wiring: gate sidecar JSON ────────────────────────────────────


def _read_sidecar(deposit: Path) -> dict:
    import json
    return json.loads((deposit / "vocabulary_gate.json").read_text("utf-8"))


def test_gate_sidecar_emits_passed_true_on_clean_deposit(tmp_path: Path) -> None:
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "manuscript.md").write_text(
        "# Manuscript\n\nClean academic prose.\n", encoding="utf-8"
    )
    result = _run_cli("--all", str(deposit), "--gate-sidecar", "--quiet")
    assert result.returncode == 0
    sidecar = _read_sidecar(deposit)
    assert sidecar["passed"] is True
    assert sidecar["total_violations"] == 0
    assert sidecar["files_with_violations"] == []
    assert sidecar["files_scanned"] == 1


def test_gate_sidecar_emits_passed_false_with_full_aggregate(tmp_path: Path) -> None:
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "protocol.md").write_text(
        "Cascata Tier 0 (Decisão 24); FALLBACK_MD para paywall.\n",
        encoding="utf-8",
    )
    (deposit / "manuscript.md").write_text(
        "Clean.\n", encoding="utf-8"
    )
    result = _run_cli("--all", str(deposit), "--gate-sidecar", "--quiet")
    assert result.returncode == 2
    sidecar = _read_sidecar(deposit)
    assert sidecar["passed"] is False
    assert sidecar["total_violations"] >= 3
    assert "protocol.md" in sidecar["files_with_violations"]
    # By-label aggregate must contain the labels we expect.
    by_label = sidecar["violations_by_label"]
    assert "tier-tiering-label" in by_label
    assert "decision-number-reference" in by_label
    assert "fallback-mode-label" in by_label


def test_gate_sidecar_requires_all_flag(tmp_path: Path) -> None:
    """--gate-sidecar without --all is a CLI error."""
    f = tmp_path / "x.md"
    f.write_text("hello\n", encoding="utf-8")
    result = _run_cli(str(f), "--gate-sidecar")
    assert result.returncode == 1
    assert "requires --all" in result.stderr


def test_artifact_vocabulary_policy_exists_and_is_well_formed() -> None:
    """The policy file is the structural pair of the regex set.

    Adding a new pattern to ``_FORBIDDEN`` without updating this policy
    would leave Claude with no concrete translation guidance — the gate
    would fail with no actionable direction. The two files are paired
    sources of truth and must co-evolve.
    """
    import xml.etree.ElementTree as ET
    policy_path = ROOT / "references" / "artifact-vocabulary-policy.xml"
    assert policy_path.is_file(), (
        f"Decisão 41 requires {policy_path.relative_to(ROOT)}"
    )
    root = ET.parse(policy_path).getroot()
    assert root.tag == "doc"
    assert root.attrib.get("type") == "policy"
    body = (root.find("markdown").text or "").strip()
    # The six required vocabulary classes must each have a section.
    expected_class_headers = [
        "Database access cascade",
        "Skill-internal numbering",
        "Enum values vs. prose",
        "Meta-projeto bleed-through",
        "SemVer rhetoric",
        "Skill brand",
    ]
    for header in expected_class_headers:
        assert header in body, (
            f"policy file is missing the '{header}' translation section — "
            f"Decisão 41 requires all six classes to be paired with a "
            f"prose translation"
        )


def test_skill_md_mentions_decision_41_and_policy_file() -> None:
    """SKILL.md must instruct Claude to read the policy.

    Without this pointer, Claude doesn't know the policy exists. Pairing
    the file with the SKILL.md mandatory is the wiring step that closes
    the loop on F19.4 (structural refactor).
    """
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Decisão 41" in skill, (
        "SKILL.md must register Decisão 41 (deposit-wide vocabulary gate)"
    )
    assert "artifact-vocabulary-policy.xml" in skill, (
        "SKILL.md must point Claude at references/artifact-vocabulary-policy.xml "
        "so the translation table is discoverable from the operational doc"
    )
    assert "--all" in skill and "vocabulary_gate.json" in skill, (
        "SKILL.md mandatories must invoke the deposit-wide gate with sidecar "
        "emission, not the legacy single-file form"
    )


# ── F19.5 — code-region suppression for filename cross-references ──────


def test_latex_texttt_filename_reference_is_not_flagged() -> None:
    """``\\texttt{protocol-v1.0.0.md}`` is a filename ref, not SemVer rhetoric.

    Without this suppression, every cross-reference between deposit
    files (which legitimately carry version tags in their filenames)
    would falsely trigger the SemVer pattern.
    """
    text = (
        "O protocolo (\\texttt{protocol-v1.0.0.md}, presente no pacote) "
        "declara explicitamente os critérios."
    )
    violations = find_violations(text, is_latex=False)
    semver_hits = [v for v in violations if v.label == "semver-version-tag"]
    assert semver_hits == [], (
        f"\\texttt{{}} should suppress filename SemVer matches; got "
        f"{[v.matched_text for v in semver_hits]}"
    )


def test_html_code_filename_reference_is_not_flagged() -> None:
    text = (
        "<p>Pacote: <code>ignorantia-rs42-validade-v1.0.0.zip</code> "
        "depositado no Zenodo.</p>"
    )
    violations = find_violations(text)
    semver_hits = [v for v in violations if v.label == "semver-version-tag"]
    assert semver_hits == []


def test_html_code_brand_is_still_flagged() -> None:
    """Skill brand fails even inside <code>... — the brand never ships."""
    text = "<p>Pacote: <code>ignorantia-rs42-validade-v1.0.0.zip</code></p>"
    violations = find_violations(text)
    brand_hits = [v for v in violations if v.label == "skill-brand"]
    assert len(brand_hits) >= 1, (
        "skill-brand must remain bound even inside code-formatted regions; "
        "the brand never appears in a deposited artifact, formatted or not"
    )


def test_decision_n_inside_backticks_is_still_flagged() -> None:
    """Wrapping ``Decisão 8`` in backticks does NOT turn it into a
    legitimate filename reference. The narrow code-region suppression
    only applies to ``semver-version-tag`` (which can legitimately
    appear inside filenames like ``protocol-v1.0.0.md``)."""
    text = "Critério IC4 — vide `Decisão 27` da skill: três idiomas como obrigação."
    violations = find_violations(text)
    assert any(v.label == "decision-number-reference" for v in violations), (
        "Decisão N must fire inside backticks — backticks do not legitimize "
        "skill-internal numbering in deposit prose"
    )


def test_review_purpose_enum_inside_backticks_is_still_flagged() -> None:
    """The most common pattern in the bad protocol — ``\`design_foundational\``
    in prose body. Backtick wrapping is cosmetic; the literal token
    is still skill-internal vocabulary in prose."""
    text = "`design_foundational` — esta revisão metodológica fundamenta..."
    violations = find_violations(text)
    assert any(v.label == "review-purpose-enum" for v in violations), (
        "review_purpose enum value must fire even inside backticks — the "
        "label is metadata-only; in prose it belongs translated, not quoted"
    )


def test_tier_label_inside_code_is_still_flagged() -> None:
    text = "Acesso: `Tier 1 OA` ou `Tier 2 paywall`, conforme tabela."
    violations = find_violations(text)
    tier_hits = [v for v in violations if v.label == "tier-tiering-label"]
    assert len(tier_hits) >= 2, (
        "Tier labels must fire inside backticks — they are skill-internal "
        "taxonomy regardless of formatting"
    )


def test_fallback_md_inside_code_is_still_flagged() -> None:
    text = "Mode `FALLBACK_MD` é acionado quando..."
    violations = find_violations(text)
    assert any(v.label == "fallback-mode-label" for v in violations), (
        "FALLBACK_MD must fire even inside backticks"
    )


def test_markdown_inline_backtick_filename_reference_is_not_flagged() -> None:
    text = "O documento `protocol-v1.0.0.md` está no pacote Zenodo."
    violations = find_violations(text)
    semver_hits = [v for v in violations if v.label == "semver-version-tag"]
    assert semver_hits == []


def test_markdown_fenced_code_block_suppresses_only_semver() -> None:
    """Triple-backtick blocks suppress ONLY the SemVer pattern — code
    legitimately contains version constants. Decisão N, enum values,
    and skill-internal labels still fire even inside fences, because
    those literals are skill vocabulary regardless of formatting."""
    text = (
        "Veja o bloco abaixo:\n\n"
        "```\n"
        "review_purpose = design_foundational  # Decisão 8\n"
        "version = v1.0.0\n"
        "```\n\n"
        "Fim."
    )
    violations = find_violations(text)
    labels = [v.label for v in violations]
    # SemVer is suppressed — version constants in a code block are fine.
    assert "semver-version-tag" not in labels
    # But skill-internal labels still fire.
    assert "decision-number-reference" in labels
    assert "review-purpose-enum" in labels


def test_markdown_fenced_code_block_brand_still_flagged() -> None:
    text = (
        "```\n"
        "package = ignorantia\n"
        "```\n"
    )
    violations = find_violations(text)
    assert any(v.label == "skill-brand" for v in violations), (
        "skill-brand must fire even inside fenced code blocks"
    )


def test_latex_href_url_with_version_is_not_flagged() -> None:
    text = (
        "\\href{https://zenodo.org/records/abc/files/manuscript-v1.0.0.pdf}{"
        "Manuscrito}"
    )
    violations = find_violations(text)
    semver_hits = [v for v in violations if v.label == "semver-version-tag"]
    assert semver_hits == []


def test_prose_outside_code_still_caught() -> None:
    """Sanity: code-region suppression must NOT bleed into surrounding prose.

    A SemVer tag in plain prose right next to a backtick code span must
    still fire. This is the core safety of the suppression logic.
    """
    text = (
        "O artefato `protocol-v1.0.0.md` está no pacote. "
        "Esta v1.0.0 será re-executada em v1.1.0."
    )
    violations = find_violations(text)
    semver_hits = [v for v in violations if v.label == "semver-version-tag"]
    # Two SemVer tags are in prose ("Esta v1.0.0", "em v1.1.0"); the
    # third (`protocol-v1.0.0.md` inside backticks) is suppressed.
    assert len(semver_hits) == 2, (
        f"prose SemVer must still fire; got {[v.matched_text for v in semver_hits]}"
    )


def test_no_gate_flag_reports_but_does_not_fail(tmp_path: Path) -> None:
    """``--no-gate`` is the triage opt-out; sidecar still written, exit 0."""
    deposit = tmp_path / "deposit"
    deposit.mkdir()
    (deposit / "protocol.md").write_text("Decisão 8 aqui.\n", encoding="utf-8")
    result = _run_cli(
        "--all", str(deposit), "--gate-sidecar", "--no-gate", "--quiet"
    )
    assert result.returncode == 0
    sidecar = _read_sidecar(deposit)
    assert sidecar["passed"] is False
    assert sidecar["total_violations"] >= 1
    # The triage warning must surface to stderr so wrappers cannot pretend
    # they didn't see it.
    assert "GATE NOT ENFORCED" in result.stderr
