# C4 architecture diagrams — Ignorantia v3

The diagrams below follow Simon Brown's C4 model: Context →
Container → Component (Code level intentionally omitted; the
codebase + docstrings are the source of truth at that resolution).
All diagrams are written in Mermaid so GitHub renders them inline
without extra tooling.

To regenerate or export to SVG/PNG locally, use any Mermaid
renderer (e.g. `npx @mermaid-js/mermaid-cli -i C4_DIAGRAMS.md`).

---

## Level 1 — System Context

Who uses Ignorantia and what does it talk to?

```mermaid
C4Context
    title System Context — Ignorantia v3

    Person(researcher, "Researcher", "Conducts a PRISMA-2020 systematic literature review.")
    Person(reviewer, "Peer reviewer", "Audits an SLR package for methodological compliance.")

    System(ignorantia, "Ignorantia", "PRISMA-2020 SLR construction skill (CLI + library).")

    System_Ext(openalex, "OpenAlex", "Open bibliographic API.")
    System_Ext(crossref, "Crossref", "DOI metadata API.")
    System_Ext(arxiv, "arXiv", "Preprint repository API.")
    System_Ext(other_sources, "60+ other sources", "Tier-1 OA, Tier-2 metadata-only, Tier-3 paywalled.")

    System_Ext(filesystem, "Local filesystem", "Manuscript JSON inputs, rendered artefacts (HTML / LaTeX / DOCX), reproducibility manifest.")

    Rel(researcher, ignorantia, "Builds an SLR via", "ignorantia <subcommand>")
    Rel(reviewer, ignorantia, "Audits via", "ignorantia audit / finalize")

    Rel(ignorantia, openalex, "Searches", "HTTPS GET")
    Rel(ignorantia, crossref, "Searches", "HTTPS GET")
    Rel(ignorantia, arxiv, "Searches", "HTTPS GET (Atom)")
    Rel(ignorantia, other_sources, "Searches via 60+ adapters", "HTTPS / Tier-2 cascade")

    Rel(ignorantia, filesystem, "Reads inputs / writes artefacts")
```

---

## Level 2 — Container

What runs inside the Ignorantia system boundary?

