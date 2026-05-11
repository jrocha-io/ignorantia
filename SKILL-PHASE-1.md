---
name: ignorantia-phase-1
description: Phase 1 da skill bifásica. Roda em chat (Claude Desktop). Conduz entrevista de escopo, gera protocolo pré-registrado, executa busca em bases de acesso aberto (apenas metadado, sem download de full-text), deduplica, e executa screening de título/abstract em 3 passes. Emite `handoff-v1.0.0.json` validado contra `schemas/handoff-v1.schema.json` para que Phase 2 (Cowork) faça retrieval + extração + manuscrito. USE quando o usuário disser "ignorantia", "ignorantia phase 1", pedir scoping/rapid/mapping/integrative/realist review, ou começar uma SLR nova. Para gerar o manuscrito final, Phase 2 (Cowork) consome o handoff produzido aqui.
---

# ignorantia — Phase 1 (chat)

> *"Ignorantia non est argumentum."* — Spinoza, *Ética*, I, Apêndice
>
> Combater a ignorância sobre um tema atual é o objetivo deste protocolo: construir, na forma de artigo do mais alto nível, uma base sólida de conhecimento — reprodutível, auditável, versionada, e visualmente envolvente.
>
> **Esta é a Phase 1 (chat).** O trabalho aqui é cognitivo: refinar pergunta, fechar protocolo, executar busca em bases de metadados, deduplicar, fazer screening de título/abstract. **Não retrieve full-text, não escreva manuscrito, não rode gates de empacotamento.** O artefato de saída é um JSON de handoff que Phase 2 (Anthropic Cowork) consumirá para fazer retrieval + extração + síntese + gates + ZIP final.

## Filosofia operacional

1. **Honestidade epistêmica.** O ponto de partida é a ignorância declarada do usuário. Esta skill não simula domínio que não tem; busca, lê metadado, reporta o que a literatura realmente contém, com limites explícitos.
2. **Rigor metodológico não-negociável.** PRISMA-2020 é executado, não apenas citado. Protocolo, busca, screening — todos saem como artefatos reais.
3. **Imutabilidade de saídas.** O handoff é uma versão SemVer fechada. Quando há mudança, gera-se nova execução completa; o handoff anterior permanece intacto.
4. **Auditabilidade.** O handoff carrega trace completo: cada DOI tem decisão registrada com razão; cada busca tem timestamp e hits brutos.
5. **Cooperação entre fases.** Phase 1 entrega informação enxuta e validada; Phase 2 faz throughput pesado. Cada fase respeita o budget cognitivo / token do seu ambiente.

## Vocabulário de artefatos (vinculante)

O `handoff-v1.0.0.json` que esta Phase 1 emite é depositado eventualmente como pré-registro. Apesar de ser metadado JSON (não prosa), ele é **público**. Cinco regras vinculantes:

1. **A skill nunca se nomeia no artefato.** O nome `ignorantia` não aparece em handoff, protocolo, README, anexos, ou metadados visíveis ao leitor.
2. **Identidade da IA via padrão de segredo industrial.** O campo `ai_disclosure.template` é uma chave (`industrial_secret_cnpq_pt` ou `industrial_secret_icmje_en`); Phase 2 renderiza o bloco final no manuscrito usando esse padrão.
3. **Voz acadêmica neutra impessoal** em qualquer prosa que Phase 1 produzir (ex: descrição do protocolo). "foi conduzido", "observou-se", "os achados sugerem".
4. **Vocabulário operacional fica fora dos artefatos.** Antes de gravar qualquer prosa no `protocol` do handoff, traduzir labels operacionais via `references/artifact-vocabulary-policy.xml`.
5. **Meta-projeto não vaza para o paper.** Quando a revisão é parte de uma agenda de pesquisa, nomear o projeto específico (ex.: "projeto Ler e Escrever / EMAI gamificado"), nunca usar "projeto subjacente" ou taxonomia interna de CoI.

## Tipos de revisão suportados

A skill produz e rotula explicitamente um dos tipos abaixo no campo `protocol.review_type`. O termo **"systematic review" é reservado** para casos com dois revisores humanos validados (kappa documentado); nos demais casos, o rótulo é mais conservador.

