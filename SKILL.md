---
name: ignorantia
description: Constrói base de conhecimento via revisão sistemática/scoping/rapid/integrative/realist/mapping da literatura (PRISMA-2020/PRISMA-ScR/PRISMA-RR conforme o modo, com flow diagram, quality appraisal e extração tabulada efetivamente executados; ACM SIGSOFT Empirical Standards para engenharia de software) do protocolo ao manuscrito final. Saída é HTML auto-contido e interativo (busca/filtros, D3.js, anotações com toggle, dark mode, refs clicáveis), versionado em SemVer e imutável. pt-BR usa ABNT; EN usa IEEE (exatas), Vancouver (saúde), APA (psicologia/educação). 10 modos hierárquicos: scoping, rapid, mapping, integrative, realist, SR (2 revisores), software paper (JOSS), position paper, technical report, white paper. USE quando o usuário disser "ignorantia", pedir SLR, scoping/rapid/mapping/integrative/realist review, software/position paper, technical report, white paper, policy brief, estado da arte, metanálise, PRISMA, Kitchenham, ou artigo acadêmico que requer base bibliográfica e diagrama PRISMA.
---

# ignorantia

> *"Ignorantia non est argumentum."* — Spinoza, *Ética*, I, Apêndice
>
> Combatir a ignorância sobre um tema atual é o objetivo deste skill: construir, na forma de artigo do mais alto nível, uma base sólida de conhecimento — reprodutível, auditável, versionada, e visualmente envolvente para o leitor.

## Filosofia operacional

1. **Honestidade epistêmica.** O ponto de partida é a ignorância declarada do usuário. O skill não simula domínio que não tem; busca, lê, sintetiza, e reporta o que a literatura realmente diz, com limites explícitos.
2. **Rigor metodológico não-negociável.** PRISMA-2020 é executado, não apenas citado. Flow diagram, quality appraisal CASP/DARE, extração tabulada — todos os elementos saem do skill como artefatos reais, não como prosa que descreve o que deveria ter sido feito.
3. **Imutabilidade de saídas.** Cada manuscrito é uma versão SemVer fechada. Quando há mudança, gera-se nova versão; a anterior permanece intacta. Versões antigas são parte do registro científico.
4. **Auditabilidade.** Toda referência citada no manuscrito é um link clicável que vai à fonte primária (DOI, arXiv, ou URL canônica). O leitor (incluindo os dois professores que farão a revisão no Zenodo) consegue verificar tudo em um clique.
5. **Engajamento do leitor.** Forma e fundo importam. Gráficos D3.js dinâmicos, tabelas filtráveis, anotações estilo professor que aparecem por toggle, dark mode — tudo a serviço de manter o leitor dentro do conteúdo o tempo todo.

## Auditoria sistemática

A skill é mantida via auditorias iterativas. Para evitar redescoberta de categorias de bugs, **`references/audits/AUDIT_PROCEDURE.md`** documenta as **27 dimensões conhecidas** de erro em 7 camadas (correção, convenções, especificação, reprodutibilidade, compatibilidade, segurança, lifecycle). Uma rodada de auditoria que cubra todas as dimensões substitui ~5 rodadas improvisadas. Histórico das auditorias em `references/audits/AUDIT_LOG.md`.

## Estado quantitativo da skill (v2.20.0)

A skill em sua versão atual (v2.20.0) tem o seguinte estado quantitativo, exposto aqui para rastreabilidade direta sem necessidade de inspecionar CHANGELOG ou journal:

- **62 adapters de busca** em `scripts/searches/search_*.py` (16 paywall + 45 OA/metadados/grey).
- **57 TIER1_RUNNERS** registrados em `search_orchestrator.TIER1_RUNNERS`. Cinco arquivos `search_*.py` adicionais não estão no dict do orquestrador por design (`search_jane`, `search_oa_button`, `search_periodicos_capes`, `search_unpaywall` — utilitários complementares; `search_orchestrator` é o próprio orquestrador).
- **7 áreas** suportadas: saude, educacao, cs_se, ciencias_sociais, humanidades, business, multi.
- **6 etapas** no `pipeline_finalize.py` (cross_tab, format_abnt, render_html_chunks, render_docx_abnt, render_latex, screening_pipeline). A Etapa 6 foi adicionada em v2.19.0 (F5 da auditoria).
- **291+ testes** com regressão verde a cada release (v2.18.0: 243; v2.18.1: +16 = 259; v2.19.0: +7 = 266; v2.20.0: +25 = 291; v2.21.0: +16 = 307; v2.22.0: +18 = 325).
- **33 decisões editoriais** em `references/DECISIONS.md` (Decisões 1-33).
- **13 decisões de design (DD)** todas implementadas (DD-1 a DD-13). DD-10 (logs em duas camadas) tem asterisco honesto: Camada 1 nativa só nos 16 paywall; legados via pós-processador do orquestrador. DD-13 (v2.22.0) consolida decisão sobre renderer HTML canônico (`render_chunks.py`) vs alternativo (`render_v2.py`).
- **3 módulos auxiliares** em `scripts/searches/`: `_adapter_base.py`, `_log_enrichment.py`. Mais 2 standalone em `scripts/`: `screening_pipeline.py`, `contextual_preamble.py`.

Cobertura média por área (TIER_DATABASES): tier1=13, tier2=4, paywall=6, total funcional ≈ 23 bases por busca.

## Arquitetura v2.15-v2.18 — cobertura premium, logs, preâmbulo

### Cascata `KEY → PROXY → FALLBACK_MD → MOCK` (Decisão DD-8, v2.15.0)

A skill cobre 16 bases pagas (Scopus, Web of Science, ScienceDirect, Embase, Springer Nature, Wiley TDM, IEEE Xplore, APA PsycInfo, EBSCO CINAHL, JSTOR full, Sage TDM, ACM Digital Library, SSRN, Hein Online, ProQuest full, Google Scholar via SerpApi) através de adapters que herdam de `scripts/searches/_adapter_base.py:PaywallAdapter`. Os adapters concretos são: `search_scopus_full.py`, `search_wos_full.py`, `search_sciencedirect_full.py`, `search_embase.py`, `search_springer_full.py`, `search_wiley_tdm.py` (chave `wiley_full`), `search_ieee_full.py`, `search_psycinfo_full.py`, `search_cinahl_full.py`, `search_jstor_full.py`, `search_sage_full.py`, `search_acm_full.py`, `search_ssrn_full.py`, `search_hein_online.py`, `search_proquest_full.py`, `search_google_scholar_serpapi.py` (chave `google_scholar`). Cada adapter implementa cascata em ordem rigorosa:

1. **`KEY` mode**: lê env var (`ELSEVIER_API_KEY`, `IEEE_API_KEY`, `SPRINGER_API_KEY`, `CLARIVATE_API_KEY`, `WILEY_TDM_KEY`, `SERPAPI_KEY`, etc.) ou argumento `--api-key`; usa API oficial.
2. **`PROXY` mode**: lê `IGNORANTIA_PROXY_HOST` ou argumento `--proxy-host`; usa proxy institucional do usuário (ezproxy, OpenAthens, CAFe).
3. **`FALLBACK_MD` mode**: gera `citations_to_obtain_<source>.md` com lista cruzada de itens (DOI, ISSN, ISBN, título, ano, autores) descoberta via Crossref/OpenAlex filter por publisher, mais 4 opções de obtenção (Periódicos CAPES com CAFe, biblioteca institucional, contato com autor correspondente, COMUT).
4. **`MOCK` mode**: fixtures determinísticas para testes/CI.

**Princípio honesto**: o adapter NÃO pula direto para fallback. Tenta KEY → PROXY antes. Sem credencial, gera o `.md` declarativo — usuário tem documento estruturado com instruções para baixar manualmente.

**ResearchGate, Academia.edu permanecem fora** (DD-6: ToS proíbe scraping; sem API). Cobertura funcional via Unpaywall + CORE + OpenAlex (DD-9), que cobrem o mesmo conjunto de PDFs auto-arquivados com identificadores estáveis.

### Disclosure user-facing v2.15.0

Mensagem pré-busca declara 4 categorias:
1. **Tier 1** (OA gratuito, full-text)
2. **Tier 2** (metadados livres)
3. **Tier 2 paywall** (cascata KEY→PROXY→FALLBACK_MD)
4. **Inviáveis automaticamente** (raras agora; apenas EBSCO Business Source full)

### Logs em duas camadas (Decisão DD-10, v2.17.0)

**Camada 1 — Adapter** (busca): cada `results_<source>.json` é acompanhado de `logs/logs_<source>.jsonl` gerado automaticamente pelo orquestrador via `scripts/searches/_log_enrichment.py`. Eventos: `fetched`, `kept_after_local_filter`, `discarded_local` com razões técnicas (`out_of_temporal_window`, `language_not_accepted`, `missing_doi`). Adapters paywall (`PaywallAdapter`) já têm log nativo via `LocalFilter`; o pós-processador preserva via `native_log_camada1_from_adapter`.

**Camada 2 — Screening** (Fase 4 PRISMA-2020): `scripts/screening_pipeline.py` registra decisões em 3 estágios sequenciais (`title` → `abstract` → `full_text`) em `screening_log.csv` com schema `study_id,doi,stage,decision,reason,reviewer,timestamp`. Reviewer types suportados: `human`, `ai_single`, `ai_dual`, `ai_assisted_human`. Saída adicional `screening_counts.json` é compatível com PRISMA-2020 flow diagram.

### Preâmbulo contextual Wikipedia/Wikidata (Decisão DD-11, v2.18.0)

`scripts/contextual_preamble.py` gera seção **"O campo onde este artigo vive"** distinta da Introdução do paper. Não é adapter de busca; é módulo de render para audiência leiga (banca multidisciplinar, leitor de white paper). Roda na Fase 7 (síntese), antes do render final.

**Fontes**: Wikipedia REST API + Wikidata `wbsearchentities` + sitelinks. Citações ABNT NBR 10520 com data de acesso e link clicável: `(WIKIPEDIA, "Termo", acesso em 2026-05-04)` e `(WIKIDATA QXXXX, "label", acesso em 2026-05-04)`.

**Outputs**: HTML (`<section id="contextual-preamble">`), Markdown (`## O campo onde este artigo vive`), JSON, e estrutura PPTX para integração com `python-pptx`.

