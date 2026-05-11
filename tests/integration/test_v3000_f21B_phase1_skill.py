"""Fix 21 / Phase B — Phase 1 skill manifest (Claude Desktop chat).

SKILL-PHASE-1.md is the entry-point skill for the chat session that
produces the biphasic handoff. These tests pin its contract:

- It is a valid operator-surface file (zero developer markers, zero
  brand outside the allowed contexts).
- It is scoped to Phase 1 work only — it never instructs Claude to
  retrieve full-text, write manuscript prose, or run the four
  monolithic-era packaging gates that belong to Phase 2.
- It points at the canonical schema (`schemas/handoff-v1.schema.json`)
  and the architecture contract (`docs/BIPHASIC-ARCHITECTURE.md`).
- The 10 interview dimensions documented in the original SKILL.md are
  all preserved (mass non-loss).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "SKILL-PHASE-1.md"


# ── existence + frontmatter ────────────────────────────────────────────


def test_skill_phase_1_exists():
    assert SKILL.is_file(), f"SKILL-PHASE-1.md missing at {SKILL}"


def test_frontmatter_declares_phase_1_name():
    """The Claude skill manifest convention requires ``name:`` in the
    frontmatter. The biphasic split uses ``ignorantia-phase-1`` so it
    doesn't collide with future Phase 2 skill manifests."""
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---"), "SKILL-PHASE-1.md must start with YAML frontmatter"
    frontmatter = text.split("---", 2)[1]
    assert re.search(r"^name:\s*ignorantia-phase-1\s*$", frontmatter, re.MULTILINE)


def test_frontmatter_description_mentions_phase_2_handoff():
    """The description must signal that this skill produces a handoff for
    Phase 2 — otherwise an operator might run Phase 1 and expect a
    manuscript at the end."""
    text = SKILL.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1].lower()
    assert "handoff" in frontmatter
    assert "phase 2" in frontmatter or "phase-2" in frontmatter or "cowork" in frontmatter


# ── Phase 1 scope is enforced (Phase 2 work is forbidden here) ─────────


_PHASE_2_FORBIDDEN_VERBS = [
    # Full-text retrieval
    r"baixar\s+(?:pdf|full[-\s]text)",
    r"download\s+full[-\s]text",
    # Writing the manuscript
    r"\bredigir\s+(?:manuscrito|§\d+)",
    r"compilar\s+(?:LaTeX|pdf)",
    r"\brun\s+pdflatex",
]


def _mandatories_block(text: str) -> str:
    m = re.search(r"<mandatories>(.*?)</mandatories>", text, re.DOTALL)
    assert m is not None, "<mandatories> block missing from Phase 1 skill"
    return m.group(1)


def test_phase_1_mandatories_does_not_instruct_full_text_retrieval():
    """Phase 1 <mandatories> must not include retrieval imperatives —
    that's Phase 2 work. The <prohibitions> block legitimately mentions
    retrieval to forbid it; this test only checks the positive
    imperatives in <mandatories>."""
    body = _mandatories_block(SKILL.read_text(encoding="utf-8"))
    for pat in _PHASE_2_FORBIDDEN_VERBS[:2]:
        assert not re.search(pat, body, re.IGNORECASE), (
            f"Phase 1 <mandatories> must not instruct full-text retrieval; "
            f"matched {pat!r}"
        )


def test_phase_1_mandatories_does_not_instruct_manuscript_writing():
    """Phase 1 <mandatories> must not include manuscript-writing imperatives."""
    body = _mandatories_block(SKILL.read_text(encoding="utf-8"))
    for pat in _PHASE_2_FORBIDDEN_VERBS[2:]:
        assert not re.search(pat, body, re.IGNORECASE), (
            f"Phase 1 <mandatories> must not instruct manuscript writing; "
            f"matched {pat!r}"
        )


def test_phase_1_skill_has_explicit_stop_after_handoff():
    """The mandatory must include a stop-after-handoff directive."""
    text = SKILL.read_text(encoding="utf-8")
    assert re.search(r"PARE\s+depois\s+de\s+emitir\s+o\s+handoff", text, re.IGNORECASE), (
        "Phase 1 must mandate stopping after handoff emission"
    )


# ── Phase 1 deliverables present ───────────────────────────────────────


def test_skill_points_at_handoff_schema():
    """The skill must reference the canonical schema by path."""
    text = SKILL.read_text(encoding="utf-8")
    assert "schemas/handoff-v1.schema.json" in text


def test_skill_points_at_architecture_doc():
    text = SKILL.read_text(encoding="utf-8")
    assert "docs/BIPHASIC-ARCHITECTURE.md" in text


def test_skill_documents_5_phase_1_steps():
    """The 5 operational steps of Phase 1 (interview, protocol, search,
    dedup, screening) plus the handoff emission step must each have a
    section heading."""
    text = SKILL.read_text(encoding="utf-8")
    expected = [
        r"^###\s+Etapa 1\s+—?\s+Entrevista",
        r"^###\s+Etapa 2\s+—?\s+Protocolo",
        r"^###\s+Etapa 3\s+—?\s+Execução",
        r"^###\s+Etapa 4\s+—?\s+Dedup",
        r"^###\s+Etapa 5\s+—?\s+Screening",
        r"^###\s+Etapa 6\s+—?\s+Emissão",
    ]
    for pat in expected:
        assert re.search(pat, text, re.MULTILINE), (
            f"Phase 1 skill is missing the section heading matching {pat!r}"
        )


