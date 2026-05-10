# DECISIONS-REGISTRY — full numbered Decisão log (developer-facing)

> **Audience: developer.** This is the canonical, numbered registry of every
> editorial / design decision made in the skill, with full version history,
> fix annotations, and verification pointers. Cited in commits, PRs, issues,
> and CHANGELOG entries.
>
> **This file is NOT shipped in the production zip.** The operator-facing
> `SKILL.md` describes the same rules in scientific prose, without numbering.
>
> The numbering provides a stable developer index. If you reword a rule in
> SKILL.md but the underlying decision stands, the registry entry keeps its
> number; the entry's body gets a new dated revision line. If you withdraw
> a decision, mark the entry as withdrawn but keep the number — never reuse it.
>
> Cross-reference: `dev-docs/DECISIONS.xml` is the engineering decisions log
> (DD-N — architecture / adapter / ToS / strategy decisions, separate stream
> from the editorial Decisões registered here).

---


## Decisões editoriais v2.0 — três modos de saída e mitigações

> **Registro central de decisões:** Para o registro canônico de **todas** as decisões editoriais e de design da skill (incluindo decisões de arquitetura de adapters, ToS, e estratégia de implementação), consultar `references/DECISIONS.xml`. Para o registro de plataformas que NÃO serão implementadas e razões técnicas, consultar `references/WONT_IMPLEMENT.xml`. Para a estratégia de rodadas em curso, consultar `references/IMPLEMENTATION_STRATEGY.xml`.

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

O arquivo `references/equator-monitoring.xml` lista as guidelines de IA emergentes (PRISMA-AI, TRIPOD-AI, CHART, CONSORT-AI, SPIRIT-AI, etc.). Job mensal verifica atualizações. Quando uma guideline relevante for publicada, abrir issue obrigatória para incorporação à v2.x.

### Decisão 6 — "Living review" reservado a protocolo formal

O termo **"living review"** é reservado a casos que cumprem o protocolo formal Cochrane/Campbell (atualização ≥quadrimestral, PRISMA-LSR, novo PROSPERO ou OSF tracking). Em todos os demais casos, o skill usa **"periodically updated review"** ou **"time-bounded review (search closed YYYY-MM-DD)"**.

### Decisão 7 — Idiomas v2.0

- **Geração** (ghostwriter): primário inglês (alvo internacional); secundários português e espanhol.
- **Avaliação** (compliance): suporta os mesmos três idiomas.
- **Mandarim, árabe, japonês, coreano**: roadmap v2.x+, exigem parsers específicos.

### Decisão 8 — Mitigações de conflito de interesse — Categoria A (5 itens) obrigatórios

Toda revisão produzida pelo skill deve incluir, sem exceção:

1. **Pré-registro PROSPERO/OSF com timestamp** antes da decisão de design (template gerado pelo skill).
2. **Declaração CoI no §01 do manuscrito** que (a) **nomeia o projeto específico** ao qual a revisão se vincula (ex: "projeto Ler e Escrever / EMAI gamificado") — nunca usar a expressão genérica "projeto subjacente", que é meta-discurso de skill —, (b) descreve o tipo de relação do autor com o projeto, e (c) declara o timing da revisão em relação às decisões de design que ela fundamenta. A declaração é redigida em prosa científica neutra; ver template em `assets/templates/protocol.xml` §01 e exemplos pareados em `references/artifact-vocabulary-policy.xml`.
3. **Seção obrigatória "Evidência contrária encontrada"** — declarar achados que contradizem decisões de projeto, ou declarar honestamente que nenhum foi identificado.
4. **Categorização do propósito da revisão**, gravada **apenas no metadado JSON** do pacote (`reproducibility_manifest.json`), em uma das quatro classes operacionais — *design-foundational* (a revisão fundamenta decisões de design subsequentes do autor no mesmo projeto), *design-validation* (a revisão valida empiricamente uma decisão de design já tomada), *design-correction* (a revisão diagnostica falha numa decisão prévia e propõe correção), *independent-inquiry* (a revisão não está ligada a decisão de design específica). Os tokens literais de enum (`design_foundational`, `design_validation`, `design_correction`, `independent_inquiry`) ficam **apenas no JSON**; em prosa de manuscript/protocol/README, traduzir para a descrição correspondente. A literal `design_foundational` no corpo de qualquer artefato depositável é violação da Decisão 41 e bloqueia o empacotamento.
5. **Pacote de reprodutibilidade Zenodo** completo (Decisão 2).

