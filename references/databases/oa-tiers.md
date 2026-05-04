# Tiers Open Access — política de acesso a bases bibliográficas

> **Constraint operacional v2.1:** O ghostwriter ignorantia SÓ consulta bases gratuitas (Tier 1) e bases com metadados livres (Tier 2). Material atrás de paywall (Tier 3) só é acessado via fornecimento manual pelo usuário (e.g., upload de PDF, exportação de citação, fornecimento de DOI específico).
>
> **Razão.** Coerência com o ethos OA-first do projeto + minimização de custos para o autor sem orçamento institucional + reprodutibilidade (qualquer terceiro pode replicar busca em Tier 1).

---

## Tier 1 — Sempre OA, sempre buscar

Bases que disponibilizam **full-text gratuito** ou apenas **artigos OA**. Sem paywall, sem necessidade de credencial institucional.

### Saúde (multi-domínio)

| Base | URL | API | Cobertura |
|---|---|---|---|
| **PubMed Central (PMC)** | https://www.ncbi.nlm.nih.gov/pmc/ | E-utilities (gratuita, sem chave) | ~9M artigos OA biomédicos |
| **EuropePMC** | https://europepmc.org/ | RESTful (gratuita) | PMC + extras europeus |
| **LILACS** | https://lilacs.bvsalud.org/ | iAH (gratuita) | Latam saúde, PT/ES/EN |
| **SciELO** | https://search.scielo.org/ | API SciELO (gratuita) | Multi-domínio Latam |
| **BDENF** | https://pesquisa.bvsalud.org/portal/?lang=pt | iAH | Enfermagem BR |
| **BVS-MS** | https://bvsms.saude.gov.br/ | manual | Ministério da Saúde BR |
| **medRxiv / bioRxiv** | https://www.medrxiv.org/ | API (gratuita) | Preprints biomédicos |

### Educação

| Base | URL | API | Cobertura |
|---|---|---|---|
| **ERIC (filtro OA)** | https://eric.ed.gov/?filter=fulltextav | RESTful (gratuita) | Educação multi-país (filtro `fulltextav`) |
| **EdArXiv** | https://edarxiv.org/ | OSF API | Preprints de educação |
| **SciELO Education** | https://search.scielo.org/ | SciELO API | Educação Latam |
| **Domínio Público (BR)** | http://www.dominiopublico.gov.br/ | manual | Educação BR |

### CS / SE / Tecnologia

| Base | URL | API | Cobertura |
|---|---|---|---|
| **arXiv (cs.*, math.*, stat.*)** | https://arxiv.org/ | API arXiv (gratuita) | Preprints + papers ($0$, multi-categorias) |
| **DBLP** | https://dblp.org/ | API DBLP (gratuita) | Metadados completos CS, ~7M registros |
| **HAL (CCSD)** | https://hal.science/ | API HAL (gratuita) | Multi-domínio com forte CS na França |
| **CORE (UK)** | https://core.ac.uk/ | RESTful (gratuita com chave) | Agregador OA, ~290M registros |

### Multi-domínio

| Base | URL | API | Cobertura |
|---|---|---|---|
| **DOAJ** | https://doaj.org/ | RESTful (gratuita) | Diretório de revistas OA, ~21k títulos |
| **OpenAlex** (filtro `is_oa=true`) | https://openalex.org/ | RESTful (gratuita) | ~250M registros, filtro OA estrito |
| **Crossref** (filtro de licença OA) | https://api.crossref.org/ | RESTful (gratuita) | ~140M registros, com filtro de licença |
| **OSF Preprints** | https://osf.io/preprints/ | OSF API (gratuita) | Multi-disciplinar preprints |
| **Zenodo** | https://zenodo.org/ | REST + OAI-PMH (gratuitas) | Repositório CERN, multi-domínio |
| **SSRN** (Public Policy Network) | https://www.ssrn.com/ | manual | Política pública, ciências sociais |
| **PhilArchive** | https://philarchive.org/ | API (gratuita) | Filosofia OA |
| **Wikipedia** | https://en.wikipedia.org/ | API MediaWiki | Mapa, NÃO fonte primária |

### Política pública / grey literature

| Base | URL | Cobertura |
|---|---|---|
| **OECD iLibrary** | https://www.oecd-ilibrary.org/ | Relatórios OECD (subset OA) |
| **UNESCO** | https://unesdoc.unesco.org/ | Relatórios UNESCO (gratuitos) |
| **Banco Mundial Open Knowledge** | https://openknowledge.worldbank.org/ | Relatórios Banco Mundial |
| **IPEA** | https://www.ipea.gov.br/portal/publicacoes | Pesquisa econômica BR |
| **INEP** | https://www.gov.br/inep/pt-br/ | Educação BR (estatísticas, censos) |
| **NIST Pubs** | https://www.nist.gov/publications | Tecnologia / standards |

---

