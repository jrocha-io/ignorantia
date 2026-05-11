"""Fix 21 / Phase C — Phase 2 skill manifest (Anthropic Cowork).

SKILL-PHASE-2.md is the entry-point skill for the Cowork session that
consumes a Phase 1 handoff and produces the final Zenodo zip. These
tests pin its contract:

- Valid frontmatter with ``name: ignorantia-phase-2``.
- Scope is Phase 2 work: retrieval + extraction-with-source-mapping +
  synthesis + compilation + 7 gates + ZIP.
- Mandatories enforce handoff validation before any retrieval starts.
- Mandatories list all 7 final gates in the canonical chain.
- Prohibitions forbid bypass of any gate, paywall bypass, IA-as-author,
  and the standard brand/vocabulary leaks.
- The skill stops at the artifact — no Zenodo upload, no email, no
  external contact.
- Operator-surface clean (zero developer markers).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "SKILL-PHASE-2.md"


# ── existence + frontmatter ────────────────────────────────────────────


def test_skill_phase_2_exists():
    assert SKILL.is_file()


def test_frontmatter_declares_phase_2_name():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---")
    frontmatter = text.split("---", 2)[1]
    assert re.search(r"^name:\s*ignorantia-phase-2\s*$", frontmatter, re.MULTILINE)


def test_frontmatter_signals_handoff_consumption():
    """The description must signal that this skill CONSUMES a handoff —
    not produces one, not starts from scratch."""
    text = SKILL.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1].lower()
    assert "handoff" in frontmatter
    assert "phase 1" in frontmatter or "phase-1" in frontmatter
    # Must NOT promise to start an SLR from scratch in Phase 2
    assert "começar uma slr nova" not in frontmatter or "a partir de um handoff" in frontmatter


# ── scope (Phase 2 work only) ──────────────────────────────────────────


def test_skill_has_10_step_workflow():
    """Phase 2 has 10 etapas: handoff validation → retrieval → extraction →
    QA → snowballing → cross-tab → synthesis → compilation → 7 gates →
    packaging."""
    text = SKILL.read_text(encoding="utf-8")
    expected = [
        r"^###\s+Etapa 1\s+—?\s+Validação",
        r"^###\s+Etapa 2\s+—?\s+Full[-\s]text\s+retrieval",
        r"^###\s+Etapa 3\s+—?\s+Leitura e extração",
        r"^###\s+Etapa 4\s+—?\s+Quality appraisal",
        r"^###\s+Etapa 5\s+—?\s+Snowballing",
        r"^###\s+Etapa 6\s+—?\s+Cross[-\s]tabulação",
        r"^###\s+Etapa 7\s+—?\s+Síntese",
        r"^###\s+Etapa 8\s+—?\s+Compilação",
        r"^###\s+Etapa 9\s+—?\s+7 Gates",
        r"^###\s+Etapa 10\s+—?\s+Empacotamento",
    ]
    for pat in expected:
        assert re.search(pat, text, re.MULTILINE), (
            f"Phase 2 skill is missing the section heading matching {pat!r}"
        )


def test_skill_mandates_handoff_validation_first():
    """The handoff validation must be mandatory and listed before any
    retrieval imperative."""
    text = SKILL.read_text(encoding="utf-8")
    mand = _mandatories_block(text)
    # The first "VALIDE o handoff" must come before "RETRIEVE full-text"
    validate_pos = mand.find("VALIDE o handoff")
    retrieve_pos = mand.find("RETRIEVE full-text")
    assert validate_pos >= 0, "Phase 2 must mandate handoff validation"
    assert retrieve_pos >= 0, "Phase 2 must mandate full-text retrieval"
    assert validate_pos < retrieve_pos, (
        "Handoff validation must come before retrieval in <mandatories>"
    )


# ── the seven gates ────────────────────────────────────────────────────


_SEVEN_GATES = [
    "check_persona_voice",
    "generate_assessment",
    "check_pipeline_invariants",
    "check_decision_19_vocabulary",
    "check_claim_source_coverage",
    "check_citation_graph",
    "check_manuscript_substantial",
]


def test_skill_lists_all_seven_gates_in_canonical_chain():
    """All 7 gates must appear in the gate-chain section, in order."""
    text = SKILL.read_text(encoding="utf-8")
    positions = [text.find(gate) for gate in _SEVEN_GATES]
    for gate, pos in zip(_SEVEN_GATES, positions):
        assert pos >= 0, f"Phase 2 skill must reference {gate}"
    # In-order: each subsequent gate appears after the previous one
    for i in range(1, len(positions)):
        assert positions[i] > positions[i - 1], (
            f"Gates must appear in canonical order. {_SEVEN_GATES[i-1]} "
            f"at {positions[i-1]}, {_SEVEN_GATES[i]} at {positions[i]}"
        )


def test_skill_mandates_each_gate_sidecar():
    """Each of the 7 gates emits a JSON sidecar; the skill must name all 7."""
    text = SKILL.read_text(encoding="utf-8")
    expected_sidecars = [
        "persona_voice_gate.json",
        "assessment_gate.json",
        "pipeline_invariants_gate.json",
        "vocabulary_gate.json",
        "claim_source_gate.json",
        "citation_graph_gate.json",
        "manuscript_substantial_gate.json",
    ]
    for sidecar in expected_sidecars:
        assert sidecar in text, (
            f"Phase 2 skill must name sidecar {sidecar}"
        )


# ── prohibitions ───────────────────────────────────────────────────────


def _prohibitions_block(text: str) -> str:
    m = re.search(r"<prohibitions>(.*?)</prohibitions>", text, re.DOTALL)
    assert m is not None, "<prohibitions> block missing"
    return m.group(1)


def _mandatories_block(text: str) -> str:
    m = re.search(r"<mandatories>(.*?)</mandatories>", text, re.DOTALL)
    assert m is not None, "<mandatories> block missing"
    return m.group(1)


def test_prohibitions_block_forbids_invalid_handoff_continuation():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA prossiga sem handoff válido", body, re.IGNORECASE)


def test_prohibitions_block_forbids_gate_bypass():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA bypass um gate", body, re.IGNORECASE)


def test_prohibitions_block_forbids_paywall_bypass():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA burle paywall", body, re.IGNORECASE)


def test_prohibitions_block_forbids_ia_as_author():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA liste a IA.*como autor", body, re.IGNORECASE)


def test_prohibitions_block_forbids_invented_dois():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA invente DOIs", body, re.IGNORECASE)


def test_prohibitions_block_caps_snowballing_depth():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA invoque snowballing recursivo além de 2", body, re.IGNORECASE)


def test_prohibitions_block_blocks_zip_without_seven_sidecars():
    text = SKILL.read_text(encoding="utf-8")
    body = _prohibitions_block(text)
    assert re.search(r"NUNCA sele o ZIP com < 7 sidecars", body)


# ── mandatories ────────────────────────────────────────────────────────


def test_mandatories_block_requires_claim_to_source_mapping():
    text = SKILL.read_text(encoding="utf-8")
    body = _mandatories_block(text)
    assert re.search(r"CRIE\s+`claim_to_source\.json`", body)


def test_mandatories_block_requires_full_compile_cycle():
    text = SKILL.read_text(encoding="utf-8")
    body = _mandatories_block(text)
    assert re.search(r"pdflatex.*bibtex.*pdflatex", body, re.DOTALL)


def test_mandatories_block_requires_skill_stops_at_artifact():
    """The mandatory must include the stop-at-artifact directive — no
    Zenodo upload, no email, no contact."""
    text = SKILL.read_text(encoding="utf-8")
    body = _mandatories_block(text)
    assert re.search(r"PARE depois de informar o caminho do ZIP", body, re.IGNORECASE)
    assert re.search(r"Não invoque Zenodo upload", body, re.IGNORECASE)


def test_mandatories_block_requires_unbranded_zip_filename():
    text = SKILL.read_text(encoding="utf-8")
    body = _mandatories_block(text)
    assert re.search(r"<author-slug>-<area>-<topic>-v<X\.Y\.Z>\.zip", body)
    assert re.search(r"sem brand da skill no filename", body, re.IGNORECASE)


# ── operator-surface cleanliness ──────────────────────────────────────


_DEVELOPER_MARKERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bFix\s+\d+(?:\.\d+)?\b"), "fix-history"),
    (re.compile(r"registrado em v\d+\.\d+"), "versioning-provenance"),
    (re.compile(r"tests/integration/"), "test-pointer"),
    (re.compile(r"RS-42 dogfood|RS-42 v\d|RS-42 Mark"), "incident-reference"),
    (re.compile(r"Para quem mantém"), "maintainer-block"),
    (re.compile(r"Verificação mecânica"), "test-coverage-pointer"),
    (re.compile(r"Adendo de manutenção"), "maintenance-aside"),
    (re.compile(r"^##\s+Hist[óo]rico\b", re.MULTILINE), "version-history-section"),
    (re.compile(r"\bdev-docs/"), "devdocs-pointer"),
)


def test_phase_2_skill_is_developer_marker_clean():
    text = SKILL.read_text(encoding="utf-8")
    hits: list[str] = []
    for pat, label in _DEVELOPER_MARKERS:
        for m in pat.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            hits.append(f"  L{line_no} [{label}]: {m.group(0)!r}")
    assert not hits, (
        "SKILL-PHASE-2.md contains developer markers — operator surface "
        "must be clean. Hits:\n" + "\n".join(hits)
    )


def test_phase_2_skill_brand_mentions_only_in_expected_contexts():
    """Same five-context allowlist as Phase 1: frontmatter, H1 title,
    anti-pattern teaching, CLI command references, Spinoza epigraph."""
    text = SKILL.read_text(encoding="utf-8")
    lines = text.splitlines()
    leaks: list[str] = []
    forbidden_marker = re.compile(
        r"NUNCA escreva|NUNCA cite|nunca se nomeia|"
        r"nome .*ignorantia.*não aparece|"
        r"Zero menções|nome da skill|sem brand",
        re.IGNORECASE,
    )
    for line_no, line in enumerate(lines, start=1):
        if not re.search(r"\bignorantia\b", line, re.IGNORECASE):
            continue
        if line_no <= 4:  # frontmatter
            continue
        if line.startswith("# ignorantia"):  # H1 title
            continue
        if "/ignorantia-execute" in line or "ignorantia-phase-2" in line:
            continue
        if "Ignorantia non est argumentum" in line:
            continue
        context_start = max(0, line_no - 5)
        context = "\n".join(lines[context_start : line_no + 1])
        if forbidden_marker.search(context):
            continue
        leaks.append(f"  L{line_no}: {line.strip()[:200]}")
    assert not leaks, (
        "SKILL-PHASE-2.md mentions the brand outside the five allowed "
        "contexts:\n" + "\n".join(leaks)
    )


# ── references between phases ──────────────────────────────────────────


def test_skill_points_at_handoff_schema():
    text = SKILL.read_text(encoding="utf-8")
    assert "schemas/handoff-v1.schema.json" in text


def test_skill_points_at_architecture_doc():
    text = SKILL.read_text(encoding="utf-8")
    assert "docs/BIPHASIC-ARCHITECTURE.md" in text


def test_skill_points_at_vocabulary_policy():
    text = SKILL.read_text(encoding="utf-8")
    assert "references/artifact-vocabulary-policy.xml" in text