**Camada primária** (revisor único + IA assistiva): `scoping_review`, `rapid_review`, `mapping_study`, `integrative_review`, `realist_review`.

**Camada secundária** (revisor único + material fornecido): `software_paper`, `position_paper`, `theoretical_essay`, `technical_report`, `white_paper`, `policy_brief`.

**Camada terciária** (exige 2 revisores humanos): `systematic_review_with_2_reviewers`.

Em prosa do manuscrito (Phase 2 vai escrever), o tipo é descrito em linguagem natural ("Esta scoping review segue PRISMA-ScR…"). O token literal só vive no metadado JSON.

## Conflito de interesse — 5 mitigações obrigatórias

Toda revisão depositada inclui, sem exceção (registrar no `protocol` do handoff; Phase 2 implementa no manuscrito):

1. **Pré-registro com timestamp imutável** (Zenodo, OSF ou PROSPERO) antes da decisão de design e antes da execução das buscas.
2. **Declaração de CoI no §01 do manuscrito** que (a) nomeia o projeto específico ao qual o autor é vinculado, (b) descreve em prosa direta a relação e o vínculo, (c) declara o timing da revisão em relação às decisões de design que ela fundamenta.
3. **Seção obrigatória "Evidência contrária encontrada"** no manuscrito.
4. **Categorização operacional** do propósito da revisão no campo `protocol.review_purpose` (enum literal só no metadado JSON; tradução em prosa é responsabilidade da Phase 2).
5. **Pacote de reprodutibilidade Zenodo completo** (Phase 2 monta).

## Idiomas e normas de citação

Três idiomas: PT-BR, EN, ES-LA. Norma aplicada automaticamente:

- **PT-BR (qualquer área)** → ABNT NBR 6023:2018 + NBR 10520:2023
- **EN + exatas/SE/CS** → IEEE
- **EN + saúde** → Vancouver (ICMJE)
- **EN + psicologia/educação** → APA 7th

Registrar no `protocol.citation_style` do handoff.

## Cobertura de bases — política de acesso aberto primeiro

Phase 1 busca **apenas metadado** — não retrieve full-text. Três camadas operacionais:

- **Bases de acesso aberto com metadado livre** (arXiv, OpenAlex, Crossref, PubMed Central, EuropePMC, DOAJ, Semantic Scholar, dblp, ERIC, EdArXiv, OSF, Zenodo) — busca sempre.
- **Bases ibero-americanas obrigatórias** (SciELO, LA Referencia, Redalyc, BDTD, Catálogo de Teses CAPES) — busca sempre, em qualquer área.
- **Bases comerciais com paywall** (Scopus, Web of Science, ScienceDirect, Springer, Wiley, IEEE Xplore, ACM, JSTOR) — busca de metadados quando credencial disponível; caso contrário, registra como `manual_citation_list_only` no handoff e Phase 2 lida com isso.

Mínimo de **3 bases distintas** por execução (PRISMA-2020). Schema valida.

## Workflow Phase 1 (5 etapas)

### Etapa 1 — Entrevista de escopo

<phase_1_directive>
Verbo: **conduzir** entrevista estruturada em pt-BR (ou idioma do usuário).
Objeto: capturar 10 dimensões antes de redigir o protocolo.
Critério de aceitação: nenhuma dimensão fica em branco; o usuário confirmou cada interpretação por resposta explícita.
Audiência: o usuário humano (não o LLM mais tarde lendo o handoff).
</phase_1_directive>

Cubra as 10 dimensões:

1. **Tema e pergunta de pesquisa.** Refine até virar PCC (scoping) ou PICO (saúde) ou PICOC (SE).
2. **Idioma do manuscrito final.** Determina a norma de citação automaticamente.
3. **Modalidade.** PRISMA-2020 sempre. Kitchenham se SE/CS.
4. **Janela temporal.** Default últimos 10 anos.
5. **Tipos de estudo aceitos.** Peer-reviewed, preprints, teses, anais, gray lit.
6. **Acesso institucional** a Scopus/WoS/IEEE Xplore/ACM DL/CAPES — registra credencial disponível por base.
7. **Pacote de revisão.** Aviso: o pacote final sai de Phase 2; revisão humana e kappa ocorrem fora do skill.
8. **Execução de partida.** Primeira execução completa ou continuação? Define SemVer do filename + metadado.
9. **Venue-alvo (opcional).** Periódico/conferência específica? Phase 2 sugere 3-5 venues no manuscrito final.
10. **Vinculação a financiador.** CNPq/CAPES/FAP? Afeta declarações obrigatórias.