def test_skill_preserves_10_interview_dimensions():
    """The 10 dimensions from the monolithic SKILL.md must all survive
    the migration to Phase 1. The numbered list 1-10 is a structural
    invariant of the interview script."""
    text = SKILL.read_text(encoding="utf-8")
    # The interview section uses numbered Markdown items 1.-10.
    interview_block = re.search(
        r"### Etapa 1\b.*?(?=^###\s|\Z)", text, re.DOTALL | re.MULTILINE
    )
    assert interview_block is not None
    body = interview_block.group(0)
    numbered = re.findall(r"^\d+\.\s+\*\*", body, re.MULTILINE)
    assert len(numbered) >= 10, (
        f"Phase 1 interview must keep all 10 dimensions; found {len(numbered)} numbered items"
    )


# ── operator-surface cleanliness (re-checks F20 invariants on the new file) ─


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


def test_phase_1_skill_is_developer_marker_clean():
    """SKILL-PHASE-1.md must satisfy the same operator-surface invariants
    as SKILL.md did after F20. Zero developer markers."""
    text = SKILL.read_text(encoding="utf-8")
    hits: list[str] = []
    for pat, label in _DEVELOPER_MARKERS:
        for m in pat.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            hits.append(f"  L{line_no} [{label}]: {m.group(0)!r}")
    assert not hits, (
        "SKILL-PHASE-1.md contains developer markers — operator surface must "
        "be clean. Hits:\n" + "\n".join(hits)
    )


def test_phase_1_skill_brand_mentions_only_in_expected_contexts():
    """The brand is allowed in 4 contexts inside SKILL-PHASE-1.md:

    1. YAML frontmatter (``name: ignorantia-phase-1`` and ``description:``)
    2. The top H1 heading (``# ignorantia — Phase 1 (chat)``), mirroring
       SKILL.md's title convention
    3. Anti-pattern teaching paragraphs (explicit ``NUNCA``/``nunca se
       nomeia`` markers)
    4. CLI command references (``/ignorantia-execute``,
       ``ignorantia-phase-1``)

    Any brand mention outside these four contexts is a leak — Phase 1
    must not embed the brand into instructional prose that operator-
    Claude would treat as canonical and reproduce in the handoff or
    surface to Phase 2.
    """
    text = SKILL.read_text(encoding="utf-8")
    lines = text.splitlines()
    leaks: list[str] = []
    forbidden_marker = re.compile(
        r"NUNCA escreva|NUNCA cite|nunca se nomeia|"
        r"nome .*ignorantia.*não aparece|"
        r"Zero menções do nome|nome da skill",
        re.IGNORECASE,
    )
    for line_no, line in enumerate(lines, start=1):
        if not re.search(r"\bignorantia\b", line, re.IGNORECASE):
            continue
        # Context 1: frontmatter (lines 2-4 typically)
        if line_no <= 4:
            continue
        # Context 2: top H1 heading
        if line.startswith("# ignorantia"):
            continue
        # Context 4: CLI command references
        if "/ignorantia-execute" in line or "ignorantia-phase-1" in line:
            continue
        # Context 5: the Spinoza Latin epigraph (the skill name etymology).
        if "Ignorantia non est argumentum" in line:
            continue
        # Context 3: anti-pattern teaching (look for forbidden marker in
        # the line itself OR in the previous paragraph context)
        context_start = max(0, line_no - 5)
        context = "\n".join(lines[context_start : line_no + 1])
        if forbidden_marker.search(context):
            continue
        leaks.append(f"  L{line_no}: {line.strip()[:200]}")
    assert not leaks, (
        "SKILL-PHASE-1.md mentions the brand outside the four allowed "
        "contexts (frontmatter, H1 title, anti-pattern teaching, CLI "
        "command references):\n" + "\n".join(leaks)
    )


# ── handoff workflow invariants ────────────────────────────────────────


def test_skill_mandates_minimum_3_bases():
    text = SKILL.read_text(encoding="utf-8")
    assert re.search(r"\bEXECUTE\s+buscas em\s+≥\s*3\s+bases", text)


def test_skill_mandates_handoff_hash_recomputation_check():
    text = SKILL.read_text(encoding="utf-8")
    assert "handoff_hash" in text
    assert "SHA-256" in text
    assert re.search(r"VALIDE o handoff contra o schema", text, re.IGNORECASE)


def test_skill_forbids_full_text_retrieval_in_prohibitions():
    """The <prohibitions> block must explicitly forbid full-text retrieval
    in Phase 1."""
    text = SKILL.read_text(encoding="utf-8")
    proh = re.search(r"<prohibitions>(.*?)</prohibitions>", text, re.DOTALL)
    assert proh is not None
    body = proh.group(1)
    assert re.search(r"NUNCA retrieve full-text", body, re.IGNORECASE)


def test_skill_forbids_manuscript_writing_in_prohibitions():
    text = SKILL.read_text(encoding="utf-8")
    proh = re.search(r"<prohibitions>(.*?)</prohibitions>", text, re.DOTALL)
    assert proh is not None
    body = proh.group(1)
    assert re.search(r"NUNCA gere prosa de manuscrito", body, re.IGNORECASE)
