# Panorama dos 8 modos do ghostwriter ignorantia v2.1

> **Objetivo deste documento.** Apresentar ao usuário, ANTES da escolha do modo de trabalho, todas as exigências de cada modo em três layers: (1) o modo em si, (2) o reporting guideline aplicável, (3) o venue alvo padrão e alternativas. Evita o cenário "tropeçar num eliminatório no meio do trabalho".
>
> **Quando consultar.** Ao iniciar qualquer trabalho com o ignorantia, antes de escolher o modo. Também quando reconsiderar mudança de modo durante a produção.
>
> **Versão.** v2.1 — 2026-05-02. Atualizar quando novos modos forem adicionados.

---

## Hierarquia: Primária, Secundária, Terciária

A ferramenta tem três tipos de modo, com naturezas e exigências de recursos humanos diferentes:

### Camada Primária — você sozinho + pesquisa bibliográfica autônoma

A ferramenta busca em bases OA (Tier 1 + Tier 2) e produz síntese/mapeamento da literatura encontrada. **O ghostwriter trabalha sozinho** com bases públicas. O usuário fornece o tema e o framework de pergunta (PICO, PCC, PICOC, SPIDER, CMO, etc.) e revisa a saída como single-reviewer (com AI dual-check quando o reporting guideline exigir).

- Modo 1: AI-Assisted Scoping Review (PRISMA-ScR + JBI Manual cap. 11)
- Modo 2: AI-Assisted Rapid Review (PRISMA-RR + Cochrane Rapid Reviews Methods Group)
- Modo 3: AI-Assisted Systematic Mapping Study (Petersen 2015 + ACM SIGSOFT Empirical Standards; Kitchenham guidelines como alternativa em CS/SE)
- Modo 9: AI-Assisted Integrative Review (Whittemore & Knafl 2005 + Toronto & Remington 2020)
- Modo 10: AI-Assisted Realist Review (RAMESES II — Wong et al. 2013, 2014)

### Camada Secundária — você sozinho + material que você fornece

A ferramenta exige **material de entrada** que o usuário traz (software pronto, tese argumentativa, dados de processo, problema de política pública). O ghostwriter organiza, redige, valida — pode fazer pesquisa bibliográfica complementar para suportar argumentos, sempre em bases OA, mas o produto principal não é pesquisa bibliográfica.

- Modo 5: Software Paper (JOSS padrão; software prévio obrigatório)
- Modo 6: Position Paper / Theoretical Essay (Zenodo + preprint padrão; tese argumentativa fornecida pelo usuário)
- Modo 7: Technical Report (Zenodo/arXiv padrão; dados/processos fornecidos pelo usuário)
- Modo 8: White Paper / Policy Brief (Zenodo padrão; problema + recomendações fornecidas pelo usuário)

### Camada Terciária — exige ≥1 humano adicional qualificado

Modos que **não podem ser executados pelo usuário sozinho** porque o reporting guideline aplicável exige independência humana entre revisores (não substitutível por AI dual-check).

- Modo 4: Systematic Review estrito (PRISMA-2020 + MECIR + kappa documentado entre 2 revisores humanos com ORCID e identidades verificáveis)

**Implicação para o fluxo do usuário**: a ferramenta NÃO oferece o Modo 4 como recomendação default. Ele só é apresentado quando o usuário declara explicitamente que tem segundo revisor humano qualificado disponível, ou quando pergunta especificamente sobre SR estrita. O eliminatório E16 garante essa separação computacionalmente — manuscritos que reivindicam "Systematic Review" sem evidência de 2 revisores são bloqueados.

---

## Tabela comparativa rápida — três layers em uma vista