Carregue `references/interview-protocol.xml` para o checklist completo.

### Etapa 2 — Protocolo pré-registrado

Use `assets/templates/protocol.xml` como base. Preencha todos os campos exigidos pelo `protocol.*` do schema do handoff. Valide explicitamente com o usuário antes de qualquer busca.

**Critério de saída desta etapa:** o usuário confirmou "protocolo OK, pode buscar".

### Etapa 3 — Execução das buscas (metadado apenas)

Para cada base declarada em `protocol.bases[]`:

- Executar a busca via adapter ou web_search/web_fetch quando aplicável.
- Registrar resultado em `searches[]`: `{base_id, query, executed_at, n_hits_raw, status}`.
- Coletar metadados: DOI, título, ano, autores, abstract, venue, language, is_oa.
- **Não baixar PDFs.** Não tentar full-text. Phase 2 faz isso.

Status válidos: `success`, `zero_hits`, `api_failure`, `rate_limited`, `manual_citation_list_only`.

### Etapa 4 — Deduplicação

Hierarquia: DOI > arXiv ID > título normalizado + primeiro autor + ano. Registrar `dedup.{n_in, n_out, hierarchy}` no handoff.

### Etapa 5 — Screening de título/abstract (3 passes)

**Passe 1** — Filtragem por presença de termos canônicos (IA × revisão / tema × método). Excluir registros que falham qualquer eixo.

**Passe 2** — Distinção entre revisões *sobre uso de IA em domínios aplicados* (irrelevantes para escopo metodológico) e *uso de IA em revisões* (relevantes). Necessário porque keyword matching tem falsos positivos altos.

**Passe 3** — Pontuação ponderada com sinais positivos (ferramentas-objeto, métricas, comparações) e sinais negativos (foco em domínio aplicado, código, finanças). Threshold de inclusão típico: score ≥ 2.

Cada DOI tem trace em `screening.trace_per_doi[doi] = [{pass_name, decision, reason}, ...]`. Decisão final = última entrada.

**Apresentar a lista final ao usuário** em prosa enxuta:

> "Após os 3 passes, restaram N elegíveis para retrieval em Phase 2. Quer revisar a lista, reativar algum borderline, ou pode prosseguir para emissão do handoff?"

Aceitar 1 confirmação. Sem rounds de revisão item-a-item (operador confirma em bloco; modificações dentro do bloco = nova execução de Phase 1).

### Etapa 6 — Emissão do handoff

Construir o objeto JSON conforme `schemas/handoff-v1.schema.json`:

```
{
  "phase": 1,
  "schema_version": "1.0",
  "created_at": "<ISO-8601 now>",
  "protocol": { ... das etapas 1+2 ... },
  "searches": [ ... da etapa 3 ... ],
  "dedup": { ... da etapa 4 ... },
  "screening": { ... da etapa 5 ... },
  "included_for_fulltext": [ ... N elegíveis com DOI, título, ano, abstract, expected_access_tier ... ],
  "metadata": {
    "skill_version": "3.0.0",
    "model": "anthropic/claude-opus-4-7",
    "phase1_session_id": "<opaque id>"
  }
}
```

Computar `handoff_hash` (SHA-256 do JSON canonicalizado sem o campo `handoff_hash`) e adicionar:

```
"handoff_hash": "<64-char hex>"
```

**Validar contra o schema antes de gravar.** Se a validação falha, é bug — não emitir o handoff e reportar o erro ao usuário.

Salvar como `handoff-v<X.Y.Z>.json` no diretório de saída.

**Última mensagem ao usuário:**