Mitigações de Categoria B (vinculação bidirecional, auditoria periódica, open peer review) são **decisões editoriais do autor**, fora do escopo do skill. Documentadas em `references/user-guidance/post-deposit-actions.xml`.

### Decisão 9 — Sprint Badge marcado como experimental/preview

O Sprint Badge atual (calibrado com n=187 SLRs em v1.x) é mantido na v2.0 mas explicitamente rotulado como **experimental/preview**. Calibração definitiva (regressiva SJR+JIF, n=1.600-3.200) é alvo da v3.0 no Cowork. O whitepaper preliminar está em `references/draft/whitepaper-PRELIMINARY.xml` com aviso explícito.

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

Cada modo tem perfil individual detalhado em três layers (modo + reporting guideline + venue padrão+alternativas) em `references/modes/mode-XX-*.md`. O panorama master está em `references/modes/MODES_OVERVIEW.xml`.

### Decisão 11 — Política OA-first (3 tiers de bases)

A v2.1 formaliza a constraint operacional de que o ghostwriter SÓ consulta bases gratuitas (Tier 1) e bases com metadados livres (Tier 2). Material atrás de paywall (Tier 3) só é acessado via fornecimento manual pelo usuário (CSV/RIS exportado da instituição, PDFs específicos, etc.).

- **Tier 1 — sempre OA, sempre buscar.** PubMed Central, EuropePMC, LILACS, SciELO, ERIC OA, arXiv, DBLP, DOAJ, OpenAlex (`is_oa=true`), Crossref (filtro OA), OSF Preprints, Zenodo, etc.
- **Tier 2 — metadados livres, full-text pode requerer fornecimento.** Crossref geral, OpenAlex geral, Semantic Scholar, PubMed completo, etc. O ghostwriter declara explicitamente quando full-text não acessível.
- **Tier 3 — apenas via material fornecido pelo usuário.** Scopus, Web of Science, Embase, IEEE Xplore subset paywall, ACM DL subset paywall, Elsevier ScienceDirect, etc.

Cada modo declara os mínimos esperados de bases Tier 1 (e quando aplicável, se Tier 3 via fornecimento é praticamente exigido). O orquestrador `scripts/searches/search_orchestrator.py` aplica a política e gera disclosure ao usuário pré- e pós-busca. Detalhes completos em `references/databases/oa-tiers.xml`.

### Decisão 12 — Padrão de venues OA-first com alternativas explicadas

Para cada modo, a ferramenta apresenta:

1. **Venue padrão**: OA-gratuito ($0 APC) ou de baixo custo, área-fit. Exemplos: JOSS para Software Paper; Zenodo para Position/Technical/White Paper; Qualis A1 BR fully OA (Cadernos de Saúde Pública, Educação e Pesquisa) para Scoping/Integrative/Realist em saúde/educação BR.
2. **Alternativas explicadas**: 1-3 venues hybrid/paywall com APC declarado, para usuários que tenham orçamento ou preferência específica.
3. **Transparência total**: ao recomendar venue, a ferramenta explica em texto livre o porquê do padrão e o porquê das alternativas, deixando a escolha final ao usuário.

A v2.0 inicial tinha cobertura OA internacional pobre (apenas Campbell). **A v2.2.0 fechou esse gap crítico** adicionando PLOS ONE (saúde/multi, $1,695 APC), F1000Research (multi/peer review aberto, $1,595 APC) e Frontiers in Education (educação, ~$2,200 APC). Brasil é upper-middle income pelo World Bank, autores brasileiros não recebem waiver automático mas podem aplicar via fee support programs declarados em cada perfil.

Tempo estimado típico de produção do ghostwriter para qualquer modo: ~15 minutos (estimativa do usuário; campo formal `time_to_produce_estimate: "user_estimate_15min_unvalidated"` em cada perfil de modo, a ser atualizado após casos reais documentados).

### Decisão 13 — Qualis CAPES em transição (registrado em v2.2.0)