| Modo | Camada | Revisores humanos exigidos | Custo padrão (OA) | Pré-registro | Bases mínimas | Estudos primários |
|---|---|---|---|---|---|---|
| Scoping Review | Primária | 1 (single-reviewer aceito) | $0 (Zenodo + preprint OA) | OSF (recomendado) | 3 | 30-200 |
| Rapid Review | Primária | 1 (single-reviewer + AI dual-check 100%) | $0 (Zenodo + preprint OA) | OSF (obrigatório) | 1 + grey lit | 10-50 |
| Mapping Study | Primária | 1 (single-reviewer + AI verification) | $0 (Zenodo + preprint OA) | OSF (recomendado) | 3 (CS: ACM DL + IEEE Xplore + Scopus/DBLP) | 50-300 |
| Integrative Review | Primária | 1 (single-reviewer + AI verification) | $0 (Zenodo + preprint OA) | OSF (recomendado) | 3 (saúde: PubMed + LILACS + CINAHL/SciELO) | 15-50 |
| Realist Review | Primária | 1 (single-reviewer + iterative refinement) | $0 (Zenodo + preprint OA) | OSF (recomendado) | 3 (multi-domínio para mecanismos) | 20-80 |
| Systematic Review (estrito) | **Terciária** | **2 humanos** (kappa documentado) | $0 (Zenodo) ou venue Q1 hybrid (~$3k+) | PROSPERO **obrigatório** | 5+ | 20-80 |
| Software Paper | Secundária | 1 (autor) + peer review JOSS aberto | $0 (JOSS) | n/a | n/a (5-15 refs comparativas) | n/a |
| Position Paper | Secundária | 1 (autor) | $0 (Zenodo + preprint OA) | n/a | n/a (10-30 refs argumentativas, busca complementar OA) | n/a |
| Technical Report | Secundária | 1 (autor) | $0 (Zenodo / arXiv) | n/a | n/a (variável) | n/a |
| White Paper | Secundária | 1 (autor) | $0 (Zenodo / OSF / SciELO Preprints / SSRN) | n/a | 1-3 + grey lit | 10-30 fontes |

> Tempo estimado típico de produção do ghostwriter para qualquer modo: **~15 minutos** (estimativa do usuário, ainda não validada empiricamente em produção real). Campo formal em cada perfil: `time_to_produce_estimate: "user_estimate_15min_unvalidated"`.

---

## Detalhe por modo

Cada um dos 10 modos tem um documento próprio com exigências completas em três layers:

- [Modo 1 — Scoping Review](./mode-01-scoping-review.md)
- [Modo 2 — Rapid Review](./mode-02-rapid-review.md)
- [Modo 3 — Mapping Study](./mode-03-mapping-study.md)
- [Modo 4 — Systematic Review (estrito)](./mode-04-systematic-review-strict.md)
- [Modo 5 — Software Paper](./mode-05-software-paper.md)
- [Modo 6 — Position Paper](./mode-06-position-paper.md)
- [Modo 7 — Technical Report](./mode-07-technical-report.md)
- [Modo 8 — White Paper](./mode-08-white-paper.md)
- [Modo 9 — Integrative Review](./mode-09-integrative-review.md)
- [Modo 10 — Realist Review](./mode-10-realist-review.md)

---

## Como decidir qual modo usar

Decisão sequencial:

1. **O usuário tem material prévio próprio que precisa virar documento publicável?**
   - Software pronto, com testes, ≥6 meses de histórico Git → Modo 5 (Software Paper)
   - Tese filosófica/argumentativa para defender → Modo 6 (Position Paper)
   - Dados/processos/relatório técnico interno → Modo 7 (Technical Report)
   - Problema de política pública + recomendações → Modo 8 (White Paper)
   - **Senão**, ir para passo 2.

2. **Qual a urgência da decisão que a pesquisa bibliográfica vai fundamentar?**
   - Urgência alta (decisão de design com prazo, política pública urgente) → Modo 2 (Rapid Review)
   - Urgência média ou baixa, ir para passo 3.

3. **Qual o objetivo da pesquisa bibliográfica?**
   - Mapear extensão e características do que existe (sem julgamento de qualidade) → Modo 1 (Scoping Review) ou Modo 3 (Mapping Study para CS/SE)
   - Sintetizar evidência mista (estudos quanti + quali + teóricos) sob uma narrativa unificada — comum em saúde/educação BR → Modo 9 (Integrative Review)
   - Explicar por que algo funciona, em que contexto, para quem (mecanismos causais) — comum em política pública e educação → Modo 10 (Realist Review)
   - Sintetizar evidência com julgamento de qualidade + meta-análise → Modo 4 (Systematic Review estrito) — **mas exige 2 revisores humanos (Camada Terciária)**

