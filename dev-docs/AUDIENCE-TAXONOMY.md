# Audience taxonomy — operator surface vs. developer surface

**Goal**: every text file in the repository is read by exactly ONE audience.

## Audiences

| Audience | Reads | Loaded at runtime by |
|---|---|---|
| **Operator** | Claude Desktop / chat session executing `/ignorantia` | `SKILL.md`, `references/*.xml` (curated), `assets/templates/*` |
| **Developer** | Claude Code in this terminal, plus human maintainer | `dev-docs/*`, `scripts/**/*.py` source, `tests/**`, repo root configs |

## SKILL.md — sections by audience

| Section | Lines (pre-F20) | Audience | Disposition |
|---|---|---|---|
| `# ignorantia` (intro) | 6-11 | Operator | Keep |
| `## Filosofia operacional` | 12-19 | Operator | Keep, scrub markers |
| `## Auditoria sistemática` | 20-23 | **Developer** | → `dev-docs/SKILL-HISTORY.md` |
| `## Estado quantitativo da skill (v2.20.0)` | 24-38 | **Developer** | → `dev-docs/SKILL-HISTORY.md` |
| `## Arquitetura v2.15-v2.18 — cobertura premium, logs, preâmbulo` | 39-78 | **Developer** | → `dev-docs/SKILL-HISTORY.md` |
| `## Decisões editoriais v2.0 — três modos de saída e mitigações` (Decisões 1-39) | 80-925 | **Both** (split per Decisão) | Strip developer markers; keep rule body |
| `## Infraestrutura de comparação automatizada (v2.5.0 — Etapa 4b)` | 745+ | **Developer** | → `dev-docs/SKILL-HISTORY.md` |
| `## Saída opcional: HTML Wiki-style (subcomando dedicado)` | 824+ | Operator | Keep, scrub markers |
| `## Saídas secundárias (geradas em paralelo)` | 925+ | Operator | Keep |
| `## Compliance ético e legal` | ~926+ | Operator | Keep |
| `## Versionamento SemVer das saídas` | ~990+ | Operator | Keep — but rewrite to make clear SemVer is metadata-only |
| `## PRISMA-2020 — execução completa, não apenas documentação` | ~997+ | Operator | Keep |
| `## Fluxo de trabalho (8 fases)` (mandatories block included) | ~1014+ | Operator | Keep |
| `## Padrões de design do HTML — referência rápida (subcomando html-wiki)` | ~1137+ | Operator | Keep (operator who calls html-wiki needs this) |
| `## Quando algo falhar` | ~1153+ | **Developer** (debugging guide) | → `dev-docs/SKILL-HISTORY.md` |
| `## Arquivos de referência > ### Existentes desde v1.x` | ~1156+ | Operator | Keep, but trim |
| `## Arquivos de referência > ### Novos na v2.0` | ~1174+ | Operator | Keep |
| `## Arquivos de referência > ### Scripts` | ~1190+ | **Developer** (operator calls scripts, doesn't grep them) | → `dev-docs/SKILL-HISTORY.md` |

## Inline markers to strip from operator-facing surface

These string patterns are developer-facing annotations interleaved through SKILL.md and need to be removed (or moved to history):

- `(registrado em vX.Y.Z[, Fix N do RS-42 remediation])` — versioning provenance in Decisão titles
- `**Verificação mecânica:** suite em tests/integration/...` — test pointer
- `**Para quem mantém esta skill:**` blocks
- `**Adendo de manutenção (vX.Y.Z, Fix N):**` blocks
- `Fix N do RS-42 remediation` — fix-history breadcrumbs
- `expandido em v2.23.3` etc. — version-trajectory asides
- `RS-42 v1.0.0 falharia com X violações`, `RS-42 Mark 4 falharia com Y violações` — dogfood references
- Internal architecture notes like `(constante VALID_REVIEW_TYPES_V21 em scripts/assessor/eliminators.py)`

## `references/` — files by audience

| File | Audience | Disposition |
|---|---|---|
| `DECISIONS.xml` (skill engineering decisions log) | **Developer** | → `dev-docs/DECISIONS.xml` |
| `V3_ARCHITECTURE_PLAN.xml` | **Developer** | → `dev-docs/V3_ARCHITECTURE_PLAN.xml` |
| `IMPLEMENTATION_STRATEGY.xml` | **Developer** | → `dev-docs/IMPLEMENTATION_STRATEGY.xml` |
| `WONT_IMPLEMENT.xml` | **Developer** | → `dev-docs/WONT_IMPLEMENT.xml` |
| `_manifesto.xml` | **Developer** (project philosophy / why-the-skill-exists) | → `dev-docs/_manifesto.xml` |
| `sprint-formal-roadmap.xml` | **Developer** (sprint timeline) | → `dev-docs/sprint-formal-roadmap.xml` |
| `audits/` | **Developer** | Already excluded from production zip (allowlist); keep in `references/` for now (already invisible to operator) |
| `calibrations/` | **Developer** | Idem |
| `draft/` | **Developer** | Idem |
| All other `*.xml` (academic-tier-criteria, prisma-2020, kitchenham, citation-styles/, databases/, modes/, profiles/, etc.) | Operator | Keep |
| `artifact-vocabulary-policy.xml` (new in F19.4) | Operator | Keep |

## `assets/templates/` — operator-facing

| File | Audience | Disposition |
|---|---|---|
| `protocol.xml` | Operator | Keep (already cleaned in F19.5) |
| `persona-voice.xml` | Operator | Keep (already cleaned in F19.5) |
| `manuscript-template.html` | Operator | Audit in Phase E |
| `extraction-form.xml` | Operator | Audit in Phase E |
| `quality-appraisal.xml` | Operator | Audit in Phase E |
| `modes/*.xml` | Operator | Audit in Phase E |

## `dev-docs/` — new tree

After Phase B:

```
dev-docs/
├── AUDIENCE-TAXONOMY.md          (this file)
├── SKILL-HISTORY.md              (content stripped from SKILL.md)
├── DECISIONS.xml                 (moved from references/)
├── V3_ARCHITECTURE_PLAN.xml      (moved from references/)
├── IMPLEMENTATION_STRATEGY.xml   (moved from references/)
├── WONT_IMPLEMENT.xml            (moved from references/)
├── _manifesto.xml                (moved from references/)
└── sprint-formal-roadmap.xml     (moved from references/)
```

`dev-docs/` is excluded from `scripts/build_production_package.py` allowlists.

## Production package allowlist diff

`scripts/build_production_package.py`:

- `REFERENCES_ROOT_GLOB`: `("references", "*.xml")` — **before**: ships all 26 top-level XMLs; **after**: same glob, but the 6 developer-only files are gone from `references/` so they won't be picked up. Net: ships 20 top-level XMLs (down from 26).
- No code change needed; the file move alone is sufficient.

## Meta-gate (Phase F)

After the refactor, a pre-build invariant must hold:

```python
DEVELOPER_MARKER_REGEXES = [
    r"\bFix\s+\d+\b",
    r"registrado em v\d+\.\d+",
    r"tests/integration/",
    r"RS-42 dogfood",
    r"Para quem mantém",
    r"Verificação mecânica",
    r"Adendo de manutenção",
    r"\bv\d+\.\d+\.\d+ falharia\b",
]
```

Run against `SKILL.md` + every shipped `references/*.xml` and `assets/templates/*`. Zero matches → operator surface is clean. Any match → block packaging.