**User-Agent compliant Wikimedia**: a skill respeita a [User-Agent policy](https://api.wikimedia.org/wiki/Documentation/Conventions/User-Agent_policy) — definir `IGNORANTIA_CONTACT_EMAIL` no ambiente para production-grade access.

**Limitação honesta**: Wikipedia não é fonte primária; é acessório explicativo. Toda afirmação metodologicamente relevante ainda deve vir de literatura peer-reviewed na Introdução/Fundamentação. Para temas muito recentes, Wikipedia pode não ter cobertura adequada — o módulo declara isso via `<p class="contextual-warning">`.

## Decisões editoriais v2.0 — três modos de saída e mitigações

> **Registro central de decisões:** Para o registro canônico de **todas** as decisões editoriais e de design da skill (incluindo decisões de arquitetura de adapters, ToS, e estratégia de implementação), consultar `references/DECISIONS.md`. Para o registro de plataformas que NÃO serão implementadas e razões técnicas, consultar `references/WONT_IMPLEMENT.md`. Para a estratégia de rodadas em curso, consultar `references/IMPLEMENTATION_STRATEGY.md`.

Estas decisões são **vinculantes em toda execução do skill em modo v2.0**:

### Decisão 1 — Modos de saída do ghostwriter (revisado em v2.1)

O termo **"systematic review" é reservado APENAS** para casos com dois revisores humanos validados (com kappa documentado e identidades verificáveis). Em todos os demais casos, o skill produz e rotula explicitamente um dos modos abaixo, organizados em três camadas hierárquicas (ver Decisão 10 v2.1 para a hierarquia completa):

**Camada Primária (você sozinho + busca autônoma):**
- **AI-Assisted Scoping Review** (default exploratório) — segue PRISMA-ScR (Tricco et al. 2018) + JBI Manual cap. 11. Single-reviewer permitido com transparência total.
- **AI-Assisted Rapid Review** (default decisional) — segue PRISMA-RR (Stevens et al. 2024) + Cochrane Rapid Reviews Methods Group. Single-reviewer com AI-assistance é explicitamente o caso para o qual a guideline foi concebida.
- **AI-Assisted Systematic Mapping Study** (default CS/SE) — segue Petersen et al. 2015 + ACM SIGSOFT Empirical Standards.
- **AI-Assisted Integrative Review** (v2.1, default saúde/educação BR com literatura mista) — segue Whittemore & Knafl 2005 + Toronto & Remington 2020.
- **AI-Assisted Realist Review** (v2.1, default para perguntas sobre mecanismos causais em programas complexos) — segue RAMESES II (Wong et al. 2013).

**Camada Terciária (exige 2 revisores humanos):**
- **Systematic Review estrito** — exige PRISMA-2020 + 2 revisores humanos com ORCID + kappa documentado.

A v2.1 também adicionou modos da **Camada Secundária** (você sozinho + material que você fornece): Software Paper, Position Paper, Technical Report, White Paper. Ver Decisão 10 para detalhes completos.

O skill **NUNCA chama de "systematic review"** sem evidência de dois revisores humanos. Eliminatório E16 bloqueia esse uso indevido em todos os 18 valores válidos de `review_type` (constante `VALID_REVIEW_TYPES_V21` em `scripts/assessor/eliminators.py`).

### Decisão 2 — Pacote de reprodutibilidade Zenodo obrigatório

Toda revisão depositada no Zenodo deve ser acompanhada de pacote completo:

- `prompt.md` — prompts completos de cada fase
- `model.txt` — provider, modelo, versão, temperatura, top_p, seed
- `databases.txt` — bases consultadas + queries exatas + datas
- `dois.csv` — DOIs antes da filtragem (raw search results)
- `selecao_log.json` — inclusões/exclusões com critério aplicado
- `verificacao_dois.json` — cross-check Crossref + Retraction Watch + OpenAlex
- `extraction_log.json` — cada extração documentada
- `ai_disclosure.md` — declaração ICMJE/IEEE-compliant
- `reproducibility_manifest.yaml` — SHA-256 de cada arquivo
- `README.md` — instruções para reproduzir

Implementação: módulo `scripts/zenodo/`. Verificação automática de DOIs via Crossref REST API + Retraction Watch + OpenAlex é **obrigatória pré-publicação**. DOIs alucinados ou retratados → eliminatório E10 (já existente, agora com camada de verificação automática).

### Decisão 3 — Preprint server semi-automático

Após gerar o pacote Zenodo, o skill propõe **um preprint server primário** (e 1-2 alternativos) com base na área do manuscrito, explica ao usuário a escolha + as alternativas descartadas (com a política de IA de cada um), e aguarda confirmação. **A submissão é manual**, feita pelo usuário com orientação do skill.

Mapeamento por área:
- Educação → EdArXiv
- Psicologia → PsyArXiv
- Saúde/Medicina → medRxiv
- Biologia → bioRxiv
- CS/SE → arXiv (cs.SE, cs.CL, cs.HC)
- Ciências Sociais multi → SSRN
- Direito → LawArXiv (subset SSRN)
- Humanidades → Humanities Commons
- Multi-área Latam → SciELO Preprints
- Genérico → Research Square

### Decisão 4 — Dois modos de Forma

- **Modo "Preprint/Zenodo"** (default na fase atual): aplicar normas área-padrão — Saúde Vancouver + PRISMA-2020; Educação APA-7 + reporting guideline; CS/SE IEEE/ACM + ACM SIGSOFT Empirical Standards; Brasil PT-BR ABNT.
- **Modo "Venue-Specific"** (quando venue alvo declarado): sobrescrever com normas do publisher mantendo o conteúdo do reporting guideline.

A Forma muda; o Conteúdo (rigor metodológico, PRISMA itens) é invariante.

### Decisão 5 — Monitoramento EQUATOR Network

O arquivo `references/equator-monitoring.md` lista as guidelines de IA emergentes (PRISMA-AI, TRIPOD-AI, CHART, CONSORT-AI, SPIRIT-AI, etc.). Job mensal verifica atualizações. Quando uma guideline relevante for publicada, abrir issue obrigatória para incorporação à v2.x.

### Decisão 6 — "Living review" reservado a protocolo formal

O termo **"living review"** é reservado a casos que cumprem o protocolo formal Cochrane/Campbell (atualização ≥quadrimestral, PRISMA-LSR, novo PROSPERO ou OSF tracking). Em todos os demais casos, o skill usa **"periodically updated review"** ou **"time-bounded review (search closed YYYY-MM-DD)"**.

### Decisão 7 — Idiomas v2.0

- **Geração** (ghostwriter): primário inglês (alvo internacional); secundários português e espanhol.
- **Avaliação** (compliance): suporta os mesmos três idiomas.
- **Mandarim, árabe, japonês, coreano**: roadmap v2.x+, exigem parsers específicos.

### Decisão 8 — Mitigações de conflito de interesse — Categoria A (5 itens) obrigatórios

Toda revisão produzida pelo skill deve incluir, sem exceção:

1. **Pré-registro PROSPERO/OSF com timestamp** antes da decisão de design (template gerado pelo skill).
2. **Declaração CoI padronizada** identificando o projeto subjacente, tipo de relação, e timing review-vs-design.
3. **Seção obrigatória "Evidência contrária encontrada"** — declarar achados que contradizem decisões de projeto, ou declarar honestamente que nenhum foi identificado.
4. **Categorização `review_purpose`** no metadado: `design_foundational | design_validation | design_correction | independent_inquiry`.
5. **Pacote de reprodutibilidade Zenodo** completo (Decisão 2).

Mitigações de Categoria B (vinculação bidirecional, auditoria periódica, open peer review) são **decisões editoriais do autor**, fora do escopo do skill. Documentadas em `references/user-guidance/post-deposit-actions.md`.

### Decisão 9 — Sprint Badge marcado como experimental/preview

O Sprint Badge atual (calibrado com n=187 SLRs em v1.x) é mantido na v2.0 mas explicitamente rotulado como **experimental/preview**. Calibração definitiva (regressiva SJR+JIF, n=1.600-3.200) é alvo da v3.0 no Cowork. O whitepaper preliminar está em `references/draft/whitepaper-PRELIMINARY.md` com aviso explícito.

### Decisão 10 — Dez modos de saída em hierarquia tripla (v2.1)

A v2.1 expande de 4 para 10 modos de saída do ghostwriter, organizados em três camadas hierárquicas baseadas no critério de quem precisa estar presente para executar honestamente o modo:

**Camada Primária — você sozinho + pesquisa bibliográfica autônoma em bases OA (Tier 1+2):**
1. AI-Assisted Scoping Review (PRISMA-ScR)
2. AI-Assisted Rapid Review (PRISMA-RR)
3. AI-Assisted Systematic Mapping Study (Petersen + SIGSOFT)
9. AI-Assisted Integrative Review (Whittemore-Knafl + Toronto-Remington)
10. AI-Assisted Realist Review (RAMESES II)

**Camada Secundária — você sozinho + material que você fornece à ferramenta:**
5. Software Paper (JOSS-aligned)
6. Position Paper / Theoretical Essay (Toulmin/Walton-inspired)
7. Technical Report (ANSI/NISO Z39.18)
8. White Paper / Policy Brief (Brookings/RAND/Carnegie/ICCT-style)

**Camada Terciária — exige ≥1 humano adicional qualificado (não pode ser executado sozinho):**
4. Systematic Review estrito com 2 revisores (PRISMA-2020 + MECIR + kappa documentado)

A ferramenta NÃO oferece o Modo 4 como recomendação default. Ele só é apresentado quando o usuário declara explicitamente que tem segundo revisor humano qualificado disponível, ou quando pergunta especificamente sobre SR estrita. O eliminatório E16 garante essa separação computacionalmente.

Cada modo tem perfil individual detalhado em três layers (modo + reporting guideline + venue padrão+alternativas) em `references/modes/mode-XX-*.md`. O panorama master está em `references/modes/MODES_OVERVIEW.md`.

### Decisão 11 — Política OA-first (3 tiers de bases)

A v2.1 formaliza a constraint operacional de que o ghostwriter SÓ consulta bases gratuitas (Tier 1) e bases com metadados livres (Tier 2). Material atrás de paywall (Tier 3) só é acessado via fornecimento manual pelo usuário (CSV/RIS exportado da instituição, PDFs específicos, etc.).

- **Tier 1 — sempre OA, sempre buscar.** PubMed Central, EuropePMC, LILACS, SciELO, ERIC OA, arXiv, DBLP, DOAJ, OpenAlex (`is_oa=true`), Crossref (filtro OA), OSF Preprints, Zenodo, etc.
- **Tier 2 — metadados livres, full-text pode requerer fornecimento.** Crossref geral, OpenAlex geral, Semantic Scholar, PubMed completo, etc. O ghostwriter declara explicitamente quando full-text não acessível.
- **Tier 3 — apenas via material fornecido pelo usuário.** Scopus, Web of Science, Embase, IEEE Xplore subset paywall, ACM DL subset paywall, Elsevier ScienceDirect, etc.

Cada modo declara os mínimos esperados de bases Tier 1 (e quando aplicável, se Tier 3 via fornecimento é praticamente exigido). O orquestrador `scripts/searches/search_orchestrator.py` aplica a política e gera disclosure ao usuário pré- e pós-busca. Detalhes completos em `references/databases/oa-tiers.md`.

### Decisão 12 — Padrão de venues OA-first com alternativas explicadas

Para cada modo, a ferramenta apresenta:

1. **Venue padrão**: OA-gratuito ($0 APC) ou de baixo custo, área-fit. Exemplos: JOSS para Software Paper; Zenodo para Position/Technical/White Paper; Qualis A1 BR fully OA (Cadernos de Saúde Pública, Educação e Pesquisa) para Scoping/Integrative/Realist em saúde/educação BR.
2. **Alternativas explicadas**: 1-3 venues hybrid/paywall com APC declarado, para usuários que tenham orçamento ou preferência específica.
3. **Transparência total**: ao recomendar venue, a ferramenta explica em texto livre o porquê do padrão e o porquê das alternativas, deixando a escolha final ao usuário.

A v2.0 inicial tinha cobertura OA internacional pobre (apenas Campbell). **A v2.2.0 fechou esse gap crítico** adicionando PLOS ONE (saúde/multi, $1,695 APC), F1000Research (multi/peer review aberto, $1,595 APC) e Frontiers in Education (educação, ~$2,200 APC). Brasil é upper-middle income pelo World Bank, autores brasileiros não recebem waiver automático mas podem aplicar via fee support programs declarados em cada perfil.

Tempo estimado típico de produção do ghostwriter para qualquer modo: ~15 minutos (estimativa do usuário; campo formal `time_to_produce_estimate: "user_estimate_15min_unvalidated"` em cada perfil de modo, a ser atualizado após casos reais documentados).

### Decisão 13 — Qualis CAPES em transição (registrado em v2.2.0)

A CAPES anunciou em janeiro/2026 que **a classificação conceitual A1-C do Qualis Periódicos será descontinuada para o quadriênio 2025-2028**. Os perfis YAML do ignorantia v2.x usam o quadriênio 2021-2024 (último válido com classificação conceitual) como referência canônica. Quando o novo modelo de avaliação CAPES for publicado, será necessário ciclo de migração dos perfis YAML — registrado como gap em `references/equator-monitoring.md` para revisão futura. A ferramenta declara explicitamente o quadriênio referenciado ao apresentar Qualis ao usuário.

### Decisão 14 — Vocabulário de tiers OA-first (registrado em v2.2.2)

A meta declarada nas versões v2.x — *"≥3 venues por área"* — é interpretada como *"≥3 venues **tier-1** por área-mãe Sucupira (QR1-Vida+Saúde+Exatas+Tec, Educação, etc.) com fallbacks tier-2/3 declarados quando o ecossistema não suporta tier-1 puro por subárea estrita"*. Esta interpretação é **coerente com a Pesquisa Qualis CAPES 2021-2024** (em `/mnt/project/Qualis_CAPES_2021-2024__Mapping_Evaluation_Area_Criteria...`), que recomenda explicitamente agrupar Vida+Saúde+Exatas+Tec sob bucket único QR1 para fins de calibração.

Os três tiers do esquema OA-first:

- **Tier 1** — diamond OA: sem APC, publisher 100% nacional ou cooperativa científica (SciELO, OJS de sociedade científica). Comportamento default semântico para perfis sem `fallback_tier` explícito.
- **Tier 2** — APC declarado modesto (≤USD 2.000), publisher comunitário científico (sociedade nacional via SciELO).
- **Tier 3** — Springer/Elsevier hybrid alto-custo (>USD 1.500) ou subscription model.

A pesquisa documental **Venues_Qualis_A2_Brasileiros_Diamond_OA_em_Exatas_e_Tecnológicas** (em `/mnt/project/`) confirma que o ecossistema editorial brasileiro em Exatas estritas **estruturalmente não contém** ≥3 venues simultaneamente diamond OA + publisher 100% nacional + aceita SLR em cada subárea. O vocabulário de tiers nomeia honestamente essa realidade em vez de fingir que ela não existe.

Operacionalmente, o engine de compliance ranqueia alternativas por `(fallback_tier ASC, aggregate_score DESC)`: tier-1 sempre emerge antes de tier-2 antes de tier-3, mesmo que tier-3 tenha score maior. Cada venue tier-2 ou tier-3 é apresentado ao usuário com APC explícito (USD original + faixa convertida quando aplicável) e justificativa da escolha do tier nas notas do perfil. Honestidade total ao usuário.

### Decisão 15 — Gap estrutural em A3 Exatas/Tec (registrado em v2.3.0)

Extensão coerente da Decisão 14 para o estrato A3. A Pesquisa Qualis 2021-2024 (Etapa 1 da estratégia consolidada v2.3-v2.4-Etapa 4b) confirmou que a oferta brasileira A3 diamond OA em CS/Engenharias estritas comporta apenas **2 venues Tier 1 puros**: POPE/SOBRAPO e RBRH/ABRH. RBIE, embora seja diamond OA da SBC, é catalogada na **área-mãe Sucupira Educação** (Computing Education), não em Exatas/Tec.

Mesmo padrão estrutural que a Decisão 14 diagnosticou para A2 — característica do ecossistema editorial brasileiro, não erro de design.

A Decisão 15 estabelece:

- **Meta A3 BR por área-mãe**: ≥3 em Educação e Saúde; **≥2** em QR1-Exatas+Tecnológicas com gap declarado.
- **Cobertura efetiva por subárea estrita CS/Eng A3**: 2 Tier 1 (POPE, RBRH) + fallbacks tier-2/3 já catalogados na v2.2.2.
- O usuário escrevendo SLR em CS/Eng A3 estrito recebe ranqueamento honesto: 2 Tier 1 puros primeiro, depois fallbacks. Sem fingir que a oferta é maior do que é.

Como subproduto da v2.3, **4 perfis legados foram recalibrados** com base na pesquisa nova: `rsp_usp` (A1 → A3), `csc_abrasco` (A1 → A3), `rbie_sbc` (B1 → A3), `pope_sobrapo` (A2 → A3). Cada um carrega nota `v2.3 RECALIBRAÇÃO` registrando evidência documental — auditabilidade total.

### Decisão 16 — Convenção de pasta `venues_qN_int` é organizativa, não estrita (registrado em v2.4.0)

Identificada inconsistência herdada da v2.2.0: dois perfis em `venues_q1_int/` (`f1000research` SJR Q2, `frontiers_education` SJR Q2) não são Q1 SJR estrito mas foram catalogados pela convenção frouxa de "alto-padrão internacional" da v2.2.0. Em vez de refator (que custaria sem ganhar valor), a Decisão 16 formaliza:

- **Pastas `venues_qN_int/` são organizativas**, agrupando venues por foco do catálogo (Q1 = "elite/prestígio internacional"; Q2 = "alto-padrão acessível"), **não por estrato estrito**.
- **O quartil real é dado pelos campos `sjr_quartile` e `jcr_quartile` em metadata**, que são autoritativos para queries do engine.
- **Sem refator obrigatório**: f1000research e frontiers_education permanecem em `venues_q1_int/` por convenção de origem; novos perfis Q2 puros vão para `venues_q2_int/`.
- O engine, ao filtrar por quartil, deve sempre consultar metadata, nunca inferir do nome da pasta.

Coerente com Decisão 14 (vocabulário de tiers como propriedade explícita em metadata) e Decisão 15 (recalibração baseada em evidência documental, não em pasta). A v2.4.0 também inclui 3 perfis Q1 SJR (ETHE, IST, JSS) na pasta `venues_q2_int/` por classificação cruzada Q2 em subáreas — Decisão 16 torna essa heterogeneidade explícita e auditável.

### Decisão 17 — Tier 0 OA locator legítimo, exclusão de plataformas em disputa judicial (registrado em v2.6.0, redação corrigida em v2.7.0 e v2.7.1)

A política OA-first formalizada na Decisão 11 (v2.1) opera sobre **bases de busca por query**. A v2.6.0 adiciona um **Tier 0** que opera sobre **resolução por DOI**: dado um DOI já encontrado em qualquer Tier 1-3, descobrir a melhor URL de full-text legítimo disponível.

**Implementação Tier 0 (em ordem de prioridade):**

1. **Unpaywall** (`scripts/searches/search_unpaywall.py`) — API REST gratuita; cobertura ~50M+ artigos OA legítimos (golden, hybrid, green/preprint); requer email de contato; sem chave de API; rate limit responsável ≤10 req/s.
2. **Open Access Button** (`scripts/searches/search_oa_button.py`) — fallback best-effort para casos onde Unpaywall não acha; cobre preprints e green OA em repositórios; também oferece URL de solicitação ao autor quando não há OA disponível.
3. **CAFe / acesso institucional** — placeholder que requer credenciais do usuário (CAFe da RNP no Brasil intermedia acesso a Capes Periódicos legalmente).
4. **Solicitação direta ao autor** — URL `https://oa.works/request/<doi>` gerada como fallback final; padrão acadêmico legítimo desde sempre.

**Plataformas em disputa judicial NÃO estão integradas ao pipeline automatizado.** A exclusão é arquitetural, não posicional:

- O `ignorantia` **não toma posição** sobre essas plataformas. Há litígios em curso envolvendo grandes publishers (Elsevier, Wiley, ACS, Springer Nature, entre outros) contra plataformas alternativas de acesso a literatura científica em múltiplas jurisdições; o mérito jurídico é objeto de disputa e o skill **não tem como função julgá-lo**.
- A integração automatizada teria efeito assimétrico: implicaria o `ignorantia` adotar uma posição sobre como o usuário deve obter material de acesso fechado. Isso viola o princípio de soberania do usuário sobre seu fluxo de trabalho.
- O skill resolve o problema **operacional** (acesso a paywalled durante triagem PRISMA) sem decidir pelo usuário: (i) Unpaywall + OAB cobrem o subset OA legítimo automaticamente; (ii) para o restante, gera-se um **`gap_report.md`** listando os itens inacessíveis e o skill **pausa**, permitindo que o usuário providencie o full-text por qualquer meio que escolher.
- Como o usuário obtém os itens é decisão do usuário. O skill não recomenda nem desaconselha plataformas, serviços ou métodos.

**Posição formal anterior corrigida.** Versões v2.6.0 e v2.6.1 da Decisão 17 afirmavam que essas plataformas "distribuem cópias não-licenciadas" e que seu uso "constitui infração". Essas afirmações replicavam a narrativa dos publishers em litigância como se fosse fato neutro. A redação atual (v2.7.0) reconhece que a operação técnica dessas plataformas é objeto de disputa e que cabe ao usuário avaliar.

O test `test_decision_17_excluded_platforms` em `tests/test_v26_tier0.py` valida que nenhuma URL de plataformas excluídas aparece no código automatizado. O test `test_gap_report_md_is_neutral` em `tests/test_v27_gap_report.py` valida que o `gap_report.md` não menciona nenhuma plataforma específica em linguagem favorável ou desfavorável.

**Quando Tier 0 é chamado:**
- **Sempre, automaticamente**, após qualquer Tier 1-3 retornar DOIs (v2.6.1).
- Cada DOI é resolvido em ordem (Unpaywall → OAB → author request) e o resultado é gravado em `<output-dir>/tier0_oa_enrichment.json`.
- Email de contato vem do argumento `--contact-email` ou da variável de ambiente `IGNORANTIA_CONTACT_EMAIL`. Sem ele, a resolução emite warning e tenta mesmo assim.
- A única forma de pular é `--skip-tier0`, reservada para uso offline/CI.

**Após Tier 0 (v2.7.0):** o skill gera um **gap report** (`<output-dir>/gap_report.md`) listando todos os itens cujo full-text não foi resolvido por fontes OA. Em uso normal, o skill então **pausa com exit code 10** (pausa intencional, não erro) aguardando que o usuário:
- Coloque full-texts em `<output-dir>/user_provided/` por qualquer método que escolher.
- Retome com `--resume-after-gap-report`.
- OU pule a resolução com `--skip-gap-resolution` — itens não providenciados serão registrados como "excluídos por inacessibilidade" no PRISMA flow diagram, com motivo declarado para auditoria.

### Decisão 18 — HTML em chunks/append na Fase 7 (registrado em v2.8.0, implementado em v2.10.0; escopo limitado ao subcomando `html-wiki` em v3.0.0-rc1)

A renderização anterior fazia uma única passada com substituição de placeholders. Falha em qualquer seção invalidava todo o trabalho. A v2.10.0 implementa renderização incremental em `scripts/render_chunks.py`:

1. Inicia o HTML com boilerplate (head + topbar + abertura do `<main>`).
2. Renderiza cada seção em chunk independente (§00, §01, ..., §N) e faz append.
3. Cada chunk é gravado em arquivo intermediário (`<output>.chunk-NN.html`) para permitir checkpoint/recovery.
4. Após todas as seções, fecha o HTML (footer).
5. Se uma seção falha, o usuário pode reprocessar só aquela seção sem perder as demais (`--resume-from-chunk N`).

Smoke test `test_render_chunks_does_not_leak_skill_brand` valida que o HTML produzido pelo render incremental também não vaza nome do skill (Decisão 19).

**Escopo (v3.0.0-rc1 — RS-42 remediation):** este protocolo aplica-se **apenas** ao subcomando `ignorantia render --format html-wiki` (Decisão 37). O pipeline canônico (LaTeX → BibTeX → PDF → DOCX) não invoca chunked-render — o `.tex` é gravado em uma única operação porque seu peso é uma ordem de grandeza menor que o HTML auto-contido. A Decisão 34 (Fix 1 do remediation) refina o protocolo de write incremental e também é escopada ao subcomando.

### Decisão 19 — Anti-vazamento de meta-discurso do skill no manuscrito (registrado em v2.8.0)

Erro identificado na auditoria do RS-42 v1.0.0: o manuscrito gerado citava literalmente "Decisão 1 do skill ignorantia v2.1", "exigência da skill", "critério de aceitação 'ao menos 3 itens' da skill", e trazia rodapé com nome do skill. O skill estava se autodeclarando dentro do output em vez de operar como ghostwriter.

**Regra absoluta:** o manuscrito final é a voz do pesquisador, não do skill. O output do skill **NUNCA** menciona:
- O nome `ignorantia` em parte alguma do output (manuscrito, anexos, metadados visíveis ao leitor).
- Decisões internas do skill numeradas ("Decisão N").
- Critérios de aceitação internos ("ao menos 3 itens", "padrão da skill").
- Templates ou exigências do skill ("conforme exigência", "padrão da skill v2.x").
- Explicações que façam o leitor entender que o pesquisador está cumprindo uma especificação técnica do ghostwriter — para o leitor, as decisões metodológicas são do pesquisador.

**Onde menções a IA são obrigatórias** (Portaria CNPq 2.664/2026, ICMJE, COPE), o disclosure usa o padrão da Decisão 33 (segredo industrial): "algoritmo particular do autor (não-divulgado por segredo industrial) + LLM declarado". Provider e modelo do LLM são divulgados; arquitetura interna do skill, não.

Esta decisão é vinculante e mecanicamente verificável. A v2.8.0 limpou:
- `assets/templates/manuscript-template.html`: removido `<title>... ignorantia v...`, `<meta generator="ignorantia v...">`, brand "ignorantia" no topbar e footer.
- `scripts/render_manuscript.py`: removido default `"ignorantia v..."` no campo `interface` do AI disclosure (substituído pelo padrão segredo industrial).

A v2.10.0 adicionará teste mecânico `test_decision_19_no_skill_leakage_in_manuscript` que parseia o `manuscript.html` final e falha o build se qualquer dos termos proibidos aparecer no output renderizado.

### Decisão 20 — Voz autoral padrão (persona) registrada (v2.8.0)

A skill opera como ghostwriter sob uma voz autoral padrão registrada. Esta voz rege como o texto é escrito; o nome literal da persona é label interno e **não aparece** em nenhum output. O by-line e a authorship do paper carregam o nome real do autor declarado pelo usuário no protocolo.

**Voz autoral padrão da skill `ignorantia`** (label interno; não exposta):

> Pesquisador autônomo há 22 anos, formação interdisciplinar em TI, design e educação, 19 anos de prática docente em letramento digital de crianças e adultos. Está escrevendo para publicação em periódico Qualis A1, com depósito prévio em Zenodo seguido de arXiv.
>
> **Voz e estilo:** acadêmico neutro impessoal ("foi conduzido", "observou-se", "os achados sugerem"). ABNT/Vancouver. IMRaD mantido até o fim para preservar o arco do storytelling científico. Clareza e economia de palavras acima de elaboração retórica.
>
> **Postura intelectual:** atenção declarada a testes de hipóteses metodológicas; cada decisão metodológica vem com justificativa breve da alternativa rejeitada; tom expositivo no restante. Verifica citações múltiplas vezes pela preocupação concreta com plágio e citações alucinadas — verificação Crossref/OpenAlex obrigatória.
>
> **Lidando com incerteza:** quando achados divergem, reporta a divergência em vez de forçar consenso. Quando decisões admitem alternativas defensáveis, declara a alternativa e justifica. Sem hedging ornamental: ou afirma com base citável, ou declara incerteza honesta.
>
> **O que a persona NÃO faz:** não cita o próprio histórico no texto; não usa primeira pessoa para reivindicar autoridade; não menciona o skill `ignorantia` nem qualquer ferramenta interna do pipeline; não cita a si própria como persona em parte alguma do output.

A persona é instrução para o ghostwriter, não personagem do paper. O pesquisador real (declarado no protocolo) é quem assina; a persona é o estilo do raciocínio textual.

### Decisão 21 — Spot-check humano da Fase 4 = aceite implícito ao prosseguir (registrado em v2.8.0)

A rubrica de qualidade anterior penalizava o autor por "não conduzir spot-check humano nas exclusões da Fase 4 (screening de título/abstract)". Essa exigência é redundante: ao prosseguir do screening para a extração, o usuário **já está revisando manualmente** os elegíveis e **já está aceitando** as exclusões. Tornar isso explícito como auditoria separada é burocracia sem ganho de qualidade.

**A v2.8.0 formaliza:** ao usuário prosseguir da Fase 4 para a Fase 5, o `reproducibility_manifest.yaml` registra automaticamente:

```yaml
phase4_exclusions_review:
  mode: implicit_consent
  consented_at: <timestamp>
  rationale: "Ao prosseguir para extração, o autor aceita as exclusões da Fase 4."
```

E a rubrica D1 (Metodologia) **deixa de penalizar** ausência de spot-check separado. O critério "Spot-check humano nas exclusões da Fase 4 não foi conduzido" é **removido** da rubrica.

### Decisão 22 — Re-execução obrigatória de buscas em data diferente por subversão (registrado em v2.9.0)

A rubrica antiga continha "(Importante) Reprodutibilidade entre runs não testada — re-executar as buscas em datas diferentes". Esse critério foi reescrito como **obrigação**: cada subversão (incremento PATCH ou MINOR com data nova) **deve** re-executar as buscas e reportar diff contra a execução anterior. Estabilidade ≥ 95% em N de hits brutos por base é o threshold; abaixo disso o skill emite warning e exige justificativa do usuário.

**Implementação técnica:** o `reproducibility_manifest.yaml` ganha o bloco `search_runs` com timestamps por execução. O orquestrador detecta automaticamente quando `today != last_run_date` e re-executa Tier 1 antes de prosseguir para Tier 2.

### Decisão 23 — Snowballing backward obrigatório (Wohlin 2014) (registrado em v2.9.0)

A rubrica antiga continha "(Polimento) Snowballing (Wohlin 2014) backward não foi sistematicamente conduzido". Reescrita como **obrigação**: snowballing backward é executado automaticamente após Fase 5 (extração) usando os DOIs dos estudos seed. Implementação em `scripts/searches/snowballing_backward.py`.

**Fluxo:**
1. Fase 5 (extração) marca estudos seed (típico: 5-10 estudos centrais ao tema).
2. `snowballing_backward.py` recupera referências citadas via Crossref (fallback OpenAlex).
3. Candidatos novos (deduplicados contra corpus já incluído) retornam ao screening da Fase 4 com `origin: backward_snowballing` no manifest.
4. Snowballing forward (citações posteriores) fica como TODO para v2.10.0+.

### Decisão 24 — "Tier 3" renomeado para `priority_0_routing`; bases pagas viram prioridade 0 obrigatória (registrado em v2.9.0)

A nomenclatura anterior tratava Scopus/WoS/Embase/IEEE Xplore subset/ACM Full/Elsevier ScienceDirect como "Tier 3 = paywall opt-in, falha aceitável se usuário não tem acesso". A v2.9.0 reorganiza:

- Essas bases são **prioridade 0**, não Tier 3.
- Cada DOI/título de busca é tentado em ordem: **Unpaywall → Open Access Button → CORE API → Periódicos CAPES (com CAFe quando disponível)**.
- O que sobrar entra no `gap_report.md` (já existente desde v2.7.0).
- Não-acesso a essas bases não é mais "limitação aceita" — é gap declarado a resolver no gap report (Decisão 17 + Decisão 24 cobrem o problema operacional).

**Implementação:** `TIER_DATABASES[area]["priority_0_routing"]` substitui `["tier3"]`. Alias `tier3` mantido até v2.10.0 para retrocompatibilidade. CORE API integrada via `scripts/searches/search_core.py`. Periódicos CAPES via `scripts/searches/search_periodicos_capes.py` (retorna instruções acionáveis quando não há credenciais).

### Decisão 25 — Bases ibero-americanas obrigatórias em todas as áreas (registrado em v2.9.0)

A rubrica antiga marcava "(Importante) SciELO direto deveria ter sido consultado" como limitação aceitável. Erro: pt-BR e es-LA são idiomas obrigatórios da skill (Decisão 27), portanto bases nessas línguas são obrigação, não polimento.

**Bases adicionadas como obrigatórias em `TIER_DATABASES`:**

| Base | Cobertura | Adapter |
|---|---|---|
| **SciELO** | América Latina + Caribe + Espanha + Portugal; revistas peer-reviewed | `search_scielo.py` (já existia) |
| **LA Referencia** | Rede federada de 13 países (Argentina, Brasil, Chile, Colômbia, Costa Rica, Equador, El Salvador, México, Panamá, Peru, República Dominicana, Uruguai, Venezuela); ~5M registros | `search_la_referencia.py` |
| **Redalyc** | ~1.300 revistas OA Ibero-América; forte em ciências sociais | `search_redalyc.py` |
| **CLACSO** | Repositório de ciências sociais e estudos críticos LA; ~150k itens (livros, capítulos, working papers) | `search_clacso.py` |
| **BDTD** | ~750k teses e dissertações brasileiras; mantida pelo IBICT | `search_bdtd.py` |
| **Scioteca (CAF)** | Repositório do banco de desenvolvimento da América Latina; gray literature em economia/desenvolvimento | `search_scioteca.py` |
| **DOAJ** | Multilíngue, todas áreas, peer-reviewed OA | (já listada no Tier 1 multi) |
| **LILACS/BVS/BIREME** | Saúde, ibero-americana | (já listada como `lilacs`) |
| **Periódicos CAPES** | Gateway federado para Scopus/WoS/Elsevier/Springer/Wiley/ACM/IEEE/Embase via CAFe | `search_periodicos_capes.py` (instruções acionáveis quando sem credenciais) |

**Cada adapter** tem fallback gracioso: modo `mock` retorna fixture determinística; modo real consulta endpoint público com User-Agent identificável e throttle conservador. Quando o endpoint retorna HTML/RSS em vez de JSON limpo, o adapter retorna `raw_size_bytes` + URL consultada e marca `parser detalhado é TODO` — o usuário pode pós-processar com feedparser/BeautifulSoup ou aguardar release futura.

### Decisão 26 — Todo elegível recebe extração com rigor de SR, independente do modo (registrado em v2.9.0)

A rubrica antiga marcava "(Importante) Apenas X% dos elegíveis foram extraídos com profundidade. Para uma scoping review, isso é defensável... para systematic review seria insuficiente." Reescrita: **todo estudo elegível recebe a mesma extração**, independente de o modo ser scoping/rapid/mapping/integrative ou SR estrito. A diferença entre modos está em **sintese** e **questões de pesquisa**, não em rigor de extração.

A heurística "extrair só o núcleo (5-10 estudos)" foi eliminada. O critério de aceitação foi removido da rubrica D3.

### Decisão 27 — EN+PT+ES como obrigação, não limitação (registrado em v2.9.0)

A rubrica antiga marcava "(Polimento) Idiomas restritos a EN/PT/ES" como lacuna a declarar. Erro: a skill **suporta esses três idiomas por design** (Decisão 7 v2.0). Cumprimento da especificação não é limitação a declarar.

**A v2.9.0 remove** quaisquer linguagens em `references/quality-rubric.md` ou na seção §09 gerada do manuscrito que tratem EN/PT/ES como restrição. Idiomas adicionais (mandarim, francês, alemão) ficam como roadmap declarado para v3.0+/Cowork.

### Decisão 28 — Formatação ABNT NBR 6023:2018 + NBR 10520:2023 obrigatória em pt-BR (registrado em v2.9.0)

A rubrica antiga marcava "(Importante) Norma ABNT aplicada de forma simplificada" como lacuna aceitável. Reescrita: formatação ABNT detalhada é **obrigatória** em pt-BR. Implementação em `scripts/format_abnt.py` cobrindo:

- **NBR 6023:2018 (Referências):** artigo, livro, capítulo de livro, tese, dissertação, conferência, eletrônico, legislação, recurso audiovisual, website, sem autoria. Autores: até 3 listados; 4+ usa `et al.` Sobrenomes em CAIXA-ALTA, prenomes abreviados.
- **NBR 10520:2023 (Citações):** sistema autor-data, citação direta curta (entre aspas, com página), citação direta longa (≥ 4 linhas, recuo 4cm, sem aspas), citação indireta (paráfrase), apud (citação de citação), citação de obra sem autoria identificada (`[s.a.]`).

**Smoke tests** validam: `(SILVA, 2023)` indireta, `(SILVA; PEREIRA, 2023, p. 45)` direta, `(VYGOTSKY, 1978 apud SILVA, 2023, p. 12)` apud, `et al.` para 4+ autores, ordem alfabética da bibliografia.

### Decisão 29 — Tabela cross-tabulação obrigatória na síntese (registrado em v2.9.0)

A rubrica antiga marcava "(Polimento) Síntese poderia incluir tabela cross-tabulação modelo × tarefa × métrica (não foi gerada)". Reescrita: cross-tabulação é **obrigatória** na §05 da síntese. Implementação em `scripts/cross_tabulation.py`:

- Recebe `extraction.csv` + nomes de 2 ou 3 dimensões a cruzar.
- Trata células multi-valor separadas por `|` ou `;` (frequente em colunas tipo "tasks").
- Trata `—`, `-`, `N/A`, `n/a` como ausências.
- Emite versão markdown (com totais por linha/coluna), HTML (para inserção direta no manuscrito), e prosa-resumo (para inserção em §05).
- Versão 3D estratifica por terceira dimensão (uma tabela por valor de Z).

**Smoke tests** validam: 2D básica, 3D estratificada, multi-valor por célula, tratamento de ausências.

### Decisão 30 — Remoção da feature "rabiscos for fun" (registrado em v2.8.0)

Feature anteriormente prevista (camada decorativa de anotações vermelhas estilo "OLHA ESSE NÚMERO!") foi **removida** integralmente. Rationale: feature decorativa que sinaliza informalidade incompatível com a voz autoral padrão (Decisão 20 — acadêmica neutra impessoal) e com o público-alvo (Qualis A1, Zenodo, arXiv). Mesmo como toggle opt-in, a presença da feature na skill comunica algo sobre a postura do skill que não corresponde ao que ele faz.

**Removido:**
- Linha 320 (antiga) do SKILL.md descrevendo a camada.
- Função `build_fun_doodles_html` em `scripts/render_manuscript.py` agora é stub que sempre retorna string vazia (mantida para retrocompatibilidade com pacotes `content.json` antigos que tenham campo `fun_doodles`).
- Toda menção a "doodles", "rabiscos", "Permanent Marker", "TOP VOICE!", etc. nos templates ativos.

**Test-cases legados** (`test-cases/scenarios/{ghostwriter,smoke,corpus18}/manuscript.html`) ainda contêm a feature renderizada — são snapshots históricos de regressão da v1.x e **não vão para o pacote dist**. Não serão reescritos porque sua função é congelar o comportamento histórico para detecção de regressão.

### Decisão 31 — Geração `.docx` ABNT obrigatória (registrado em v2.10.0)

Output `.docx` no padrão ABNT (NBR 14724:2011 + NBR 6023:2018 + NBR 10520:2023) é parte obrigatória do pacote final em pt-BR. Implementação em `scripts/render_docx_abnt.py` usando `python-docx`.

Padrões aplicados:
- Papel A4, margens 3cm/3cm/2cm/2cm.
- Fonte Times New Roman 12pt corpo; 10pt citações longas e notas.
- Espaçamento 1,5 corpo; simples em citações longas, notas, referências.
- Recuo de parágrafo 1,25 cm.
- Citação longa (≥ 4 linhas): recuo 4cm da margem esquerda, fonte 10pt, espaçamento simples, sem aspas.
- Numeração de página no canto superior direito a partir da Introdução.
- Referências alinhadas à esquerda, espaçamento simples, em ordem alfabética.

Coopera com `scripts/format_abnt.py` (Decisão 28) — referências e citações já formatadas como string entram como `paragraphs[i].type = "reference"` ou `"long_quote"` no content.json e o renderer aplica a tipografia correta.

### Decisão 32 — Geração `.tex` + `.pdf` obrigatória (registrado em v2.10.0)

Output `.tex` (LaTeX) é parte obrigatória do pacote final. Compilação para `.pdf` é opcional (depende de `pdflatex` ou `xelatex` no PATH). Implementação em `scripts/render_latex.py`.

Tipografia ABNT aproximada via packages padrão do TeX Live (sem dependência de `abntex2`):
- `geometry`: margens 3cm/3cm/2cm/2cm.
- `setspace` + `\onehalfspacing`: espaçamento 1,5.
- `mathptmx`: Times New Roman.
- `babel` com `[main=brazilian, provide=*]` (compatível com TeX Live moderno).
- `csquotes`, `hyperref`.
- Ambiente `longquote` customizado: recuo 4cm + fonte 10pt + singlespace (NBR 10520:2023 §6.1).

Caracteres especiais (`& % $ # _ { } ~ ^ < >`) são escapados automaticamente. A função `compile_pdf` roda o engine 2x para resolver referências cruzadas, com timeout configurável e log preservado.

Para conformidade plena com a classe abntex2, o usuário pode trocar manualmente `\documentclass{article}` por `\documentclass{abntex2}` — o conteúdo gerado é compatível.

### Decisão 33 — Identidade da skill como segredo industrial (registrado em v2.8.0)

A skill `ignorantia` é obra autoral do usuário, com direito a segredo industrial sobre arquitetura interna, decisões editoriais numeradas, vocabulário interno (Tiers, modos, fases), e qualquer detalhe que revele lógica proprietária. A v2.8.0 formaliza:

**Onde menções a IA são legalmente obrigatórias** (Portaria CNPq 2.664/2026; ICMJE 2024; COPE; Diretrizes específicas de publishers), o disclosure usa o padrão:

> Algoritmo particular do autor (não-divulgado por segredo industrial) + LLM declarado abaixo.
> Provider: Anthropic. Modelo: Claude [versão]. Interface: claude.ai (web).

O **provider** e **modelo** do LLM são divulgados (obrigação ética sob ICMJE/COPE). A **arquitetura interna do skill** não é (direito ao segredo industrial não conflita com a obrigação de disclosure — a obrigação é sobre uso de IA, não sobre revelar ferramentas autorais customizadas).

**Onde menções NÃO são obrigatórias** (manuscrito propriamente dito, narrativa metodológica, footers, títulos, metadados visíveis), o nome `ignorantia` **não aparece**. A justificativa metodológica é apresentada como decisão do pesquisador, não como cumprimento de especificação técnica do skill (Decisão 19).

A v2.8.0 aplicou esta decisão limpando:
- `assets/templates/manuscript-template.html` — title, meta generator, brand topbar, brand footer.
- `scripts/render_manuscript.py` — campo `interface` do AI disclosure passou de `"ignorantia v..."` para `"algoritmo particular do autor (não-divulgado por segredo industrial) + LLM declarado acima"`.

Releases futuras (v2.9.0+) farão varredura sistemática nos demais templates de modo (`assets/templates/modes/*.md`) e nos prompts gerados.

### Decisão 34 — Protocolo de chunked write para SLRs grandes (registrado em v2.23.1, urgência alta)

A Decisão 18 (v2.10.0) implementou renderização incremental em
`scripts/render_chunks.py`, mas o uso operacional pelo Claude na
sessão de chat ainda assumia produção do HTML completo numa única
passada de resposta. Em SLRs com >5 seções OU >20 referências, a
soma de (a) resultados de buscas web, (b) verificação de DOIs, (c)
extração + síntese e (d) geração de prosa em uma única resposta
estoura o budget de contexto antes de qualquer arquivo ser escrito
em disco. Sintoma observado em RS-42 (2026-05-08): a sessão aborta
com "Esta conversa não pode ser compactada ainda mais. Inicie um
novo chat para continuar." sem produzir nenhum artefato.

**Regra operacional vinculante**: SLRs que satisfaçam **qualquer**
critério abaixo seguem o protocolo de chunked write:

- ≥5 seções no manuscrito (introdução + métodos + resultados +
  discussão + conclusão já satisfaz);
- ≥20 referências no corpus final;
- ≥3 web searches projetadas para a Fase 3;
- modo `systematic_review_strict` (sempre).

**Protocolo (vincula `Claude` em sessão chat, não código Python)**:

1. **Persistir `searches.json` ANTES da síntese.** Toda Fase 3
   (busca) escreve `<output_dir>/searches.json` em disco antes de
   qualquer prosa ser gerada na resposta. O conteúdo do JSON
   nunca volta para o contexto da resposta — apenas o
   `searches.json` path é referenciado a partir da Fase 4.

2. **Persistir `extraction.csv` e `quality-appraisal.csv` antes
   da síntese narrativa.** A Fase 5/6 grava em CSV; a Fase 7 lê
   o CSV via `python3 scripts/...` e produz prosa **uma seção
   por vez**.

3. **Renderização HTML por seções (chunked append).** Para cada
   seção §00, §01, …, §N, invocar em chamada separada:

   ```bash
   python3 scripts/render_chunks.py \
       --output-dir <out> \
       --section §<N> \
       --append \
       --content <out>/content-section-<N>.json
   ```

   Cada chamada é uma round-trip independente. O HTML completo
   nunca está no contexto da conversa — só o chunk corrente.

4. **Render LaTeX/DOCX/PDF é uma única chamada de pipeline** que
   lê `<out>/content.json` consolidado em disco (não o contexto):

   ```bash
   python3 scripts/pipeline_finalize.py \
       --output-dir <out> \
       --skip-html-chunks  # já gerados acima
   ```

5. **NUNCA acumular HTML completo no contexto da conversa.** Se a
   resposta tiver mais de ~10 KB de prosa renderizada, particionar
   antes de continuar. O Claude deve preferir "vou gerar a próxima
   seção em uma chamada separada" a "vou continuar a redação aqui".

**Verificação mecânica**: o pipeline_summary.json gerado deve
mostrar `"steps": [...]` com `"render_html_chunks"` chamado N
vezes (uma por seção) **OU** o Claude deve emitir a sequência
correspondente de subprocess calls visíveis na transcrição.
Sessões que produzem 0 chamadas a `render_chunks.py --append`
mas alegam ter renderizado HTML são suspeitas — o usuário deve
validar.

Esta decisão **não substitui** a Decisão 18; ela formaliza o
protocolo operacional que Claude segue para *invocar* o mecanismo
incremental que a Decisão 18 já tinha disponível em código mas
não estava sendo acionado.

### Decisão 35 — Budget guardrails operacionais por fase (registrado em v2.23.1)

Complementa a Decisão 34 (chunked write) com **limites mecânicos
por fase** que o Claude verifica em sessão de chat antes de
prosseguir. O objetivo não é blindar o pipeline contra abuso (não
há atacante); é dar ao Claude pontos de decisão claros onde optar
por externalizar trabalho em vez de continuar acumulando no
contexto.

#### Fase 3 — Buscas web

* **Máximo 5 web searches por execução de SLR** quando a sessão
  está conduzindo o pipeline diretamente. SLRs maiores devem
  receber a lista de queries pré-pesquisada via
  `<output_dir>/searches.json` gerado em sessão anterior.
* Se a Fase 3 efetiva exigir >5 queries, parar, escrever a lista
  em `<output_dir>/queries-pending.txt`, recomendar ao usuário
  rodar `python3 scripts/searches/search_orchestrator.py --batch
  <queries-pending.txt>` em terminal (subprocess longo fora do
  chat), e aguardar o `searches.json` consolidado.

#### Fase 6 — Extração

* **Máximo 30 referências processadas em uma única resposta**.
  Para >30, processar em lotes de 25 escrevendo
  `extraction.csv` incrementalmente (modo `--append`); cada lote
  é uma chamada subprocess separada, não uma resposta longa.
* O CSV vai pra disco a cada lote; o contexto da conversa
  guarda só o caminho `<output_dir>/extraction.csv`, não os
  registros.

#### Fase 7 — Síntese narrativa

* **Máximo 1 seção por resposta**. Cada `<section>` HTML é uma
  chamada subprocess a `render_chunks.py --append --section §<N>`
  conforme Decisão 34.
* Se a resposta corrente já tem >10 KB de prosa renderizada,
  parar antes de iniciar a próxima seção e ceder o controle de
  volta ao usuário com a próxima seção como próximo passo
  explicitado.

#### Fase 8 — Empacotamento Zenodo

* Empacotamento final é uma única chamada a
  `python3 scripts/slr_to_package.py --output-dir <out>`. O
  conteúdo do ZIP nunca volta ao contexto da conversa — apenas
  o caminho do `.zip` e o SHA-256 calculado.

#### Verificação mecânica

A Decisão 35 é vinculante mas **não tem teste pytest** — é uma
diretriz operacional para sessões interativas. A verificação é
indireta:

* **`pipeline_summary.json`** mostra quantas chamadas a
  `render_chunks.py --append` ocorreram. Sessões que afirmam ter
  processado SLR grande mas mostram <N seções no summary são
  suspeitas.
* **Logs de adapter (Camada 1, DD-10)** registram timestamps das
  buscas. Mais de 5 timestamps próximos numa SLR pequena indica
  que a Fase 3 não foi externalizada.

## Infraestrutura de comparação automatizada (v2.5.0 — Etapa 4b)

A v2.5.0 adicionou `scripts/comparison/` — andaime reprodutível para comparar a `ignorantia` contra baselines de SLR tooling (B!SON, JANE, ASReview LAB v2, Penelope.ai e snapshots manuais de recommenders comerciais). Conforme `scripts/comparison/PROTOCOL.md`:

- **Categoria 1 (recommenders):** B!SON com API REST aberta + JANE em scaffold + snapshots manuais para Elsevier/Springer/Wiley/T&F/IEEE/Clarivate.
- **Categoria 2 (screening):** ASReview LAB v2 em modo simulação com SYNERGY dataset.
- **Categoria 3 (compliance):** Penelope.ai e GoodReports via snapshot manual.
- **Categoria 4 (workflow systems — EM, ScholarOne, OJS, eJournalPress):** **explicitamente excluídos** porque não fazem comparação semântica de conteúdo.

Cada cliente tem fallback gracioso (modo `mock`) com fixtures determinísticas baseadas em valores publicados. Schema de output unificado em `schemas/unified_output.schema.json` (v1.0.0). Relatórios em markdown via `report.py`. **Esta infraestrutura não produz validação empírica — ela cria o andaime para que a validação aconteça quando casos reais existirem (Etapa 4b empírica).**



<critical_rules>

Estas regras são absolutas. Onde houver conflito entre regra crítica e qualquer outra orientação deste documento, a regra crítica vence.

<prohibitions>
NUNCA invente resultados de busca, números de hits, estudos, autores, anos, DOIs ou citações. Se uma busca não foi executada ou falhou, declare a falha.
NUNCA simule um segundo revisor nem calcule Cohen's kappa por conta própria — esse passo é responsabilidade humana, ocorre fora do skill, depois do upload no Zenodo.
NUNCA edite uma versão SemVer já publicada — gere nova versão.
NUNCA burle paywall. Acesso a base paga via credencial institucional legítima do usuário, em script transparente. Plataformas em disputa judicial estão fora do escopo do pipeline automatizado (Decisão 17); como o usuário resolve gap manualmente é decisão dele.
NUNCA execute buscas antes do protocolo estar fechado e validado pelo usuário.
NUNCA omita do manuscrito a seção §09 "O que esta versão NÃO é" — limites declarados são parte da entrega.
NUNCA cite uma referência sem link clicável para a fonte primária no HTML final.
NUNCA prossiga para a próxima fase do fluxo sem ter o artefato concreto da fase anterior gerado e nomeado conforme convenção.
NUNCA liste a IA (Claude, GPT, Gemini, etc.) como autor do manuscrito — viola COPE, ICMJE, e Portaria CNPq nº 2.664/2026.
NUNCA omita a "Declaração de uso de IAG" (pt-BR) ou "Declaration of AI use" (EN) — é obrigatória.
NUNCA insira dados pessoais de terceiros em ferramentas IAG — viola LGPD e art. 9 da Portaria CNPq.
NUNCA insira projetos de pesquisa de terceiros em IAG para gerar parecer — vedado pela Portaria CNPq.
NUNCA gere figura ou imagem por IA para uso no manuscrito sem declaração explícita e justificativa — vários publishers (Nature, Elsevier, AAAS) proíbem.
NUNCA chame de "systematic review" um manuscrito sem evidência de dois revisores humanos com kappa documentado — use "scoping review", "rapid review" ou "mapping study" conforme a Decisão 1 das decisões editoriais v2.0.
NUNCA chame de "living review" um manuscrito sem protocolo formal Cochrane/Campbell ativo — use "periodically updated review" ou "time-bounded review" conforme Decisão 6.
NUNCA deposite manuscrito no Zenodo sem o pacote de reprodutibilidade completo (Decisão 2) — DOIs alucinados ou retratados são bloqueantes (eliminatório E10 reforçado).
NUNCA omita as 5 mitigações Categoria A de CoI (Decisão 8): pré-registro, declaração CoI padronizada, seção "evidência contrária encontrada", categorização review_purpose, pacote Zenodo.
</prohibitions>

<mandatories>
GERE sempre os 8 artefatos secundários: protocol.md, searches.json, screening.csv, quality-appraisal.csv, extraction.csv, prisma-flow.svg, bibliography.bib, README.md.
GERE sempre o pacote acadêmico canônico: manuscript.tex + bibliography.bib → manuscript.pdf (Zenodo) + manuscript.docx (revisão Word). HTML Wiki-style **NÃO** é gerado pelo fluxo padrão — só quando o usuário invoca explicitamente o subcomando `ignorantia render --format html-wiki` (Decisão 37).
NOMEIE o pacote como ignorantia-<area-slug>-<topic-slug>-v<X.Y.Z>.zip.
INCLUA hash SHA-256 de cada artefato no README.md.
APLIQUE a norma de citação correta automaticamente: PT-BR→ABNT; EN+exatas→IEEE; EN+saúde→Vancouver; EN+psicologia/educação→APA.
APLIQUE PRISMA-2020 sempre. Para temas de SE/CS, complemente com Kitchenham QA1–QA8.
EXECUTE quality appraisal CASP-style ou DARE para cada estudo incluído, com pontuação registrada por questão e por revisor.
PERGUNTE ao usuário, no início, se há acesso institucional a Scopus/WoS/IEEE Xplore/CAPES, antes de planejar buscas em bases pagas.
INSIRA o bloco "Declaração de uso de IAG" (pt-BR) ou "Declaration of AI use" (EN) em §03 ou §03.x do manuscrito, listando ferramenta, versão, etapas e responsabilidade humana.
PRIORIZE literatura de venues e publishers de elite na busca: Nature/Science/PNAS/Lancet/Cell, periódicos IEEE/ACM/Elsevier/Springer Nature/Wiley/Sage/Taylor & Francis, AAAS, AMA, BMJ, ACS, RSC, APS, ASME, OUP, CUP, MIT Press, conforme área.
SUGIRA na Fase 8 entre 3 e 5 venues de submissão da área, com URL da política de IA do publisher, ISSN, JIF/CiteScore, modelo de acesso.
GERE ao final da Fase 8 o arquivo `avaliacao_v<X.Y.Z>.md` via `scripts/generate_assessment.py` — nota 0.0-10.0 contra a rubrica em `references/quality-rubric.md`, com lista priorizada do que falta para 10.0. Nota 10.0 = pronto para venue de elite máxima OU Qualis A1 nacional. Arredondamento sempre para baixo.
LISTE no README.md o checklist de compliance executado (CNPq art. 9, COPE, ICMJE, LGPD, CEP/CONEP) com cada item marcado E a nota da avaliação automática.
DECLARE explicitamente, no header e no metadado do manuscrito, o `review_type`. Valores válidos v2.1 (ver `references/modes/MODES_OVERVIEW.md` e `VALID_REVIEW_TYPES_V21` em `scripts/assessor/eliminators.py`): camada primária = scoping_review | rapid_review | mapping_study | integrative_review | realist_review; camada secundária = software_paper | position_paper | theoretical_essay | technical_report | white_paper | policy_brief; camada terciária = systematic_review_with_2_reviewers — Decisões 1, 10 v2.1.
DECLARE no metadado o `review_purpose` (design_foundational | design_validation | design_correction | independent_inquiry) — Decisão 8 v2.0.
GERE pacote de reprodutibilidade via `scripts/zenodo/` antes do depósito Zenodo, com DOIs verificados via Crossref+Retraction Watch+OpenAlex — Decisão 2 v2.0.
APLIQUE engine de compliance via `scripts/compliance/` contra venue alvo (se declarado) e produza `compliance_report.json` com aggregate_score + dimensões + gaps priorizados + venues alternativos ranqueados.
APRESENTE ao usuário a recomendação de preprint server pareada com 1-2 alternativas e suas políticas de IA, e aguarde confirmação antes de gerar o pacote do preprint server escolhido — Decisão 3 v2.0.
</mandatories>

<verifiable_acceptance_criteria>
O HTML final tem um número de versão SemVer no header e no footer (mesma versão em ambos).
O HTML carrega offline depois do primeiro carregamento (apenas D3.js v7 via CDN é externo; tudo mais é inline).
Toda referência [n] no texto é clicável e leva à fonte primária; tooltip mostra a citação completa formatada.
A tabela de estudos incluídos tem sticky header, filtros por coluna, e ordenação por click.
Os toggles "Anotações", "Rabiscos", "Escuro" e "Colapsar" funcionam (verificável via aria-pressed após click).
O diagrama PRISMA-2020 inline tem todos os números coerentes: identified ≥ deduplicated ≥ screened ≥ assessed ≥ included.
A seção §09 "O que esta versão NÃO é" tem pelo menos 3 itens declarados.
O manuscrito contém uma seção identificada como "Declaração de uso de IAG" (pt-BR) ou "Declaration of AI use" (EN) com ferramenta, versão, etapas, e atribuição de responsabilidade humana.
A IA NÃO está listada como autor em parte alguma do manuscrito.
O README.md do pacote lista o hash SHA-256 de cada artefato, a versão SemVer, o changelog desde a versão anterior (se houver), e o checklist de compliance.
A Fase 8 produziu uma lista de 3-5 venues sugeridos com URL da política de IA do publisher.
O pacote contém `avaliacao_v<X.Y.Z>.md` com nota numérica 0.0-10.0, ponto-a-ponto por dimensão, e seção "O QUE FALTA PARA NOTA 10.0" com itens priorizados em Crítico/Importante/Polimento.
</verifiable_acceptance_criteria>

</critical_rules>

## Saída opcional: HTML Wiki-style (subcomando dedicado)

> **NÃO é o artefato acadêmico canônico.** O artefato canônico para depósito Zenodo / proteção de IP é o **PDF compilado a partir de `manuscript.tex` + `bibliography.bib`** (ver Decisão 32 e Decisão 36 — a serem mescladas pelas Fixes 5/7 do remediation RS-42). O DOCX é secundário (mesma estrutura, formato compatível com revisão Word). O HTML descrito nesta seção é **opt-in**, gerado apenas quando o usuário invoca explicitamente o subcomando `ignorantia render --format html-wiki` — nunca faz parte do pacote acadêmico depositado no Zenodo.

A saída HTML, quando invocada, reúne num só documento navegável o manuscrito completo (introdução → método → resultados → discussão → conclusão), o diagrama PRISMA, a tabela interativa de estudos incluídos, gráficos D3.js dinâmicos, a camada de anotações de professor, e a lista de referências clicáveis. Funciona como artigo no estilo Wikipedia/divulgação técnica — distribuição didática, não registro acadêmico de prioridade. Por causa do seu peso (200-260 KB de tokens em renderização single-pass), depende obrigatoriamente do **protocolo de chunked-render** descrito na Decisão 18 (e refinado pela Decisão 34, a ser mesclada pela Fix 1 do RS-42).

Características obrigatórias quando o subcomando é invocado:

- **Toolbar fixa** com busca textual, filtros por seção/RQ/ano/tipo de estudo, toggles de dark mode e camada de anotações.
- **Estrutura modular numerada** (§00 prólogo, §01 introdução, ..., §N referências), no estilo dos documentos de referência do projeto. Cada seção é colapsável.
- **Tabela de estudos incluídos** com colunas filtráveis (ID, autor/ano, venue, framework citado, métodos, RQ atendida, QA score). Sticky header ao rolar.
- **Gráficos D3.js** dinâmicos: PRISMA flow diagram (gerado por script), distribuição temporal dos estudos, heatmap de QA scores por dimensão × estudo, rede de co-citação se aplicável.
- **Camada de anotações** estilo professor — comentários, observações, conexões transversais entre seções — que aparecem em margem direita ou tooltip, com toggle on/off na toolbar. **Importante:** o toggle NÃO altera a largura máxima do conteúdo principal — em viewports largos (≥ 1140px) as anotações aparecem na margem externa direita; em viewports menores caem inline abaixo do parágrafo-âncora. Fonte das anotações é a mesma do body em itálico (a11y-friendly, **não** uma cursive handwritten).
- **Referências [n]** numeradas e clicáveis: o número [n] tem `<a href="DOI/URL">` direto para a fonte primária, e o hover mostra a referência completa formatada na norma do projeto.
- **Dark mode toggle** funcional, persistido em `localStorage` apenas se o ambiente permitir; caso contrário, em variável JS.
- **Box "O que esta versão NÃO é"** ao final, no estilo do v1.0.0 do parametros_especificacao_prompts — limites declarados explicitamente.
- **Footer com versão SemVer, data ISO, hash dos artefatos de reprodutibilidade**, link para o pacote no Zenodo (preenchido pelo usuário após upload).

O HTML é **auto-contido**: CSS inline em `<style>`, JS inline em `<script>`, sem dependências externas exceto D3.js v7 carregado via CDN com fallback local opcional. Funciona offline depois de carregado.

### Decisão 37 — HTML Wiki-style segregado em subcomando dedicado (registrado em v3.0.0-rc1)

Após o incidente RS-42 (dogfood falhou com "Esta conversa não pode ser compactada ainda mais" antes de qualquer artefato ser gravado), ficou claro que o pipeline padrão **não pode** assumir geração de HTML como passo obrigatório. O HTML é pesado (200-260 KB de tokens), depende de chunked-render (Decisão 18) e não é o artefato acadêmico — é divulgação. Mistura-lo no fluxo canônico fazia o pipeline falhar antes de produzir o PDF acadêmico, que é o que de fato precisa ser depositado no Zenodo.

**Regra:** o pipeline default da skill produz `manuscript.tex` + `bibliography.bib` → PDF (canônico) + DOCX (secundário). HTML Wiki-style **só é gerado** quando o usuário invoca `ignorantia render --format html-wiki` separadamente, **após** o pipeline canônico ter terminado com sucesso. Implicações:

1. Quando o subcomando `html-wiki` é invocado, o protocolo de chunked-render (Decisão 18, refinado pela Decisão 34 a ser mesclada da Fix 1) é obrigatório.
2. Falha na renderização HTML **não invalida** o pacote acadêmico (PDF + DOCX já estão em disco).
3. O HTML gerado **não vai** para Zenodo — o pacote depositado contém apenas o PDF, DOCX, telemetria, declarações éticas e dados de reprodutibilidade.
4. O HTML é distribuído separadamente (site institucional, blog, redes acadêmicas) como divulgação didática.

Esta decisão fecha o laço aberto pela Decisão 36 (Fix 5 — HTML reclassificado como secundário) ao explicitar **onde no fluxo** o HTML é gerado: nunca dentro do pipeline canônico, sempre como subcomando opt-in posterior. Decisão 18 (chunks) e Decisão 34 (chunked-write) permanecem aplicáveis mas escopadas ao subcomando.

## Saídas secundárias (geradas em paralelo)

Acompanham o pipeline canônico (PDF + DOCX), no mesmo pacote versionado depositado no Zenodo:

- `protocol.md` — protocolo pré-registrado da SLR (template em `assets/templates/protocol.md`).
- `searches.json` — strings booleanas, datas, hits brutos por base.
- `screening.csv` — cada paper com decisão (incluir/excluir/dúvida) e CI/CE invocado.
- `quality-appraisal.csv` — pontuação CASP/DARE/Kitchenham por estudo, por questão.
- `extraction.csv` — formulário de extração preenchido.
- `prisma-flow.svg` e `prisma-flow.pdf` — diagrama PRISMA (gerado por `scripts/prisma_flow.py`).
- `bibliography.bib` — bibliografia em BibTeX, consumida tanto pela compilação canônica do PDF (via `\bibliography{}` no `.tex`) quanto pela conversão DOCX via pandoc.
- `README.md` — versão, hashes, instruções de reprodução.

**Manuscrito acadêmico canônico (default, sempre gerado):**
- `manuscript.tex` — fonte LaTeX que importa `bibliography.bib`.
- `manuscript.pdf` — PDF compilado por `pdflatex + bibtex + pdflatex × 2` (Fix 7). **Este é o artefato depositado no Zenodo.**
- `manuscript.docx` — DOCX convertido do mesmo `.tex` via pandoc (Fix 7), estruturalmente idêntico ao PDF, para revisão Word.

**Distribuição didática opcional (subcomando separado):**
- `manuscript.html` — HTML Wiki-style auto-contido. Gerado **apenas** quando `ignorantia render --format html-wiki` é invocado explicitamente. **Não vai** para o pacote Zenodo. Ver Decisão 37.

## Compliance ético e legal

Aplicação automática conforme o idioma/contexto do manuscrito. Não é opcional.

### Manuscritos em pt-BR

Aplicar **simultaneamente**:

- **Portaria CNPq nº 2.664/2026** — Política de Integridade na Atividade Científica. Inserir bloco "Declaração de uso de Inteligência Artificial Generativa" em §03 (ou §03.x) declarando ferramenta, versão, etapas de uso, e responsabilidade humana. Vedação de autoria à IA. Vedação à inserção de projetos de terceiros em IA para parecer.
- **Documentos de Área CAPES** da disciplina. Carregar via `web_fetch` quando relevante para verificar critérios de avaliação de produção e periódicos prioritários.
- **Sistema CEP/CONEP** e **Resoluções CNS 466/2012 e 510/2016** — quando o tema envolve estudos com humanos. SLR em si geralmente não requer aprovação CEP, mas declarar status no protocolo.
- **LGPD (Lei 13.709/2018)** — não inserir dados pessoais de terceiros em IAG. Cuidado especial com temas de saúde, menores, dados sensíveis.
- **Lei de Direitos Autorais (Lei 9.610/1998)** — citação com atribuição (já garantida pelos DOI/URL clicáveis), paráfrase como padrão, não reproduzir figuras de outras obras.

Carregue `references/compliance-ptbr.md` para detalhes operacionais e o checklist completo. Esse arquivo contém também o **bloco padrão da declaração de IA** que deve entrar tanto no HTML quanto no manuscrito formal.

### Manuscritos internacionais (EN)

Aplicar **simultaneamente**:

- **COPE position on Authorship and AI tools** — IA não é autor; declaração obrigatória; responsabilidade humana integral.
- **ICMJE Recommendations (jan 2024 update)** — Sections II.A.3-4 e IV.A.3.d: declaração no submission cover letter e no manuscript; AI não citável como fonte; revisores não fazem upload de manuscritos a LLMs.
- **Política específica do publisher-alvo** quando conhecido. As principais (Elsevier, Springer Nature, Wiley, Taylor & Francis, Sage, IEEE, ACM, AAAS/Science, Nature, BMJ, JAMA, OUP, CUP, MIT Press, ACS, RSC, APS, ASME, AMA) têm políticas alinhadas com COPE/ICMJE mas com variações específicas — consultar.

Carregue `references/compliance-international.md` para detalhes operacionais, lista de venues de elite por área, política específica de cada publisher, e o **bloco padrão "Declaration of AI use"** em inglês.

### Preferência por publishers/instituições de elite

Tanto na fase 3 (busca) quanto na fase 8 (recomendação de venue para submissão), o skill **prioriza** literatura e venues das seguintes instituições, agrupadas por área:

- Multidisciplinares de elite: Nature, Science, PNAS, Lancet, Cell.
- Medicina/saúde: NEJM, BMJ, JAMA, Cochrane Library, Annals of Internal Medicine.
- CS/Eng/Exatas: IEEE Transactions, ACM Transactions, JMLR, CACM, conferências top (NeurIPS, ICML, ICLR, ACL, CHI, SIGGRAPH, ICSE).
- Química: ACS (JACS), Wiley (Angewandte), RSC (Chem Soc Rev), Nature Chemistry.
- Física: APS (PRL, PRX, RMP), Nature Physics.
- Engenharia: ASME, IEEE.
- Educação: AERA/Sage, APA, Computers & Education (Elsevier), BJET (Wiley).
- Psicologia: APA journals, Annual Review of Psychology, Trends in Cognitive Sciences.
- Imprensas universitárias: OUP, CUP, MIT Press.
- OA de elite: PLOS, eLife, Royal Society Open Science.

A lista completa por área, com URLs e ISSNs, está em `references/compliance-international.md`. Na **Fase 8**, a skill produz uma lista de **3-5 venues sugeridos** para submissão, com nome, publisher, URL da política de IA do publisher, ISSN, JIF/CiteScore mais recente, ciclo editorial típico, e modelo de acesso.

### Acesso legítimo a bases pagas

Sempre que o usuário não tem acesso institucional direto:

1. Sugerir login via **Portal de Periódicos da CAPES com CAFe** (cobre Scopus, WoS, IEEE Xplore, ScienceDirect, Springer Link, ACM, Wiley para vinculados a IES brasileiras).
2. Sugerir **Unpaywall** (api.unpaywall.org) para localizar versões OA dos papers paywalled.
3. Sugerir **arXiv** e repositórios institucionais (BDTD, OSF) para preprints e versões aceitas.
4. Sugerir **contato direto com autores correspondentes** por e-mail.
5. **Não sugerir nem desaconselhar plataformas em disputa judicial.** Conforme Decisão 17 (v2.7.0), o `ignorantia` não toma posição sobre essas plataformas; itens não resolvidos por Tier 0 entram no `gap_report.md` e o usuário decide como providenciá-los.

A skill pode gerar, sob demanda, um script Python (`scripts/download_via_proxy.py`) que automatiza o uso do proxy institucional **legítimo** quando o usuário fornece suas credenciais.

## Versionamento SemVer das saídas

**Convenção:** `<linha-de-pesquisa>.<inclusão-exclusão>.<correção>` (MAJOR.MINOR.PATCH).

- **MAJOR** — mudança na linha de pesquisa: nova RQ, novo escopo, troca de metodologia (PRISMA → Kitchenham), troca de área. Versão 2.x.x rompe com 1.x.x.
- **MINOR** — inclusão ou exclusão de estudos no corpus: novas buscas, novo critério aplicado, ampliação ou restrição da janela temporal. A linha de pesquisa permanece; o conjunto sintetizado muda.
- **PATCH** — correções: erro tipográfico, citação ajustada, ortografia, número errado em tabela. Não muda o conteúdo substantivo.

A primeira saída completa é **v1.0.0**. Cada saída posterior é um pacote novo (HTML + secundários + flow + bib + readme), com seu próprio número de versão e data ISO. **Saídas antigas não são editadas — elas permanecem como registro histórico.** O `README.md` de cada versão lista o que mudou em relação à anterior, com link ao pacote anterior se houver.

A ler obrigatoriamente: `references/semver-policy.md` antes de qualquer publicação de versão.

## PRISMA-2020 — execução completa, não apenas documentação

Estes elementos são todos **executados**, com artefato real saindo do pipeline:

1. **Protocolo pré-registrado** — gerado primeiro, validado pelo usuário antes de qualquer busca. (`protocol.md`)
2. **Lista finita e fechada de bases** declarada antes da busca. (Seção do protocolo)
3. **Strings booleanas por base** — uma por base na sintaxe correta (ACM, IEEE Xplore, Scopus, WoS, dblp, SciELO, CAPES, etc.). (`searches.json`)
4. **Critérios de inclusão/exclusão** numerados, aplicados, decisão registrada para cada paper. (`screening.csv`)
5. **PRISMA flow diagram** com números reais — identificados, deduplicados, screened, full-text avaliados, incluídos. (`prisma-flow.svg/pdf`, gerado por `scripts/prisma_flow.py`)
6. **Quality appraisal** CASP ou DARE para cada estudo incluído. (`quality-appraisal.csv`, instrumento descrito em `assets/templates/quality-appraisal.md`)
7. **Extração de dados** num formulário pré-definido. (`extraction.csv`, schema em `assets/templates/extraction-form.md`)
8. **Reprodutibilidade** — outro pesquisador que rode o pipeline com o protocolo chega ao mesmo conjunto de papers (sujeito a atualizações dos índices). Pacote completo no Zenodo.

**Cohen's kappa entre dois revisores:** o skill **não simula** o segundo revisor. O pacote vai ao Zenodo, dois professores humanos fazem a revisão independente, e o kappa é computado por eles. O skill produz a primeira passagem e a infraestrutura para a segunda.

Para temas de engenharia de software, **Kitchenham complementa PRISMA**: as questões QA1–QA8 entram no quality appraisal, e snowballing (Wohlin 2014) é executado a partir dos seed papers identificados.

## Fluxo de trabalho (8 fases)

### Fase 1 — Entrevista de escopo

<phase_1_directive>
Verbo: **conduzir** entrevista estruturada de escopo, em pt-BR (ou no idioma do usuário).
Objeto: capturar 8 dimensões obrigatórias antes de redigir o protocolo.
Critério de aceitação: nenhuma dimensão fica em branco; o usuário confirmou a interpretação por meio de resposta explícita.
Audiência da pergunta: o usuário (não o LLM mais tarde lendo o protocolo).
</phase_1_directive>

Pergunte cobrindo as 8 dimensões abaixo. Use `ask_user_input_v0` quando o ambiente permitir (mais cômodo no mobile):

1. **Tema e pergunta de pesquisa.** Refine até virar PICO (saúde) ou PICOC (SE) ou equivalente para a área.
2. **Idioma do manuscrito final.** PT-BR ou EN. Determina norma de citação:
   - PT-BR (qualquer área) → ABNT
   - EN + exatas/SE/CS → IEEE
   - EN + saúde → Vancouver
   - EN + psicologia/educação → APA
3. **Modalidade.** PRISMA-2020 sempre. Kitchenham se SE/CS.
4. **Janela temporal.** Default: últimos 10 anos.
5. **Tipos de estudo.** Peer-reviewed, preprints, teses, anais, gray lit.
6. **Acesso institucional** a Scopus/WoS/IEEE Xplore/ACM DL/CAPES — para gerar scripts de download legítimo via proxy.
7. **Pacote de revisão.** Avise que o pacote final será depositado no Zenodo; revisão humana por dois professores e kappa ocorrem fora do skill.
8. **Versão de partida.** Se é a primeira passagem (será v1.0.0); se é continuação de uma SLR anterior do mesmo usuário, informe a versão anterior para gerar v1.1.0 / v2.0.0 / etc.
9. **Venue-alvo (opcional).** Se o usuário já tem um periódico/conferência em mente para submissão, registre — a skill ajusta norma de citação, comprimento, e estrutura ao máximo. Se não tem, a Fase 8 sugere 3-5 venues. Em pt-BR, perguntar também se há programa de pós-graduação stricto sensu vinculado (Plataforma Sucupira). Em EN, perguntar a área-foco para alinhar com o publisher de elite mais adequado.
10. **Vinculação a financiador.** Se o usuário recebe fomento CNPq/CAPES/FAP, informar — afeta as declarações obrigatórias e o local de pré-registro do protocolo (Zenodo serve em todos os casos; PROSPERO se for SLR de saúde).

Carregue `references/interview-protocol.md` para o checklist completo.

### Fase 2 — Protocolo pré-registrado

Use `assets/templates/protocol.md`. Valide explicitamente com o usuário antes de qualquer busca. Salve como `protocol-v<X.Y.Z>.md`.

### Fase 3 — Execução das buscas

**Bases executadas diretamente** (scripts em `scripts/`): arXiv, Semantic Scholar, dblp, Crossref, SciELO, mais `web_search`/`web_fetch` para Scholar, BDTD, Dialnet, Redalyc.

**Bases guiadas** (Scopus, WoS, IEEE Xplore, ScienceDirect, Springer Link, Portal CAPES): gerar string booleana correta + instruções; se acesso institucional, gerar Python script via proxy. Nunca burlar paywall.

Carregue `references/databases/international.md` ou `references/databases/portuguese.md`.

Para cada base: data, string usada, hits brutos. Salvar em `searches.json`.

### Fase 4 — Deduplicação e screening

`scripts/deduplicate.py` para deduplicar (DOI > arXiv ID > título+autor+ano). Screening de título/abstract aplicando CI/CE. Screening full-text dos sobreviventes (PDFs via Unpaywall + repositórios institucionais quando o usuário tem acesso). Cada decisão fica em `screening.csv`.

### Fase 5 — Quality appraisal

CASP ou DARE para todos. Kitchenham QA1–QA8 adicional se SE. Score por estudo. Threshold: estudos abaixo do corte ficam sinalizados na síntese, mas a inclusão/exclusão pelo QA é registrada. Saída: `quality-appraisal.csv`. Carregue `assets/templates/quality-appraisal.md`.

### Fase 6 — Extração

Formulário pré-definido (`assets/templates/extraction-form.md`). Saída: `extraction.csv`.

### Fase 7 — Síntese e geração do HTML interativo

A síntese é narrativa-temática por RQ, com cross-tabulação por dimensões (Munzner/Yi/CASP — adaptado à área). Tabelas comparativas e gráficos D3.js complementam.

A geração do HTML usa `assets/templates/manuscript-template.html` como base e `scripts/render_manuscript.py` para:

- Substituir placeholders com dados do `extraction.csv`, `quality-appraisal.csv`, `searches.json`.
- Embutir os gráficos D3.js com dados pre-renderizados (não dependem de network em runtime).
- Embutir o PRISMA flow diagram (SVG inline).
- Renderizar referências como `[n]` com `<a href="DOI">` e `<span class="ref-tooltip">` para o tooltip.
- Renderizar a camada de anotações como `<aside class="annotation" data-anchor="paragraph-id">` que aparece via toggle.
- Aplicar a paleta correspondente à área (dark mode opcional).
- **Inserir o bloco "Declaração de uso de IAG" (pt-BR) ou "Declaration of AI use" (EN)** em §03.x, conforme `references/compliance-ptbr.md` ou `references/compliance-international.md`.

Carregue o arquivo de norma correspondente: `references/citation-styles/{ieee|vancouver|apa|abnt}.md`. Carregue `references/output-design-patterns.md` para detalhes de layout, paleta, e padrões de interação.

### Fase 8 — Manuscrito formal opcional + sugestão de venues + empacotamento

**Manuscrito formal**, se solicitado:
- Exatas + EN → LaTeX (IEEE) — `assets/templates/manuscript-ieee.tex` + bibtex
- Outros → docx — usando `python-docx` e a norma definida (com cuidado especial para ABNT)

**Sugestão de venues para submissão.** Antes do empacotamento, gere uma lista de **3-5 venues** alinhados ao tema, ao idioma, e à preferência por publishers de elite. Para cada venue:

- Nome (periódico ou conferência)
- Publisher / sociedade
- ISSN ou identificador
- URL da política de IA do publisher (Elsevier, Springer Nature, Wiley, T&F, Sage, IEEE, ACM, etc.)
- Indicador de qualidade: JIF/CiteScore mais recente OU estrato Qualis (para pt-BR, ciclo 2021-2024 enquanto vigente)
- Modelo de acesso (subscription, hybrid, OA Gold com APC, OA Diamond)
- Estimativa de ciclo editorial (semanas até primeira decisão)
- Justificativa breve da adequação ao tema

Lista canônica das instituições/publishers a priorizar, por área, em `references/compliance-international.md`. Para pt-BR, complementar com a verificação dos Documentos de Área CAPES (`references/compliance-ptbr.md`).

Salve em `venue-suggestions.md` no pacote.

**Empacote** tudo em `ignorantia-<area-slug>-<topic-slug>-v<X.Y.Z>.zip` com:

- `manuscript.html` (sempre)
- `manuscript.pdf` ou `manuscript.docx` (se solicitado)
- `protocol.md`, `searches.json`, `screening.csv`, `quality-appraisal.csv`, `extraction.csv`
- `prisma-flow.svg`, `prisma-flow.pdf`
- `references.bib`
- `venue-suggestions.md` — lista de 3-5 venues
- `ai-declaration.md` — cópia standalone da declaração de uso de IA (pt-BR ou EN)
- `compliance-checklist.md` — checklist com cada item marcado (CNPq art. 9, COPE/ICMJE quando EN, LGPD, CEP/CONEP, LDA, periódicos prioritários consultados)
- **`avaliacao_v<X.Y.Z>.md`** — relatório de avaliação automática contra a rubrica de qualidade. Gerado obrigatoriamente por `scripts/generate_assessment.py` ao final da Fase 8. Contém: nota final 0.0–10.0, notas por dimensão (D1 metodologia, D2 compliance, D3 corpus, D4 textual, D5 apresentação), bonificadores aplicados, eliminatórios verificados, **lista priorizada do que falta para nota 10.0** (separada em Crítico / Importante / Polimento), e veículo-alvo recomendado conforme a faixa de nota. **Critério essencial:** a nota 10.0 só é atingida quando o manuscrito está pronto para submissão a pelo menos UM venue de elite máxima (Elsevier/Nature/Wiley/T&F/Sage flagships, IEEE/ACM Transactions, ASME, APS, ACS, RSC, AAAS, AMA/JAMA, BMJ, NEJM/MMS, OUP, CUP, MIT Press) ou Qualis A1 nacional para pt-BR. A nota é arredondada SEMPRE para baixo. Detalhes da rubrica em `references/quality-rubric.md`.
- `README.md` com SemVer, datas, hashes SHA-256, link para versão anterior se houver, e resumo do checklist + nota da avaliação automática
- `LICENSE` (CC-BY-4.0 default, confirmado com usuário)

**Instrua o usuário sobre upload ao Zenodo:**

1. https://zenodo.org/uploads/new
2. Comunidade: `ignorantia` (sugerida) ou específica da área.
3. Versão: o número SemVer + tag `slr` + tag da área.
4. License: CC-BY-4.0.
5. Após o upload, o DOI obtido entra no protocolo da próxima versão.
6. Para SLRs em saúde, considerar pré-registro adicional no PROSPERO (https://www.crd.york.ac.uk/prospero/).
7. Para vinculados a programa de pós-graduação stricto sensu brasileiro, declarar a publicação na Plataforma Sucupira após o aceite do periódico-alvo.

## Padrões de design do HTML — referência rápida (subcomando `html-wiki`)

> Aplica-se **apenas** quando o subcomando opcional de renderização HTML é invocado (Decisão 37). O pipeline canônico (PDF + DOCX) não usa estes padrões — usa LaTeX puro com BibTeX externo (Fix 6).

A leitura completa está em `references/output-design-patterns.md`. Pontos críticos:

- **Numeração de seções** explícita (§00–§N), igual aos documentos de referência do projeto.
- **Tiers/categorias com cor temática.** Ex.: tier A vermelho, B laranja, C azul, D verde, E cinza. Definir paleta no início do template, derivar do tema da área.
- **Referências [n] com tooltip** ao hover: mostra a referência formatada completa. Click vai ao DOI/URL.
- **Sticky toolbar** no topo, sempre visível. Layout: busca à esquerda, filtros no meio, toggles à direita.
- **Tabela com filtros multi-coluna**, blocos colapsáveis. Como a referência do `prompt_engineering_reference_v3_IEEE_3`.
- **Box "O que esta versão NÃO é"** ao final do método — limites declarados.
- **Anotações de professor** estilo margem do livro: `<aside>` posicionado absolutamente à direita do parágrafo âncora; revelado por toggle.
- **Dark mode** via CSS vars + class `.dark` no `<html>`.
- **Acessibilidade:** ARIA labels, contraste mínimo WCAG AA, `prefers-reduced-motion` respeitado nas transições.

## Quando algo falhar

- **Base inacessível:** documente como tentada, falhou, e prossiga.
- **Poucos resultados (<10 incluídos):** alerte usuário, sugira relaxar critérios. **Não invente** estudos.
- **Muitos resultados (>500):** ofereça filtros adicionais documentados.
- **Tema fora da capacidade:** se o tema requer base de dados que o skill não pode acessar nem orientar (ex.: base militar classificada), declare.

## Arquivos de referência

### Existentes desde v1.x

- `references/interview-protocol.md` — checklist da entrevista
- `references/prisma-2020.md` — checklist PRISMA-2020 e diagrama
- `references/kitchenham.md` — guidelines Kitchenham
- `references/citation-styles/{ieee,vancouver,apa,abnt}.md` — exemplos por tipo de fonte
- `references/databases/international.md` — sintaxe de busca por base internacional
- `references/databases/portuguese.md` — sintaxe de busca por base lusófona
- `references/output-design-patterns.md` — padrões de design do HTML interativo
- `references/semver-policy.md` — política de versionamento SemVer das saídas
- `references/compliance-ptbr.md` — Portaria CNPq nº 2.664/2026, CAPES, CEP/CONEP, LGPD, LDA
- `references/compliance-international.md` — COPE, ICMJE, políticas dos publishers de elite
- `references/quality-rubric.md` — rubrica de avaliação 0.0-10.0 com 5 dimensões
- `assets/templates/protocol.md` — template de protocolo pré-registrado
- `assets/templates/extraction-form.md` — schema de extração
- `assets/templates/quality-appraisal.md` — instrumentos CASP/DARE/Kitchenham
- `assets/templates/manuscript-template.html` — template HTML interativo

### Novos na v2.0

- `references/profiles/_schema/venue_profile.schema.json` — JSON Schema dos perfis de venue
- `references/profiles/_guidelines/{prisma-2020,prisma-s,prisma-scr,prisma-rr,mecir,campbell-standards,sigsoft-empirical-standards}.yaml` — perfis declarativos das reporting guidelines
- `references/profiles/venues_a1_br/{csp_fiocruz,rsp_usp,csc_abrasco,ep_usp,rbe_anped,cp_fcc,jbcs_sbc,jistem_usp,rbie_sbc}.yaml` — 9 venues brasileiros
- `references/profiles/venues_q1_int/{nejm,lancet,bmj,cdsr,tse_ieee,tosem_acm,emse_springer,err_elsevier,rer_aera,campbell_sage,rsm_wiley}.yaml` — 11 venues Q1 internacionais
- `references/equator-monitoring.md` — monitoramento de guidelines de IA emergentes
- `references/claude-chat-tasks/c7-semantic-review.md` — prompt estruturado para C7 (releitura semântica) — *presente no full package; removido do dist por limite de 200 arquivos*
- `references/claude-chat-tasks/c8-originality-check.md` — prompt para C8 (originalidade real) — *idem*
- `references/claude-chat-tasks/c9-linguistic-quality.md` — prompt para C9 (qualidade linguística) — *idem*
- `references/claude-chat-tasks/c10-t4-depth-and-temperature.md` — prompts para C10 (profundidade) e T4 (agregação) — *idem*
- `references/draft/whitepaper-PRELIMINARY.md` — whitepaper preliminar do Sprint Badge (rotulado como rascunho até v3.0) — *presente no full package; removido do dist*
- `references/user-guidance/post-deposit-actions.md` — orientações ao usuário sobre mitigações Cat. B (vinculação bidirecional, auditoria periódica, open peer review) — fora do escopo do skill

### Scripts

- `scripts/searches/search_*.py` — buscas por base (arXiv, S2, dblp, Crossref, SciELO)
- `scripts/deduplicate.py` — deduplicação por DOI > arXiv ID > título+autor+ano
- `scripts/prisma_flow.py` — gerador de diagrama PRISMA SVG/PDF
- `scripts/render_chunks.py` — **renderer HTML canônico** (usado pelo pipeline_finalize). Renderização incremental em chunks com checkpoint. Decisão 18.
- `scripts/render_v2.py` — render alternativo 4-tabs (Manuscrito/Auditoria/Dados/Venues). Não é o caminho do pipeline_finalize. Útil para visualização rica standalone.
- `scripts/render_manuscript.py` — **DEPRECATED em v2.21.0** (legacy v1 com aviso no topo do arquivo). Mantido apenas para compatibilidade com testes históricos.
- `scripts/render_docx_abnt.py` — render Word ABNT (Decisão 31). Suporta `--contextual-preamble`.
- `scripts/render_latex.py` — render TeX/PDF ABNT (Decisão 32). Suporta `--contextual-preamble` com conversor Markdown→LaTeX completo (v2.20.0).
- `scripts/pipeline_finalize.py` — **orquestrador das 6 etapas finais**. Chama os 4 renderers + cross_tab + format_abnt + screening_pipeline. Suporta `--contextual-preamble` propagando aos 3 renderers (HTML/docx/latex) desde v2.21.0.
- `scripts/contextual_preamble.py` — gera "O campo onde este artigo vive" via Wikipedia + Wikidata (DD-11).
- `scripts/screening_pipeline.py` — Camada 2 PRISMA-2020 com CSV auditável (DD-10).
- `scripts/generate_assessment.py` — gera `avaliacao_v<X.Y.Z>.md` aplicando a rubrica
- `scripts/slr_to_package.py` — empacota o pacote final
- `scripts/attest_phase_transition.py` — attestation entre fases
- `scripts/assessor/` — engine de auditoria (eliminators, plagiarism, rubric, sprint_badge experimental, temperature, venues, visual_aids, self_test)
- **NOVO** `scripts/compliance/` — engine de compliance editorial determinístico (parse, hard_rules, guidelines, scope, engine; Stages 1-7)
- **NOVO** `scripts/zenodo/` — gerador do pacote de reprodutibilidade + verificador de DOIs (Crossref + Retraction Watch + OpenAlex)