## Tier 2 — Metadados livres, full-text pode requerer fornecimento

Bases que permitem **busca livre por metadados** (título, autor, abstract, keywords) mas o full-text pode estar em paywall ou requerer credenciais.

| Base | URL | API | Cobertura |
|---|---|---|---|
| **Crossref** (geral, sem filtro OA) | https://api.crossref.org/ | RESTful (gratuita) | ~140M registros, metadados completos |
| **OpenAlex** (geral, sem filtro OA) | https://openalex.org/ | RESTful (gratuita) | ~250M, metadados + abstract quando OA |
| **Semantic Scholar** | https://www.semanticscholar.org/ | RESTful (gratuita com rate limit) | ~200M, AI-enhanced metadata |
| **PubMed** (completo, não só PMC) | https://pubmed.ncbi.nlm.nih.gov/ | E-utilities | ~36M registros biomédicos |
| **CINAHL** (subset OA) | via EBSCO | dependente | Enfermagem (subset gratuito) |
| **Google Scholar** | https://scholar.google.com/ | scrape limitado por TOS | Indexação ampla mas com limitações de uso programático |

**Limitações de uso de Tier 2:**

- Full-text pode requerer acesso institucional ou compra individual.
- O ghostwriter **busca** em Tier 2 mas **declara explicitamente** quando não conseguiu acessar full-text.
- Estudos relevantes encontrados em Tier 2 sem full-text disponível são listados em `studies_with_metadata_only.csv` no pacote Zenodo.

---

## Tier 3 — Apenas via material fornecido pelo usuário

Bases atrás de **paywall completo** ou que **proíbem acesso programático** sem credencial institucional.

| Base | Status |
|---|---|
| **Scopus (Elsevier)** | Paywall completo |
| **Web of Science (Clarivate)** | Paywall completo |
| **Embase (Elsevier)** | Paywall completo |
| **PsycINFO completo (APA)** | Paywall majoritário |
| **IEEE Xplore (subset paywall)** | Subset OA disponível em Tier 1 (via OpenAlex), restante paywall |
| **ACM Digital Library (subset paywall)** | Subset OA disponível em Tier 1 (via OpenAlex), restante paywall |
| **SpringerLink (subset paywall)** | Subset OA disponível, restante paywall |
| **Elsevier ScienceDirect** | Paywall majoritário |
| **Wiley Online Library** | Paywall majoritário |
| **CINAHL completo** | Paywall via EBSCO |

**Política operacional para Tier 3:**

- O ghostwriter **NÃO faz busca direta** em Tier 3.
- Quando o usuário tem acesso institucional, pode **exportar resultados de busca** (CSV/RIS) e fornecer ao ghostwriter como input.
- Quando o usuário tem PDF específico (paywall mas obtido legalmente via biblioteca), pode fornecer.
- O pacote Zenodo declara explicitamente quais bases Tier 3 foram consultadas via fornecimento manual.

---

## Implementação no engine de busca

### Hierarquia operacional

```
1. Tier 1 — buscar SEMPRE; buscar primeiro.
2. Tier 2 — buscar SEMPRE; busca depois de Tier 1; declarar limitações de full-text.
3. Tier 3 — só consultar se usuário fornecer materiais (não busca direta da ferramenta).
```

### Transparência ao usuário

O ghostwriter, ao iniciar busca, declara explicitamente:

> "Vou buscar em Tier 1 ([n] bases) e Tier 2 ([m] bases). Tier 3 ([k] bases) não será consultado a menos que você forneça material exportado de sua instituição. Quer prosseguir, ajustar bases, ou fornecer material Tier 3 antes de começar?"

Após busca:

> "Encontrei [X] estudos em Tier 1 (full-text acessível), [Y] em Tier 2 (apenas metadados; full-text requereria acesso institucional ou fornecimento), e [Z] em material Tier 3 que você forneceu. O pacote Zenodo declarará isso explicitamente."

### Coerência com modos

| Modo | Tiers consultados |
|---|---|
| 1 (Scoping) | Tier 1 + 2; Tier 3 apenas via fornecimento |
| 2 (Rapid) | Tier 1 (mínimo 1 base) + grey lit OA |
| 3 (Mapping) | Tier 1 + 2; Tier 3 frequentemente exigido em CS/SE — usuário fornece |
| 4 (SR estrito) | Tier 1 + 2 + Tier 3 frequentemente OBRIGATÓRIO via fornecimento |
| 5 (Software Paper) | n/a (não é revisão) |
| 6 (Position Paper) | Tier 1 + 2 (busca complementar) |
| 7 (Technical Report) | variável |
| 8 (White Paper) | Tier 1 + grey literature |
| 9 (Integrative) | Tier 1 + 2 |
| 10 (Realist) | Tier 1 + 2 (multi-domínio) |

---

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-05-02 | Criação. 3-tier architecture. Lista de bases por tier. Política operacional de transparência. |