```mermaid
C4Container
    title Container Diagram — Ignorantia v3

    Person(researcher, "Researcher")

    System_Boundary(ignorantia, "Ignorantia v3") {
        Container(cli, "Click CLI", "Python · Click 8.x", "ignorantia audit / finalize / render / search. Composition root + JSON-schema validation.")

        Container(application, "Application layer", "Python · stateless use cases", "RunAuditUseCase, FinalizePipelineUseCase, RenderManuscriptUseCase, SearchForStudiesUseCase.")

        Container(domain_search, "Search bounded context", "Python · domain", "SearchOrchestrator, AdapterPort / AdapterFactoryPort, FetchedItem, DeduplicatorService.")

        Container(domain_render, "Render bounded context", "Python · domain", "ManuscriptDoc + builder, RendererPort, CitationFormatterPort.")

        Container(domain_pipeline, "Pipeline bounded context", "Python · domain", "PipelineExecutor + PipelineStep registry.")

        Container(domain_compliance, "Compliance bounded context", "Python · domain", "ComplianceEngine, VenueProfile, Decision, DesignDecision.")

        Container(domain_audit, "Audit bounded context", "Python · domain", "ManifestService, AuditEntry, ReproducibilityManifest.")

        Container(infrastructure, "Infrastructure adapters", "Python", "60+ search adapters (HTTP), HtmlRenderer, LatexRenderer, DocxRenderer, four citation formatters, single shared HttpClient.")

        Container(legacy, "ignorantia.legacy", "Python · compat shim", "DeprecationWarning + migration_guide() pointer for v2 callers.")
    }

    System_Ext(external_apis, "External search APIs", "OpenAlex, Crossref, arXiv, etc.")
    System_Ext(filesystem, "Local filesystem")

    Rel(researcher, cli, "Runs", "argv")
    Rel(cli, application, "Calls use cases via DTOs")
    Rel(application, domain_search, "Composes")
    Rel(application, domain_render, "Composes")
    Rel(application, domain_pipeline, "Composes")
    Rel(application, domain_audit, "Composes")
    Rel(application, infrastructure, "Resolves ports", "DIP")
    Rel(domain_search, infrastructure, "AdapterPort instances created by factory")
    Rel(domain_render, infrastructure, "Renderer / formatter instances")
    Rel(infrastructure, external_apis, "Searches via shared HttpClient", "HTTPS")
    Rel(cli, filesystem, "Reads inputs / writes artefacts")
    Rel(legacy, application, "Forwards v2 callers (with warning)")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

The compliance bounded context is omitted from the relations above
to keep the diagram readable: it is composed by future use cases
(planned: `EvaluateManuscriptUseCase`) but is not yet wired through
a CLI subcommand in v3.0.0-alpha.

---

## Level 3 — Component (Render bounded context)

The render context drilled down to its components. The pattern is
representative — search, audit, pipeline, and compliance follow the
same shape (entities + ports + services + factory + concrete
adapters in `infrastructure/`).

```mermaid
C4Component
    title Component Diagram — Render Bounded Context

    Container_Boundary(domain_render, "domain/render/") {
        Component(manuscript, "ManuscriptDoc", "Frozen dataclass + Builder", "title, abstract, sections, references, language, keywords. ManuscriptDoc.builder() for fluent assembly.")
        Component(reference, "Reference", "Frozen dataclass", "type, title, authors, year, venue, volume, doi, …")
        Component(section, "Section", "Frozen dataclass", "id, title, body_md.")

        Component(value_objects, "Value objects", "str-Enum", "CitationStyle (abnt/apa/ieee/vancouver), OutputFormat (html/docx/latex).")

        Component(renderer_port, "RendererPort", "ABC", "render(doc) -> bytes; output_format -> OutputFormat.")
        Component(citation_port, "CitationFormatterPort", "ABC", "format_reference(ref); format_inline_citation(ref, page=, index=); style -> CitationStyle.")
        Component(interactive_port, "InteractiveRendererPort", "ABC extends RendererPort", "render_section(section) -> bytes for incremental output.")
    }

    Container_Boundary(infrastructure_render, "infrastructure/render/") {
        Component(html_renderer, "HtmlRenderer", "Concrete RendererPort + InteractiveRendererPort")
        Component(latex_renderer, "LatexRenderer", "Concrete RendererPort")
        Component(docx_renderer, "DocxRenderer", "Concrete RendererPort", "Behind [docx] extra; lazy-import.")
        Component(md_to_latex, "MarkdownToLatex", "Pure function", "Tiny Markdown subset → LaTeX with proper escaping.")

        Component(abnt, "AbntCitationFormatter", "Concrete CitationFormatterPort")
        Component(apa, "ApaCitationFormatter", "Concrete CitationFormatterPort")
        Component(ieee, "IeeeCitationFormatter", "Concrete CitationFormatterPort")
        Component(vancouver, "VancouverCitationFormatter", "Concrete CitationFormatterPort")
        Component(citation_factory, "citation_formatter_for", "Factory", "CitationStyle -> CitationFormatterPort (lazy-singleton).")
    }

    Container(application, "RenderManuscriptUseCase", "application/")
    Container(cli_render, "ignorantia render", "interface/cli/")

    Rel(cli_render, application, "Builds DTO + executes")
    Rel(application, manuscript, "Builds via ManuscriptDoc.builder()")
    Rel(application, renderer_port, "Calls render()")

    Rel(renderer_port, citation_port, "Uses for the references list")
    Rel(html_renderer, renderer_port, "implements")
    Rel(html_renderer, interactive_port, "also implements")
    Rel(latex_renderer, renderer_port, "implements")
    Rel(latex_renderer, md_to_latex, "Uses for body_md → LaTeX")
    Rel(docx_renderer, renderer_port, "implements")

    Rel(abnt, citation_port, "implements")
    Rel(apa, citation_port, "implements")
    Rel(ieee, citation_port, "implements")
    Rel(vancouver, citation_port, "implements")
    Rel(citation_factory, citation_port, "Returns one of these")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

---

## What's not drawn

* **Code-level (Level 4)** — UML class diagrams are intentionally
  omitted. Each class' shape is best read in its own
  `entities.py` / `value_objects.py` / `services.py` file with
  the `mypy --strict` annotations as the source of truth.
* **Data flow timing** — sequence diagrams (search → render →
  audit) belong in the tutorial and the architecture-plan
  document, not at the C4 level.
* **Deployment view** — Ignorantia ships as a Python package
  installed via pip; there is no separate runtime topology to
  draw.

For the design rationale behind the bounded-context split, the
DDD vocabulary, and the SOLID principle mapping, see
[`dev-docs/V3_ARCHITECTURE_PLAN.xml`](../../dev-docs/V3_ARCHITECTURE_PLAN.xml).
