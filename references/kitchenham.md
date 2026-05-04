# Kitchenham guidelines for SLR in software engineering

Kitchenham B, Charters S. *Guidelines for performing Systematic Literature Reviews in Software Engineering*. EBSE Technical Report EBSE-2007-01, 2007. Updated by Kitchenham et al. (2015) in *Evidence-Based Software Engineering and Systematic Reviews*, CRC Press.

This is the canonical SLR methodology for SE/CS. It predates PRISMA 2020 and has its own vocabulary, but the two are compatible and best-practice papers report both.

## Three phases

### Phase 1 — Planning the review

1. Identify the need for a review.
2. Specify the research question(s) — typically PICOC.
3. Develop a review protocol containing:
   - Background
   - Research question(s)
   - Search strategy (terms, resources, search process)
   - Study selection criteria and procedures
   - Study quality assessment checklists and procedures
   - Data extraction strategy
   - Synthesis strategy
   - Project timetable
4. Evaluate the protocol (peer review).

### Phase 2 — Conducting the review

5. Identify research (search execution).
6. Select primary studies.
7. Assess study quality.
8. Extract required data.
9. Synthesize data.

### Phase 3 — Reporting the review

10. Specify dissemination mechanisms.
11. Format the main report.
12. Evaluate the report.

## Search strategy

Kitchenham emphasizes:

- **Major SE databases:** IEEE Xplore, ACM Digital Library, ScienceDirect (Elsevier), Springer Link, Wiley Online Library, EI Compendex/Engineering Village, ISI Web of Science, Scopus, Google Scholar.
- **dblp** is invaluable for completeness of CS bibliography.
- **Snowballing** (forward + backward citation tracking) is recommended as a complement to database search. Wohlin (2014) gives a formal procedure.

Search strings should be derived from PICOC keywords + synonyms, joined with Boolean operators. Each database's exact syntax varies — document one string per database.

## Quality assessment (QA) — Kitchenham's recommended generic questions

Score each included primary study on:

- **QA1** — Are the aims of the study clearly stated?
- **QA2** — Are the scope, context and experimental design of the study clearly defined?
- **QA3** — Are the variables in the study likely to be valid and reliable?
- **QA4** — Is the research process documented adequately?
- **QA5** — Are all study questions answered?
- **QA6** — Are the negative findings presented? *(optional)*
- **QA7** — Are the main findings stated clearly in terms of credibility, validity and reliability?
- **QA8** — Do the conclusions relate to the aim of the purpose of the study?

Scoring: Yes = 1, Partial = 0.5, No = 0. Sum across questions; threshold for inclusion in synthesis is typically ≥ 50% of max.

For empirical SE specifically, see the **Dyba & Dingsoyr (2008)** 11-question checklist.

## Synthesis

- **Quantitative synthesis** (meta-analysis) when data allow — rare in SE due to heterogeneity.
- **Narrative synthesis** is the norm. Group by RQ or by intervention type. Use tables to compare studies.
- **Thematic synthesis** for qualitative-heavy SLRs.

## Combining Kitchenham + PRISMA

Best-practice modern SE SLR papers report:

- Kitchenham's three-phase structure as the methodology section.
- PRISMA 2020 flow diagram in the results.
- Both Kitchenham QA1–QA8 (or Dyba-Dingsoyr) and PRISMA's risk-of-bias terminology.
- Pre-registration on Zenodo or OSF (PROSPERO is health-only).

This gives reviewers the SE-specific rigor Kitchenham defined plus the cross-disciplinary recognizability of PRISMA.

## Common pitfalls Kitchenham warns about

1. **Insufficiently specific RQ** → unmanageable scope.
2. **Missing snowballing** → incomplete coverage even with good database search.
3. **Single reviewer** → bias; always two independent reviewers + Cohen's kappa.
4. **No protocol pre-registration** → review becomes irreproducible/ad-hoc.
5. **No QA** → can't distinguish strong from weak evidence in the synthesis.