**Regra de ouro**: se o usuário trabalha sozinho e quer a ferramenta produzir o documento, modos 1, 2, 3, 5, 6, 7, 8, 9, 10 são viáveis. Modo 4 (SR estrito, Camada Terciária) só faz sentido se o usuário tem um segundo revisor humano qualificado disposto a fazer screening + extraction independentes com kappa documentado.

---

## Constraints operacionais que afetam todos os modos

### Bases de busca: hierarquia OA-first (Tier 1 → 2 → 3)

A ferramenta prioriza bases de busca por tier:

- **Tier 1 — sempre OA, sempre buscar**: DOAJ, PubMed Central (PMC), arXiv, bioRxiv, medRxiv, EuropePMC, SciELO, OSF Preprints, Zenodo, ERIC OA filter, OpenAlex (com filtro `is_oa=true`), Crossref (com filtro de licença OA), Wikipedia (mapa, não fonte primária).
- **Tier 2 — busca de metadados livre, full-text pode requerer fornecimento**: Crossref geral, OpenAlex geral, Semantic Scholar, Google Scholar (uso limitado por TOS).
- **Tier 3 — apenas via material fornecido pelo usuário**: Scopus, WoS, IEEE Xplore (subset paywall), ACM DL (subset paywall), Elsevier ScienceDirect, Springer, Wiley.

Veja `references/databases/oa-tiers.md` para detalhes técnicos.

### AI Disclosure obrigatória em TODOS os modos

Independente do modo, a ferramenta sempre adiciona seção "Declaration of AI use" / "Declaração de uso de IAG" listando: ferramenta usada, versão, etapas de uso, parâmetros (temperatura, seed quando disponível), e atribuição de responsabilidade humana.

### Conflict of Interest: 5 mitigações Categoria A obrigatórias

Independente do modo:
1. Pré-registro PROSPERO/OSF com timestamp anterior à decisão de design (quando aplicável)
2. Declaração CoI padronizada
3. Seção "Evidência contrária encontrada" (quando aplicável)
4. Categorização `review_purpose` no metadado
5. Pacote de reprodutibilidade Zenodo

### Pacote de reprodutibilidade Zenodo

Todos os 8 modos geram pacote completo: `prompt.md`, `model.txt`, `databases.txt` (quando aplicável), `dois.csv` (quando aplicável), `selecao_log.json` (quando aplicável), `verificacao_dois.json`, `extraction_log.json` (quando aplicável), `ai_disclosure.md`, `reproducibility_manifest.yaml` (com SHA-256), `README.md`.