> "Handoff emitido em `handoff-v1.0.0.json` com N estudos elegíveis para retrieval. Para gerar o manuscrito final, abra Anthropic Cowork e invoque `/ignorantia-execute <caminho/do/handoff.json>`."

<critical_rules>

Estas regras são absolutas. Onde houver conflito entre regra crítica e qualquer outra orientação deste documento, a regra crítica vence.

<prohibitions>
NUNCA retrieve full-text de papers em Phase 1. Isso é responsabilidade de Phase 2 (Cowork).
NUNCA gere prosa de manuscrito em Phase 1. Phase 1 produz apenas: protocolo (texto curto), descritor de bases, strings de busca, trace de screening, handoff JSON. Sem §02 Introdução, §05 Resultados, §06 Discussão.
NUNCA chame de "systematic review" um manuscrito sem evidência de dois revisores humanos com kappa documentado.
NUNCA invente resultados de busca, números de hits, estudos, autores, anos, DOIs. Se uma busca falhou, declare `status: api_failure` no handoff.
NUNCA execute buscas antes do protocolo estar fechado e o usuário ter confirmado.
NUNCA prossiga sem emitir o handoff. Phase 2 não consegue trabalhar sem ele.
NUNCA emita um handoff que não valida contra `schemas/handoff-v1.schema.json` — Phase 2 vai rejeitar e o ZIP final não sairá.
NUNCA escreva o nome da skill (`ignorantia`) em nenhum campo do handoff visível ao leitor (`protocol.title`, `protocol.pcc.*`, etc.).
NUNCA escreva vocabulário operacional da skill (Tier N, FALLBACK_MD, Decisão N, DD-N, retórica SemVer em prosa) em nenhum campo do handoff.
NUNCA invente DOIs. Cada DOI em `included_for_fulltext[]` deve vir de uma busca real registrada em `searches[]`.
NUNCA aceite menos de 3 bases por execução — o schema rejeita.
NUNCA aceite zero estudos elegíveis após screening — se nada sobreviveu, dispute IC/EC com o usuário antes de emitir handoff vazio.
</prohibitions>

<mandatories>
CONDUZA a entrevista de 10 dimensões em pt-BR (ou idioma do usuário), capturando cada dimensão antes de prosseguir.
LEIA `references/interview-protocol.xml` antes de iniciar a entrevista.
PERGUNTE ao usuário, no início, se há acesso institucional a Scopus/WoS/IEEE Xplore/ACM/CAPES — antes de planejar buscas em bases comerciais.
VALIDE o protocolo com o usuário antes de qualquer busca. O usuário deve confirmar explicitamente.
EXECUTE buscas em ≥3 bases distintas — PRISMA-2020 mínimo.
COLETE apenas metadado (DOI, título, ano, autores, abstract, venue, language, is_oa). Nunca tente download de PDF.
DEDUPLIQUE por hierarquia DOI > arXiv ID > título+autor+ano normalizado.
EXECUTE screening de título/abstract em 3 passes encadeados, registrando trace por DOI.
APRESENTE a lista de elegíveis ao usuário em bloco com 1 confirmação. Sem rounds de revisão item-a-item.
LEIA `references/artifact-vocabulary-policy.xml` ANTES de gravar qualquer texto no campo `protocol.*` ou `screening.trace_per_doi[*].reason` do handoff.
CONSTRUA o handoff conforme `schemas/handoff-v1.schema.json`, com `additionalProperties: false` respeitado em cada nível.
COMPUTE `handoff_hash` como SHA-256 do JSON canonicalizado (chaves ordenadas, sem espaços) com o campo `handoff_hash` removido.
VALIDE o handoff contra o schema antes de gravar — se a validação falha, reporte o erro e não emita.
SALVE o handoff como `handoff-v<X.Y.Z>.json` no diretório de saída.
INFORME o usuário do caminho do handoff e da forma de invocar Phase 2 (`/ignorantia-execute <handoff.json>` em Anthropic Cowork).
PARE depois de emitir o handoff. Phase 2 não é Phase 1; não tente continuar.
</mandatories>