A CAPES anunciou em janeiro/2026 que **a classificação conceitual A1-C do Qualis Periódicos será descontinuada para o quadriênio 2025-2028**. Os perfis YAML do ignorantia v2.x usam o quadriênio 2021-2024 (último válido com classificação conceitual) como referência canônica. Quando o novo modelo de avaliação CAPES for publicado, será necessário ciclo de migração dos perfis YAML — registrado como gap em `references/equator-monitoring.xml` para revisão futura. A ferramenta declara explicitamente o quadriênio referenciado ao apresentar Qualis ao usuário.

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

### Decisão 18 — HTML em chunks/append na Fase 7 (registrado em v2.8.0, implementado em v2.10.0; **rebaixada a artefato secundário** em v2.23.1, Decisão 36; **escopo limitado ao subcomando `html-wiki`** em v3.0.0-rc1, Decisão 37)

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

A v2.10.0 adicionou teste mecânico que parseia o template final e falha o build se a string literal `"ignorantia"` aparecer. **A v2.23.1 (Fix 10 do RS-42 remediation) expande o escopo** com `scripts/check_decision_19_vocabulary.py`, que vetta uma **família** de leakages encontrados no dogfood RS-42 v1.0.0:

- **SemVer rhetoric** (`v1.0.0`, `v1.1.0`) — texto acadêmico diz "future work", não "v1.1.0".
- **Referência procedural interna** (`Decisão 8 do protocolo`, `Decisão 22`) — atribui as escolhas metodológicas a um item de checklist em vez do pesquisador.
- **Classificação interna** (`Categoria A`, `Categoria B`) — taxonomia de mitigações é metadado, não prosa.
- **Nomes literais de campos JSON** (`review_purpose`, `purpose_per_stage`, `human_oversight`, `execution_method`, etc.) — pertencem ao metadado, não à voz acadêmica.
- **Brand `ignorantia`** consolidado sob o mesmo verificador.

O verificador é binding: exit code 2 quando há qualquer violação. Deve ser encadeado via `&&` antes do empacotamento Zenodo. Cobertura mecânica em `tests/integration/test_v2231_decision_19_vocabulary.py` (17 casos, incluindo regressão direta com frases extraídas literalmente do RS-42 v1.0.0). LaTeX preamble é ignorado para não falsificar com `\\usepackage[utf8]`.

**A v2.23.3 (Fix 19 do RS-42 remediation, Decisão 41) expande novamente** o escopo para deposit-wide e adiciona 8 padrões novos (`Tier N`, `FALLBACK_MD`, `KEY → PROXY`, `DD-N`, valores enum de `review_purpose`, `projeto subjacente`, `outras N revisões`, `função declaratória/instrumental`) — ver Decisão 41 para o protocolo completo e a tabela de tradução em `references/artifact-vocabulary-policy.xml`.

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

**Adendo de manutenção (v2.23.1, Fix 12 do RS-42 remediation):** o dogfood de 2026-05-08 revelou que a Decisão 20 era seguida só intermitentemente — o consumidor lia o texto descritivo e ainda escrevia `Phase 3 invocou search_orchestrator.py` no manuscrito. A causa: nada na skill tornava a persona mecanicamente acionável. A correção introduziu duas camadas (não documentadas aqui na seção descritiva, mas no corpo operacional da skill):

- `assets/templates/persona-voice.xml` — scaffold pareado anti-padrão ↔ persona, lido pelo consumidor na Fase 7. Operação detalhada em `<mandatories>` e na seção de fluxo de trabalho.
- `scripts/check_persona_voice.py` — verificador heurístico advisory/strict. Operação detalhada em `<mandatories>`.

**Para quem mantém esta skill:** a Decisão 20 sozinha não bloqueia o vazamento de voz; o scaffold + verificador são o caminho mecânico. Remover qualquer um deles re-abre o anti-padrão observado no dogfood RS-42 v1.0.0.

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

### Decisão 22 — Re-execução obrigatória de buscas em data diferente em cada nova execução (registrado em v2.9.0; vocabulário corrigido em v2.23.3, Fix 19.5)

A rubrica antiga continha "(Importante) Reprodutibilidade entre runs não testada — re-executar as buscas em datas diferentes". Esse critério foi reescrito como **obrigação**: cada nova execução completa do pipeline **deve** re-rodar as buscas em data distinta da execução anterior e reportar diff contra ela. Estabilidade ≥ 95% em N de hits brutos por base é o threshold; abaixo disso o skill emite warning e exige justificativa do usuário.