---

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-05-02 | Criação inicial. 8 modos documentados em três layers. Hierarquia primária/secundária explícita. Tempo estimado de 15 min marcado como `user_estimate_15min_unvalidated`. |
| 1.1 | 2026-05-02 | Hierarquia ajustada para três camadas (Primária / Secundária / Terciária). Adicionados Modo 9 (Integrative Review — Whittemore-Knafl + Toronto-Remington) e Modo 10 (Realist Review — RAMESES II) à Camada Primária. Total de 10 modos. |
| 1.2 | 2026-05-02 | v2.2.0: 3 venues OA INT adicionados (PLOS ONE, F1000Research, Frontiers in Education) — fecha gap crítico de cobertura OA internacional. Antes da v2.2, apenas Campbell era Q1 INT fully OA. Agora há cobertura OA em saúde geral (PLOS ONE), multi-área com peer review aberto (F1000Research), e educação (Frontiers in Education). |
| 1.3 | 2026-05-02 | v2.2.1: 9 venues A2 BR diamond OA adicionados (3 por área-mãe Sucupira: Educação, QR1-Vida+Saúde, QR1-Exatas+Tecnológicas). Total 32 perfis de venue. Decisão 13 (Qualis CAPES em transição) registrada. |
| 1.4 | 2026-05-03 | v2.2.2: vocabulário de tiers OA-first (Decisão 14). 8 perfis fallback em `venues_fallback_br/` (2 tier-2 + 6 tier-3) cobrindo subáreas estritas de Eng, Mat e Física onde o ecossistema editorial brasileiro estruturalmente não comporta tier-1 puro. Engine atualizado para ranquear por `(fallback_tier ASC, score DESC)`. Total 40 perfis de venue. Não inventou oferta — catalogou em tiers o que pesquisas em `/mnt/project/` já documentavam como fallbacks. |
| 1.5 | 2026-05-03 | v2.3.0: 21 perfis A3 BR + B1 BR (17 novos + 4 recalibrados). Decisão 15 (gap estrutural em A3 Exatas/Tec, extensão coerente da Decisão 14): apenas 2 Tier 1 puros (POPE, RBRH); RBIE catalogada como Educação. Recalibração de 4 venues legados (rsp_usp, csc_abrasco, rbie_sbc, pope_sobrapo) conforme Pesquisa Qualis 2021-2024 (Etapa 1 v2.3). Engine atualizado para 5 pastas de perfis. Total 57 perfis. |
| 1.6 | 2026-05-03 | v2.4.0: 11 perfis Q2 INT em `venues_q2_int/`. Decisão 16: pastas `venues_qN_int/` são organizativas (não estratos estritos); quartil real fica em metadata. Cobre as 3 áreas-mãe (Edu: Cogent Education, ETHE, Education Sciences MDPI, Educational Studies; Saúde: BMC Med Education, RLAE, NEP; CS/SE/Eng: IST, JSS, PeerJ CS, IEEE Access). RLAE = único caso identificado de Q2 INT + Tier 1 + brasileiro. Engine atualizado para 6 pastas. Total 68 perfis. **Roadmap v2.x catalogação completo.** Próximo: Etapa 4b (validação empírica). |
| 1.7 | 2026-05-03 | v2.5.0: Etapa 4b infraestrutura. `scripts/comparison/` com clientes (B!SON, JANE scaffold, ASReview, snapshot ingestor), métricas (top-k/MRR/nDCG, WSS@95/recall/ATD, F1/κ), unify+report e schema unificado v1.0.0. 8 smoke tests + 53 regressão = 61/61. Workflow systems (EM, ScholarOne, OJS, eJP) **explicitamente excluídos** com justificativa documentada. Mudança de natureza: deixa de ser expansão de catálogo, passa a ser andaime de avaliação empírica. **Validação empírica continua pendente** — requer SLRs reais. |
| 1.8 | 2026-05-03 | v2.6.0: Tier 0 OA locator legítimo. Decisão 17 (Tier 0 + exclusão de plataformas em disputa judicial): Unpaywall + Open Access Button + fallback de solicitação ao autor. Cobertura ~50M artigos OA. Plataformas em litigância NÃO integradas ao pipeline automatizado; teste mecânico valida ausência de URLs. 3 módulos Python novos em `scripts/searches/`. Flag `--enrich-tier0` no orquestrador. 69/69 testes (61 regressão + 8 v2.6). |
| 1.9 | 2026-05-03 | v2.6.1: Tier 0 automático. Removidas flags opt-in (`--enrich-tier0`, `--tier0-email`, `--tier0-mock`). Adicionadas `--skip-tier0` (offline/CI) e `--contact-email` (fallback `IGNORANTIA_CONTACT_EMAIL`). Princípio: operação legal + resolve problema = default, não opção. 69/69 testes preservados. |
| 1.10 | 2026-05-03 | v2.7.0: gap report + pausa para resolução manual. Decisão 17 reescrita com posição neutra real (`ignorantia` não julga litígios em curso; decisão de como obter material é do usuário). Novo módulo `access_gap_report.py` gera `gap_report.md` listando itens sem OA legítimo; orquestrador pausa com exit code 10; usuário providencia full-texts em `user_provided/` e retoma. Linguagem em `compliance-international.md` neutralizada. 74/74 testes (5 novos validam neutralidade do relatório). |
| 1.11 | 2026-05-03 | v2.7.1: correção editorial — substituição de nomes literais de plataformas em disputa judicial por termos genéricos em todo o projeto. Sem mudança de comportamento. Teste mecânico renomeado para `test_decision_17_excluded_platforms`. 74/74 testes preservados. |
| 1.12 | 2026-05-03 | v2.8.0: release de eliminação (1ª de 3) respondendo à auditoria do RS-42 v1.0.0. Decisões 18 (reservada), 19 (anti-vazamento), 20 (voz autoral padrão / persona), 21 (consentimento implícito Fase 4), 30 (remoção rabiscos for fun), 33 (segredo industrial). Limpeza de meta-discurso em templates HTML e em `render_manuscript.py`. Rubrica D5 reescrita; 9 critérios obsoletos formalmente removidos. 79/79 testes (74 regressão + 5 v2.8). |
| 1.13 | 2026-05-03 | v2.9.0: release de adições obrigatórias (2ª de 3). Decisões 22-29: re-execução por subversão, snowballing backward (Wohlin 2014), Tier 3 → priority_0_routing, 6 adapters ibero-americanos novos (LA Referencia, Redalyc, CLACSO, BDTD, Scioteca, Periódicos CAPES), CORE API, todo elegível com rigor de SR, EN+PT+ES como obrigação, ABNT NBR 6023:2018 + NBR 10520:2023, cross-tabulação obrigatória. 8 módulos Python novos. Cobertura Tier 1 dobrou nas áreas saúde/educação/CS. Nova área `ciencias_sociais`. 101/101 testes (79 regressão + 22 v2.9). |
| 1.14 | 2026-05-03 | v2.10.0: release de outputs (3ª de 3). Decisões 18 (HTML em chunks/append), 31 (.docx ABNT NBR 14724:2011), 32 (.tex + .pdf via pdflatex/xelatex). Snowballing forward via OpenAlex. 4 módulos Python novos. PDF compila com sucesso em TeX Live 2024 com babel[main=brazilian,provide=*]. 115/115 testes (101 regressão + 14 v2.10). Trilha de resposta à auditoria do RS-42 v1.0.0 fechada. |
| 1.15 | 2026-05-03 | v2.10.1: patch de coerência operacional. Auditoria sistemática da v2.10.0 revelou que módulos foram criados mas não integrados ao pipeline. CRIT-1: TIER1_RUNNERS expandido de 5 para 13 adapters. CRIT-2: search_scielo trata 403 graciosamente + --mock. CRIT-3: path absoluto removido em render_v2. CRIT-4: search_doaj.py e search_lilacs.py criados. CRIT-5: novo `pipeline_finalize.py` encadeia os 5 outputs em comando único. IMP-1: vocabulário "Tier 3" → "priority_0_routing" nas mensagens user-facing. IMP-2/3: `manifest_helpers.py` implementa Decisões 21 e 22. IMP-5: rubrica D1 alinhada (snowballing deixa de ser bonificação). 134/134 testes (115 regressão + 19 v2.10.1). Sem nova decisão editorial. |
| 1.16 | 2026-05-03 | v2.10.2: patch de completude de adapters + honestidade declarativa. 7 rodadas técnicas adicionando 10 adapters novos (pubmed_central, europepmc, biorxiv, medrxiv, eric, osf_preprints, edarxiv, zenodo, hal, openalex). TIER_DATABASES reorganizado: redundâncias declarativas removidas (openalex_oa, crossref_oa_filter, pubmed_full, eric_full); nova categoria `unimplementable[]` declara honestamente bases sem API pública (acm_full, ieee_full, ssrn). Disclosure user-facing reescrita com 3 categorias claras (implementadas / inviáveis / priority_0). Cobertura declarada vs implementada agora é 1:1 (antes: 23 declaradas, 13 implementadas). 155/155 testes (134 regressão + 21 v2.10.2). Sem nova decisão editorial. |
| 1.17 | 2026-05-03 | v2.11.0: ascensão a "ghostwriter premium". Análise MoSCoW dos adapters esperados por reviewers Q1/banca/consultoria identificou 19 a implementar — 5 MUSTs + 6 SHOULDs + 8 COULDs (sendo 1 utilitário Fase 8 fora do TIER1_RUNNERS). MUSTs incluem tripé canônico Cochrane Handbook (Cochrane CENTRAL, ClinicalTrials.gov, PubMed completo) + livros OA (OAPEN) + indicadores bibliométricos (Dimensions FWCI/Altmetric). SHOULDs cobrem JSTOR OA, SciELO Preprints, Dialnet, PEPSIC, Catálogo CAPES, Engineering Village (Compendex OA subset). COULDs incluem grey_lit multi-provider (UNESCO/OECD/World Bank/IPEA/INEP/NIST/WHO), PhilArchive, Spell, REDIB, E-LIS, ProQuest OA, DABI, e jane (classificador de venue). 2 áreas novas em TIER_DATABASES: humanidades e business. TIER1_RUNNERS quase dobrou (23 → 41). 189/189 testes (155 regressão + 34 v2.11.0). Sem nova decisão editorial. |
| 1.18 | 2026-05-03 | v2.11.1: patch de registro de decisões. Cria 3 arquivos de governança (`references/DECISIONS.md`, `references/WONT_IMPLEMENT.md`, `references/IMPLEMENTATION_STRATEGY.md`). DD-5 (WON'T da v2.11.0) parcialmente revogada por DD-7: 14 publishers paywall tornam-se implementáveis sob nova premissa "acesso via mecanismo legal do usuário"; ResearchGate + Academia.edu permanecem WON'T por DD-6 (ToS proíbe). Estratégia de 8 rodadas (v2.12 a v2.18) registrada e em curso. Sem código novo de adapter; preparação para R2-R8. |
| 1.19 | 2026-05-04 | v2.15.0: adapters paywall com cascata legal. Consolida R2-R6 da estratégia v2.11.1. 16 adapters criados: Elsevier x3 (Scopus/ScienceDirect/Embase), publishers grandes x4 (Springer/Wiley/IEEE/WoS), APA-EBSCO-JSTOR-Sage x4, sem-API x4 (ACM/SSRN/Hein/ProQuest), Google Scholar via SerpApi. Template arquitetural `_adapter_base.py` com cascata `KEY → PROXY → FALLBACK_MD → MOCK` (DD-8). Sem credencial, gera `citations_to_obtain_<base>.md` com instruções CAFe. TIER_DATABASES reorganizado com nova categoria `tier2_paywall` por área; bases que estavam em `priority_0_routing` ou `unimplementable` migraram quando cascata é viável. Disclosure user-facing v2.15.0 mostra 4 categorias (Tier 1, Tier 2, Tier 2 paywall, Inviáveis). TIER1_RUNNERS: 57 (era 41). 222/222 testes (189 regressão + 33 v2.15.0). Bases inviáveis: 1 (era 5). DD-10 (logs detalhados) e DD-11 (Wikipedia preâmbulo) ainda pendentes para v2.17/v2.18. |
| 1.20 | 2026-05-04 | v2.18.0: fechamento da estratégia v2.11.1. Consolida R7 (DD-10 logs) + R8 (DD-11 preâmbulo). 3 módulos novos: `scripts/searches/_log_enrichment.py` (pós-processador Camada 1 — fetched/kept/discarded_local em JSON Lines, integrado ao orquestrador), `scripts/screening_pipeline.py` (Camada 2 — screening 3 estágios title/abstract/full_text com CSV PRISMA-compatible + counts JSON), `scripts/contextual_preamble.py` (Wikipedia + Wikidata para seção "O campo onde este artigo vive" distinta da Introdução, em HTML/Markdown/JSON/PPTX, citações ABNT NBR 10520 com data de acesso, suporte PT-BR/EN/ES). 243/243 testes (222 regressão + 21 v2.18.0). Todas as 12 DDs implementadas. As 8 rodadas v2.11-v2.18 estão entregues. |
| 1.21 | 2026-05-04 | v2.19.0: release de auditoria — fechamento dos 17 achados em 4 sprints. S1 (P0 críticos): F1 contextual_preamble.py reescrito (UA compliant Wikimedia + wbsearchentities + warnings), F2 SKILL.md atualizado com seção "Arquitetura v2.15-v2.18", F3 README estável (saiu de alpha), F4 integração de contextual_preamble aos 3 renderers (HTML, docx ABNT, LaTeX). S2 (P1): F5 screening_pipeline como Etapa 6 do pipeline_finalize + manifest tracking, F6 bug grey_lit corrigido (7 providers iterados), F7 mock dos PaywallAdapter inclui log_camada1. S3 (P2): F8 datetime.utcnow → now(timezone.utc) em 9 arquivos, F9 import logging removido, F10 comentário wiley_tdm corrigido, F11 lareferencia → la_referencia, F12-F13 documentação honesta sobre cobertura logs e credencial institucional. S4 (P3): F15 parser RSS real para search_la_referencia.py via xml.etree.ElementTree (saiu de _REAL_PARTIAL), F16 testes integração com mock urllib. 266/266 testes (243 → +16 v2.18.1 + 7 v2.19.0). Pipeline_finalize: 6 etapas (era 5). |
| 1.22 | 2026-05-04 | v2.20.0: release de auditoria iterativa #2 — fechamento dos 9 achados em 3 sprints. H1 (P0): A1 version stamps, A2 conversor Markdown→LaTeX completo (\textit, \textbf, itemize, \href), A3 arxiv aceita --year-start/--year-end (era silenciosamente excluído via orquestrador). H2 (P1): A4 SKILL.md com seção quantitativa (57 runners, 61 adapters, 6 etapas, 270+ testes), A5 DOIs mock la_referencia padronizados, A6 --mock retrofit em arxiv/crossref/dblp/semantic_scholar. H3 (P2/P3): A7 grey_lit stderr, A8 arxiv backoff 429, A9 parser HTML LILACS via regex conservadora. 291/291 testes (266 → +25 v2.20.0). REAL_PARTIAL: 16 (era 17). |
| 1.23 | 2026-05-04 | v2.21.0: release de auditoria iterativa #3 — fechamento dos 13 achados em 3 sprints. T1 (P0 vitrine quebrada arquitetural): B1 pipeline_finalize propaga preâmbulo aos 3 renderers, B2 render_chunks integra preâmbulo (era o usado pelo pipeline mas não tinha F4), B3 docstring 6 outputs, B5 SKILL.md placeholder, B6 docstring la_referencia. T2 (P1 + E2E): B4 schema unificado total_results, B8 ResourceWarnings 182→2, B11 render_manuscript DEPRECATED, B13 16 testes E2E pipeline_finalize via subprocess. T3 (P2/P3): B7 parser real Redalyc via JSON+HTML fallback (sai REAL_PARTIAL), B9 asteriscos órfãos documentados, B10 renderer canônico documentado, B12 AUDIT_LOG consolidado em references/audits/. 307/307 testes (291 → +16 v2.21.0). REAL_PARTIAL: 15 (era 16). |
| 1.24 | 2026-05-04 | v2.22.0: release de auditoria iterativa #4 — fechamento dos 8 achados em 3 sprints. U1 (P1 coerência): C1+C2 schema unificado nos 4 retrofitted (year_range top-level + year/language/is_oa/doi item-level), C4 README com 8 contadores quantitativos, C5 render_manuscript emite DeprecationWarning runtime. U2 (P1 parsers ibero Decisão 25): C3.1 CLACSO parser DSpace, C3.2 Dialnet parser HTML público, C3.3 PePSIC reusa LILACS parser, C3.4 SciELO Preprints parser OJS. U3 (P2/P3): C6 bdtd/scioteca/grey_lit declaram REAL_PARTIAL, C7 CHANGELOG cross-doc path, C8 DD-13 renderer canônico (12→13 DDs). 325/325 testes (307→+18 v2.22.0). REAL_PARTIAL: 11 (era 15). Bug auto-detectado por teste pré-existente: def search() removida em search_dialnet.py por str_replace; restaurada. |
| 1.25 | 2026-05-04 | v2.23.0: release de auditoria iterativa #5 + análise SOLID/DRY. TDD: 34 testes ANTES dos fixes. W1 (P0): D3 paridade mock vs real nos 4 retrofitted (parse_entry/normalize reais ganham language/is_oa/url/venue), E1 source_tier sempre str canônica (Liskov violation resolvida em 58 adapters), D5 helper cli_exit_with_error_message em 35 adapters. W2 (P1): D1+D2 schema legacy unificado (year_range em 20 adapters; SciELO modernizado), E2 USER_AGENT centralizado via _skill_version.py (10 → 1 valor), E6 AdapterMethod enum. W3: D6 orchestration_summary.json, DIM 4 contadores corrigidos. W4: E10 pipeline_finalize com PIPELINE_STEPS registry (Open/Closed). 359/359 testes. Adicionado: V3_ARCHITECTURE_PLAN.md detalhando Clean Architecture/DDD/bounded contexts para v3.0.0; cowork adiado para v4. |