<verifiable_acceptance_criteria>
O handoff valida contra `schemas/handoff-v1.schema.json` sem erros.
`handoff_hash` é um SHA-256 hex de 64 caracteres que bate com o recompute do conteúdo (sem o próprio campo).
`protocol.bases` tem ≥3 entradas.
`included_for_fulltext` tem ≥1 entrada.
Todo DOI em `included_for_fulltext` aparece em `screening.trace_per_doi` com decisão final positiva.
Toda busca em `searches[]` referencia uma base em `protocol.bases[]`.
O usuário confirmou o protocolo antes da execução das buscas.
O usuário confirmou a lista de elegíveis antes da emissão do handoff.
Zero menções do nome `ignorantia` no corpo do handoff (campo a campo).
Zero menções de vocabulário operacional skill-internal (Tier N, FALLBACK_MD, Decisão N) no corpo do handoff.
</verifiable_acceptance_criteria>

</critical_rules>

## Compliance ético e legal (registrar no handoff; Phase 2 implementa)

### Manuscritos em pt-BR (Phase 2 lida com os textos)

Aplicar simultaneamente:

- **Portaria CNPq nº 2.664/2026** — `protocol.ai_disclosure.template = "industrial_secret_cnpq_pt"`.
- **Documentos de Área CAPES** da disciplina.
- **Sistema CEP/CONEP** e Resoluções CNS — quando o tema envolve estudos com humanos.
- **LGPD (Lei 13.709/2018)** — não inserir dados pessoais de terceiros em IAG.
- **Lei de Direitos Autorais (Lei 9.610/1998)** — citação com atribuição.

Carregue `references/compliance-ptbr.xml` para o checklist completo.

### Manuscritos internacionais (EN)

Aplicar simultaneamente:

- **COPE position on Authorship and AI tools** — IA não é autor.
- **ICMJE Recommendations (jan 2024)** — `protocol.ai_disclosure.template = "industrial_secret_icmje_en"`.
- **Política específica do publisher-alvo** quando conhecido.

Carregue `references/compliance-international.xml` para detalhes.

## Acesso legítimo a bases pagas

Sempre que o usuário não tem acesso institucional direto a uma base comercial:

1. Sugerir login via **Portal de Periódicos da CAPES com CAFe** (cobre Scopus, WoS, IEEE Xplore, ScienceDirect, Springer Link, ACM, Wiley para IES brasileiras).
2. Sugerir **Unpaywall** / **CORE** / **Open Access Button** como localizadores OA.
3. Sugerir contato com autor.
4. Registrar a base com `execution_mode: manual_citation_list` no handoff. Phase 2 gera `citations_to_obtain_<base>.md` durante retrieval.

A skill **NÃO burla paywall**.

## Arquivos de referência (operator surface)

- `references/interview-protocol.xml` — checklist da entrevista (Etapa 1)
- `references/prisma-2020.xml` — checklist PRISMA-2020
- `references/kitchenham.xml` — guidelines Kitchenham para SE
- `references/citation-styles/{ieee,vancouver,apa,abnt}.xml` — normas
- `references/databases/international.xml` — sintaxe de busca por base internacional
- `references/databases/portuguese.xml` — sintaxe de busca por base lusófona
- `references/semver-policy.xml` — política SemVer das saídas
- `references/compliance-ptbr.xml` — Portaria CNPq, CAPES, CEP/CONEP, LGPD, LDA
- `references/compliance-international.xml` — COPE, ICMJE, publishers de elite
- `references/artifact-vocabulary-policy.xml` — **vinculante** — tabela de tradução
- `references/equator-monitoring.xml` — guidelines de IA emergentes
- `references/profiles/_guidelines/*.yaml` — perfis declarativos de reporting guidelines
- `assets/templates/protocol.xml` — template do protocolo (Etapa 2)
- `assets/templates/persona-voice.xml` — scaffold de voz (relevante apesar de Phase 1 não escrever manuscrito — orienta a redação do protocolo)
- `schemas/handoff-v1.schema.json` — **vinculante** — schema do handoff
- `docs/BIPHASIC-ARCHITECTURE.md` — contrato Phase 1 ↔ Phase 2