**Em prosa do manuscrito (ex: §06 limitações, §07 trabalhos futuros):** descrever como "re-execução em data subsequente" ou "execução futura". A retórica SemVer interna (`subversão`, `incremento PATCH/MINOR`, `v1.1.0`) é vocabulário de gerenciamento de versão e **não aparece em prosa de artefato** — fica apenas em filename do pacote (`ignorantia-...-v1.1.0.zip`) e em metadado JSON.

**Implementação técnica:** o `reproducibility_manifest.yaml` ganha o bloco `search_runs` com timestamps por execução. O orquestrador detecta automaticamente quando `today != last_run_date` e re-executa as bases de acesso aberto antes de prosseguir para as comerciais.

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

**A v2.9.0 remove** quaisquer linguagens em `references/quality-rubric.xml` ou na seção §09 gerada do manuscrito que tratem EN/PT/ES como restrição. Idiomas adicionais (mandarim, francês, alemão) ficam como roadmap declarado para v3.0+/Cowork.

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

### Decisão 31 — Geração `.docx` ABNT obrigatória (registrado em v2.10.0; redefinida via `pandoc` a partir do `.tex` em v2.23.1, Fix 7)

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

### Decisão 32 — Geração `.tex` + `.pdf` obrigatória (registrado em v2.10.0; reclassificada como **artefato canônico** em v2.23.1, Decisão 36)

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

### Decisão 36 — Reclassificação do HTML como artefato secundário; PDF/DOCX como artefatos acadêmicos canônicos (registrado em v2.23.1)

**Reclassificação de hierarquia de saída**. A v2.10.0 / Decisão 18
estabeleceu o `manuscript.html` como "renderer canônico" via
`scripts/render_chunks.py`. Operacionalmente, em uso real
(RS-42 dogfood, 2026-05-08), ficou claro que o HTML não é o
artefato acadêmico — é um relatório informativo estilo Wikipedia
com design instrucional, útil para banca, white paper e leitura
de divulgação, mas **não é o que vai pro Zenodo como depósito de
IP**. Para registro acadêmico (proteção contra roubo de ideias,
citação canônica em catálogos), o que conta é PDF compilado de
LaTeX + BibTeX.

**Nova hierarquia (vinculante a partir de v2.23.1):**

| Artefato | Papel | Geração default? |
|---|---|---|
| `manuscript.tex` | **Source-of-truth** do artigo | ✅ sim |
| `bibliography.bib` | BibTeX entries (referenciado por `\bibliography{}`) | ✅ sim (após Fix 6) |
| `manuscript.pdf` | **Citação canônica do depósito Zenodo** (compilado por `pdflatex+bibtex`) | ✅ sim |
| `manuscript.docx` | Formato secundário para revisores que pedem `.docx` (convertido via `pandoc -s manuscript.tex -o manuscript.docx`) | ✅ sim |
| `manuscript.html` | Relatório informativo Wikipedia-style (TOC, dark mode, design instrucional) | ❌ **não — só com flag explícita** |

**Implicações operacionais:**

1. **Skill **não** gera HTML por padrão.** O HTML continua acessível
   mas exige requisição explícita do usuário ("quero o HTML
   também", "gere a versão Wikipedia", `--with-html` no CLI).
   Sem isso, o pipeline produz apenas `.tex` + `.bib` + `.pdf` +
   `.docx`.

2. **HTML, quando pedido, roda em sessão separada.** O HTML
   chunked-write (Decisão 34) acontece numa invocação
   independente, depois que o artigo acadêmico (`.pdf`) já
   foi gerado e salvo. Nunca na mesma sessão de chat. Isso
   alinha com Fix 8 (relocação do protocolo de chunked render
   para subcomando separado).

3. **Decisões 18, 31, 32 permanecem em vigor** para os
   respectivos artefatos, mas a **canonicidade** muda: o
   "renderer canônico" agora é `render_latex.py` → PDF
   (Decisão 32 reclassificada). O HTML chunked
   (`render_chunks.py`, Decisão 18) continua sendo o **canônico
   para o caminho HTML** quando o caminho HTML é pedido — só
   que esse caminho deixou de ser default.

4. **Pacote Zenodo**: `manuscript.pdf` + `manuscript.docx` +
   `manuscript.tex` + `bibliography.bib` + protocolos +
   logs + declarações. `manuscript.html` permanece em
   **arquivo separado**, não no ZIP de depósito acadêmico.
   (Detalhe completo em `docs/MIGRATION_v2_TO_v3.md` e
   subsequentes notas de release.)

**Justificativa de IP** (motivação primária da Decisão):
o depósito Zenodo serve para **timestamping autoral imutável** —
DOI emitido pelo Zenodo + SHA-256 do ZIP + carimbo de data.
Cumpre a função de *proof-of-anteriority*. PDF é o formato
universalmente aceito por revisores e catálogos como evidência
de autoria; HTML não tem essa convenção (cada Zenodo
landing-page renderiza HTML diferentemente). A escolha
operacional é gerar primeiro o que protege a IP, depois o que
diverge para divulgação.

**Migração**: Fixes 6 e 7 (BibTeX como first-class + pipeline
de compilação PDF/DOCX) fornecem o código que torna esta
Decisão executável. Até Fix 6 lançar, `manuscript.tex`
continua emitindo `\thebibliography` inline (compila pra PDF
mas não gera `.bib` separado).


---

## Subsequent Decisões registered outside the main 'Decisões editoriais' section

Decisão 37 was registered alongside the html-wiki subcommand documentation.
Decisões 38, 39, 41 were registered alongside the mandatory gates they introduced.
Decisão 40 has no dedicated section — it was introduced as a mandatory directive only (Fix 12, v2.23.1) instructing Claude to load `assets/templates/persona-voice.xml` before generating `content.json` in Phase 7.

### Decisão 37 — HTML Wiki-style segregado em subcomando dedicado (registrado em v3.0.0-rc1)

Após o incidente RS-42 (dogfood falhou com "Esta conversa não pode ser compactada ainda mais" antes de qualquer artefato ser gravado), ficou claro que o pipeline padrão **não pode** assumir geração de HTML como passo obrigatório. O HTML é pesado (200-260 KB de tokens), depende de chunked-render (Decisão 18) e não é o artefato acadêmico — é divulgação. Mistura-lo no fluxo canônico fazia o pipeline falhar antes de produzir o PDF acadêmico, que é o que de fato precisa ser depositado no Zenodo.

**Regra:** o pipeline default da skill produz `manuscript.tex` + `bibliography.bib` → PDF (canônico) + DOCX (secundário). HTML Wiki-style **só é gerado** quando o usuário invoca `ignorantia render --format html-wiki` separadamente, **após** o pipeline canônico ter terminado com sucesso. Implicações:

1. Quando o subcomando `html-wiki` é invocado, o protocolo de chunked-render (Decisão 18, refinado pela Decisão 34 a ser mesclada da Fix 1) é obrigatório.
2. Falha na renderização HTML **não invalida** o pacote acadêmico (PDF + DOCX já estão em disco).
3. O HTML gerado **não vai** para Zenodo — o pacote depositado contém apenas o PDF, DOCX, telemetria, declarações éticas e dados de reprodutibilidade.
4. O HTML é distribuído separadamente (site institucional, blog, redes acadêmicas) como divulgação didática.

Esta decisão fecha o laço aberto pela Decisão 36 (Fix 5 — HTML reclassificado como secundário) ao explicitar **onde no fluxo** o HTML é gerado: nunca dentro do pipeline canônico, sempre como subcomando opt-in posterior. Decisão 18 (chunks) e Decisão 34 (chunked-write) permanecem aplicáveis mas escopadas ao subcomando.

### Decisão 38 — Avaliador automático é gate vinculante para empacotamento Zenodo (registrado em v2.23.1, Fix 9 do RS-42 remediation)

O dogfood RS-42 v1.0.0 (2026-05-08) foi empacotado e entregue mesmo após `scripts/generate_assessment.py` reportar **4.0/10.0** com **três eliminatórios** (cobertura insuficiente, declaração de IA ausente, IA possivelmente listada como autora). O assessor sempre saía com exit code 0; nada programático impedia o empacotamento de um artefato que o próprio sistema marcou como `"INACEITÁVEL para submissão"`. Resultado: usuário recebeu pacote ruim e teve que rejeitar manualmente.

**Regra (vinculante a partir de v2.23.1):** o avaliador é um **gate**. Comportamento padrão:

1. Exit code **2** quando há **qualquer** eliminatório, OU quando a nota final < `--gate-min-score` (default `7.0`).
2. Sidecar `<package_dir>/assessment_gate.json` sempre escrito, com `{passed, score, min_score, eliminatory_count, eliminatory_failed, score_failed, report_path, version}` para consumo programático por wrappers.
3. Relatório markdown em `--out` continua sendo escrito mesmo em falha — o gate não suprime a saída humana.
4. Flag `--no-gate` existe **apenas** para triagem em sessão de debug; nunca em fluxo de produção. Wrappers que invoquem `--no-gate` em produção devem ser tratados como bug.

**Implicações operacionais:**

- Toda chamada do avaliador na Fase 8 deve ser encadeada via shell short-circuit:
  ```bash
  python3 scripts/generate_assessment.py ... && \
      python3 scripts/zenodo/build_package.py ...
  ```
  O `&&` honra o exit code 2 e impede a montagem do ZIP quando o gate falha.
- O Claude, em sessão de chat, deve ler `assessment_gate.json` antes de declarar a entrega como concluída. Se `passed: false`, a próxima ação obrigatória é endereçar os itens da seção "Crítico" do `avaliacao_v<X.Y.Z>.md`, **não** empacotar.
- Pacote Zenodo com nota baixa só é admissível como artefato de **versão preview/draft** (ex.: `v0.x.y` ou tag `-rc`), nunca como release final.

**Verificação mecânica:** suite em `tests/integration/test_v2231_assessment_gate.py` cobre exit-code 2 em falha por eliminatório, exit-code 2 em falha por score, escrita do sidecar JSON em ambos os casos, escrita do relatório markdown mesmo em falha, e bypass via `--no-gate`. Releases futuras devem manter o gate como invariante de design — relaxar `--gate-min-score` é decisão consciente do operador, não um default.

Esta decisão **complementa** a Decisão 8 (mitigações Categoria A obrigatórias) e a Decisão 19 (anti-vazamento de meta-discurso) ao adicionar o último elo da cadeia: depois de gerar o relatório de qualidade, **respeitar** o relatório.

### Decisão 39 — Invariantes de pipeline são gate vinculante para empacotamento (registrado em v2.23.1, Fix 11 do RS-42 remediation)

O dogfood RS-42 v1.0.0 (2026-05-08) declarou em `searches.json.metadata.execution_method` o valor `single_session_ad_hoc_web_search` — Claude executou 5 queries via Google SERP em sessão de chat em vez de invocar o `search_orchestrator.py` com as 14+ bases Tier 1+Tier 2 que a SKILL.md prescreve. O pacote foi finalizado mesmo assim porque nada programático bloqueou.

**Regra (vinculante a partir de v2.23.1):** três invariantes mecânicos são verificados antes do empacotamento Zenodo via `scripts/check_pipeline_invariants.py`:

- **I1 — método de execução não-ad-hoc.** `searches.json.metadata.execution_method` não pode ser `single_session_ad_hoc_web_search` em fluxo de produção. Operador pode passar `--accept-ad-hoc-search` para aceitar conscientemente uma cobertura parcial (preview/draft), mas isso é decisão deliberada e nunca o default.
- **I2 — cobertura mínima de bases.** ≥3 bases distintas em `metadata.tier1_databases_actually_queried` (ou layout legado `per_database`). PRISMA-2020 espera múltiplas bases; pipelines com 0–2 violam o protocolo.
- **I3 — sem steps em ERROR.** Quando `pipeline_summary.json` existe, nenhum step pode ter `status: ERROR`. Steps com falha devem ser resolvidos antes do empacotamento.

Exit code do verificador:

| Código | Significado |
|---|---|
| 0 | Todos os invariantes passam — pacote pode ser empacotado |
| 1 | Input ausente ou inválido (`searches.json` faltando ou JSON quebrado) |
| 2 | Pelo menos um invariante falhou |

Comportamento: deve ser encadeado via `&&` antes do ZIP, igual à Decisão 38 (assessor gate) e à expansão da Decisão 19 (vocabulário). A combinação dos três gates fecha o caminho que permitiu RS-42 v1.0.0 ser entregue como pacote final.

**Verificação mecânica:** suite em `tests/integration/test_v2231_pipeline_invariants.py` (17 casos) cobre cada invariante isoladamente, o bypass via flag explícita, layouts v3 e v2 do `searches.json`, e regressão direta com payload extraído do RS-42 v1.0.0.

### Decisão 41 — Política de vocabulário de artefatos como gate vinculante deposit-wide (registrado em v2.23.3, Fix 19 do RS-42 remediation)

O dogfood RS-42 Mark 4 (v2.23.2, 2026-05-09) revelou que o gate da Decisão 19 expandido na v2.23.1 (Fix 10) era insuficiente em duas dimensões:

1. **Escopo errado.** O gate só corria contra `manuscript.tex`. O pior vazamento da Mark 4 estava em `protocol-v1.0.0.md` (que ia pro pacote Zenodo) — `vide Decisão 27 v2.9.0 da skill`, `Cascata Tier 0 (Decisão 24)`, `DD-6:`, `design_foundational`. O protocolo é depósito público; deveria ter sido inspecionado.
2. **Padrões insuficientes.** A v2.23.1 vettava SemVer, `Decisão N`, `Categoria A/B`, JSON-field-names. Não cobria `Tier N`, `FALLBACK_MD`, `KEY → PROXY`, `DD-N`, valores enum de `review_purpose` (`design_foundational`), nem o meta-projeto bleed-through (`projeto subjacente`, `outras 41 revisões`, `função declaratória/instrumental`) — que dominaram a Mark 4 com 92 violações em 4 arquivos.

A causa estrutural mais profunda: a SKILL.md instruía Claude a popular `review_type` e `review_purpose` com valores literais de enum (`scoping_review`, `design_foundational`), e Claude tratava esses literais como "vocabulário correto" — vazando-os para a prosa do paper. Não havia distinção explícita entre **payload de metadado** (onde o enum é obrigatório) e **voz da prosa** (onde a enum literal é violação).

**Regra (vinculante a partir de v2.23.3):**

1. **Política de tradução.** O arquivo `references/artifact-vocabulary-policy.xml` é vinculante. Mapeia 6 classes de label operacional para suas traduções científicas obrigatórias. Claude lê a política ANTES de gravar QUALQUER prosa em disco que ficará no pacote Zenodo. Em particular: enum-values de `review_type`/`review_purpose` ficam apenas no metadado JSON; em prosa traduz-se com a tabela.

2. **Gate deposit-wide.** `scripts/check_decision_19_vocabulary.py --all <output_dir> --gate-sidecar` varre todos os `.md`/`.tex`/`.html` do depósito (CSV/JSON/SVG/PDF/ZIP são pulados — são dados, não prosa). Falha (exit 2) se qualquer arquivo tiver violação de qualquer um dos 12 padrões. Sidecar `vocabulary_gate.json` registra `passed/total_violations/files_with_violations/violations_by_label`.

3. **Encadeamento.** Encadear via `&&` antes do ZIP, junto com os gates da Decisão 38 (assessor) e Decisão 39 (invariantes). Os três gates juntos fecham o caminho que permitiu RS-42 Mark 4 ser entregue como pacote final apesar da mistura instrução-conteúdo.

**Verificação mecânica:** 21 testes novos em `tests/integration/test_v2233_fix19_vocabulary_expansion.py` cobrem cada padrão novo, o walk recursivo do depósito, o sidecar JSON, o opt-out `--no-gate` para triagem, e regressão direta com frases extraídas literalmente de `RS-42_protocol-v1.0.0.md` e `RS-42_manuscript-v1.0.0.tex` da Mark 4. Smoke-run da Mark 4 contra o gate deposit-wide: 92 violações em 4 arquivos — exatamente o vazamento diagnosticado pelo usuário.

**Para quem mantém esta skill:** os padrões em `_FORBIDDEN` (em `scripts/check_decision_19_vocabulary.py`) e a tabela de tradução em `references/artifact-vocabulary-policy.xml` são fontes pareadas de verdade. Adicionar um novo padrão sem atualizar a tabela é regressão estrutural — Claude não saberá traduzir, vai escrever vocabulário-fantasma e o gate vai falhar sem direção construtiva.
