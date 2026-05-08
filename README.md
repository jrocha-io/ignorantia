# ignorantia

> Construção de revisões sistemáticas de literatura (SLR) PRISMA-2020 do mais alto nível, com saída em HTML interativo auto-contido, versionada e auditável.

**Versão:** 2.23.0 (estável) + v3.0.0-alpha (Clean Architecture em integração — domain/application/infrastructure/interface bounded contexts, Click CLI, JSON-schema validados em runtime).

**Estado quantitativo (v2):** 62 adapters de busca · 57 TIER1_RUNNERS · 7 áreas · 16 paywall com cascata legal · 6 etapas no `pipeline_finalize` · 13 DDs · 33 decisões editoriais.
**Estado quantitativo (v3):** 4 bounded contexts · 4 use cases · 4 subcomandos CLI · 4 JSON-schemas · 2127+ testes verde.

➡️ Migrando da v2? Comece por **[`docs/MIGRATION_v2_TO_v3.md`](docs/MIGRATION_v2_TO_v3.md)**.

## O que é

`ignorantia` é uma skill executada pelo Claude (Anthropic) que conduz uma SLR completa, do protocolo pré-registrado ao manuscrito final. O ponto de partida é a **ignorância declarada do usuário** sobre um tema — o resultado é um artigo do mais alto nível, reprodutível e auditável.

Diferenciais:

- **PRISMA-2020 executado, não citado.** Flow diagram com números reais, quality appraisal CASP/DARE para cada estudo, extração tabulada — todos artefatos saem do pipeline.
- **HTML interativo auto-contido.** Saída primária com gráficos D3.js, tabelas filtráveis, anotações estilo professor, dark mode, e referências clicáveis.
- **Cobertura premium via cascata legal (v2.15.0).** 16 adapters paywall (Scopus, WoS, ScienceDirect, Embase, Springer, Wiley TDM, IEEE Xplore, APA PsycInfo, EBSCO CINAHL, JSTOR, Sage, ACM, SSRN, Hein Online, ProQuest, Google Scholar via SerpApi) com cascata `KEY → PROXY → FALLBACK_MD → MOCK`. Sem credencial, gera `citations_to_obtain_<base>.md` com 4 opções de obtenção (CAPES, biblioteca, autor, COMUT).
- **Logs em duas camadas (v2.17.0).** Camada 1 (adapter): `fetched`/`kept_after_local_filter`/`discarded_local` em JSON Lines automático. Camada 2 (screening): 3 estágios PRISMA-2020 (`title`/`abstract`/`full_text`) com CSV auditável reviewer-by-reviewer.
- **Preâmbulo contextual Wikipedia/Wikidata (v2.18.0).** Seção "O campo onde este artigo vive" distinta da Introdução, para audiência leiga (banca multidisciplinar, white paper). Citações ABNT NBR 10520 com data de acesso.
- **Sprint Badge calibrado empiricamente** em 187 SLRs reais (Plataforma Sucupira CAPES Qualis 2021-2024). Classifica o pacote em A1/A2/A3/B1 ou SUB-B1, com precision Q1 = 97.6% no modo pacote mínimo.
- **SemVer imutável.** Cada saída é uma versão fechada. Versões antigas permanecem como registro histórico.
- **Compliance acadêmica completa.** Portaria CNPq 2.664/2026, COPE, ICMJE, LGPD, CEP/CONEP, declarações obrigatórias de uso de IA.

## Quickstart (v3 CLI — recomendado)

Instalação e primeiro uso em <5 minutos:

```bash
# 1. Instalar (com extras opcionais — [docx] ativa exportação .docx)
pip install -e '.[dev,docx]'

# 2. Verificar instalação
ignorantia --version
ignorantia --help

# 3. Renderizar um manuscrito JSON em HTML (escolha citation-style)
ignorantia render \
    --input meu-manuscrito.json \
    --output meu-manuscrito.html \
    --format html \
    --citation-style abnt
# → {"output_format": "html", "byte_size": 12345, "output_path": "meu-manuscrito.html"}

# 4. Buscar literatura em múltiplos adapters (with year window)
ignorantia search \
    --text "evidence synthesis methodology" \
    --source openalex --source crossref --source arxiv \
    --year-start 2020 --year-end 2025 \
    --output resultados.json

# 5. Registrar uma entrada no manifest de reprodutibilidade
ignorantia audit \
    --action search.run \
    --actor cli \
    --payload '{"n_results": 87}'
```

Cada subcomando emite uma linha JSON validada contra um schema em
`src/ignorantia/interface/manifests/`. Detalhes do shape de
`--input` para `render`, opções avançadas e API programática em
[`docs/MIGRATION_v2_TO_v3.md`](docs/MIGRATION_v2_TO_v3.md).

## Quickstart (v2 scripts — legacy)

Em 5 linhas, do tema à avaliação:

```bash
# 1. Construir o pacote (manualmente ou via Claude)
# 2. Avaliar
python3 scripts/assessor/main.py \
    --package-dir meu-pacote/ \
    --content meu-pacote/content.json \
    --extraction meu-pacote/extraction.csv \
    --qa meu-pacote/quality-appraisal.csv \
    --searches meu-pacote/searches.json \
    --html meu-pacote/manuscript.html \
    --version 1.0.0 --topic-slug meu-tema --area-slug edu \
    --lang pt-BR \
    --out avaliacao.json

# 3. Renderizar HTML final
python3 scripts/render_v2.py \
    --content meu-pacote/content.json \
    --assessment avaliacao.json \
    --extraction meu-pacote/extraction.csv \
    --qa meu-pacote/quality-appraisal.csv \
    --searches meu-pacote/searches.json \
    --prisma meu-pacote/prisma-flow.svg \
    --version 1.0.0 --topic-slug meu-tema \
    --out manuscript.html
```

O Sprint Badge aparece no HTML como pill colorida com tooltip detalhado.

## Fluxo de trabalho (8 fases)

1. **Entrevista de escopo** — captura tema, idioma, modalidade, janela temporal, tipos de estudo, acesso institucional, venue-alvo, vínculo a financiador.
2. **Protocolo pré-registrado** — `protocol-v<X.Y.Z>.md` validado pelo usuário antes de qualquer busca.
3. **Execução das buscas** — Crossref, OpenAlex, Europe PMC, Unpaywall (gratuitas) + Scopus/WoS/IEEE Xplore via proxy institucional legítimo.
4. **Deduplicação e screening** — DOI > arXiv ID > título+autor+ano. Decisões registradas.
5. **Quality appraisal** — CASP/DARE para todos. Kitchenham QA1-QA8 se SE/CS.
6. **Extração** — formulário pré-definido.
7. **Síntese e HTML interativo** — narrativa-temática por RQ, gráficos D3.js, anotações estilo professor.
8. **Avaliação automática + sugestão de venues + empacotamento** — `avaliacao_v<X.Y.Z>.md` + Sprint Badge + 3-5 venues sugeridos + ZIP final para Zenodo.

## Sprint Badge — calibração empírica

O Sprint Badge classifica o pacote em estratos Qualis brasileiros. **No escopo deste skill, apenas A1, A2, A3 e B1 são reconhecidos** — os estratos A4, B2, B3, B4 e C existem na Plataforma Sucupira mas estão fora da cobertura empírica do corpus de calibração.

Dois modos:

- **`texto_integral` (default):** 9 faixas finas (C, B4, B3, B2, B1, A4, A3, A2, A1), calibradas em 4 cenários canônicos. Validação empírica em FT real ainda pendente (planejada para Rodada S).
- **`pacote_mínimo` (auto-detect ou opt-in):** 3 faixas (SUB-Q4, Q2-Q3, Q1), calibradas empiricamente em 187 SLRs reais (Rodada N). Precision Q1 = 97.6%.

Detector heurístico v0 marca um pacote como mínimo quando ≥2 dos 4 sinais são detectados:
1. `ai_declaration` menciona Crossref/OpenAlex/metadata
2. `background_html` contém placeholder "não extraído" / "not extracted"
3. ≥70% das references sem DOI
4. `not_this_version_items` menciona metadata

Override via flag CLI: `--minimal-package=auto|yes|no`.

Documentação técnica completa em `references/whitepaper-sprint-badge-calibration.md`.

## Três exemplos de uso

### 1. Pipeline completo (do protocolo ao ZIP final)

Use o Claude com a skill ativa. Diga:

> "Quero fazer uma revisão sistemática sobre [tema]. PRISMA-2020, manuscrito em pt-BR, janela 2018-2026."

O Claude conduz a entrevista de escopo, gera o protocolo, executa as buscas, faz screening, quality appraisal, extração, síntese, e empacota tudo.

### 2. Apenas avaliação de um pacote já construído

Você tem um pacote SLR (próprio ou de terceiro) e quer avaliá-lo:

```bash
python3 scripts/assessor/main.py \
    --package-dir caminho/ \
    --content caminho/content.json \
    --extraction caminho/extraction.csv \
    --qa caminho/quality-appraisal.csv \
    --searches caminho/searches.json \
    --html caminho/manuscript.html \
    --version 1.0.0 --topic-slug topico --area-slug edu \
    --lang pt-BR \
    --out avaliacao.json
```

Saída: JSON com nota Conteúdo (0-10), letra Forma (A-E), Sprint Badge (faixa Qualis), eliminadores verificados, auditoria forense, e lista priorizada do que falta para nota 10.

### 3. Em lote (calibração ou benchmark)

Para rodar o pipeline em N pacotes (ex.: corpus de calibração):

```bash
python3 scripts/run_calibration_batch.py \
    --packages /tmp/calibration_packages \
    --workers 4 \
    --out /tmp/batch_results.json
```

(Disponível a partir da Rodada S2.)

## Estrutura do projeto

```
ignorantia/
├── SKILL.md                      # Entry point para o Claude
├── README.md                     # Este arquivo (para usuários humanos)
├── journal.txt                   # Log de desenvolvimento
├── scripts/
│   ├── assessor/                 # Pipeline de avaliação
│   │   ├── main.py               # Orquestração
│   │   ├── eliminators.py        # E1-E15
│   │   ├── rubric.py             # C1-C7 + F1-F7
│   │   ├── sprint_badge.py       # Calibração Qualis
│   │   ├── temperature.py        # T1-T4
│   │   ├── audit.py              # Forense A1-A7
│   │   ├── venues.py             # Verificação de venues
│   │   ├── plagiarism.py         # Plágio camada 1
│   │   └── visual_aids.py        # TLDR cards, grifos, marca-texto
│   ├── render_v2.py              # Geração do HTML interativo
│   ├── slr_to_package.py         # Conversor SLR → pacote (calibração)
│   ├── searches/                 # Ferramentas auxiliares de busca
│   │   ├── README.md
│   │   ├── search_arxiv.py
│   │   ├── search_crossref.py
│   │   ├── search_dblp.py
│   │   ├── search_scielo.py
│   │   └── search_semantic_scholar.py
│   ├── deduplicate.py
│   └── prisma_flow.py
├── assets/
│   └── templates/
│       ├── manuscript-template-v2.html
│       ├── protocol.md
│       ├── extraction-form.md
│       └── quality-appraisal.md
├── references/                   # Documentação operacional
│   ├── whitepaper-sprint-badge-calibration.md
│   ├── calibration-corpus.json
│   ├── venue-stratum-mapping.json
│   ├── calibrations/             # Histórico por versão
│   ├── archived/                 # Versões obsoletas mantidas
│   └── round-J-final-report.md, round-L, round-M, round-N
└── test-cases/                   # Fixtures de regressão
    ├── content_h.json
    ├── corpus_25.json
    └── calibration/
```

## Cenários canônicos de regressão

A pipeline tem 4 cenários de teste preservados em `test-cases/`:

| Cenário | Versão | Conteúdo | Forma | Sprint Badge esperado |
|---|---|---|---|---|
| smoke (pacote vazio) | 1.0.0 | 0.0 | E | 🚫 NÃO-CLASSIFICÁVEL |
| corpus 18+ realista | 1.0.0 | 7.2 | A | B1 |
| ghostwriter v0.1.0 | 0.1.0 | 3.7 | A | ⚠️ SUB-B4 |
| Caso H (letramento idosos) | 1.0.0 | 6.3 | D | B3 |

Validação automática via `python3 scripts/assessor/main.py --self-test` (a partir da Rodada Q5).

## Princípios

- **Honestidade epistêmica.** O skill não inventa dados. Se uma busca falhou, declara a falha.
- **Rigor metodológico.** PRISMA-2020 é executado, não citado.
- **Imutabilidade.** Cada versão SemVer é fechada. Não se edita versão publicada.
- **Auditabilidade.** Toda referência tem link clicável para fonte primária.
- **Engajamento do leitor.** Forma e fundo importam.

## Licença

CC-BY-4.0 (default; confirmado com usuário no Fase 1).

## Citação sugerida

Se você usar `ignorantia` em pesquisa publicada:

> Skill `ignorantia` v2.0.0-alpha25 (2026). Anthropic Claude. Sprint formal de calibração empírica realizado em 187 SLRs reais. Whitepaper técnico em `references/whitepaper-sprint-badge-calibration.md`.

## Histórico de versões

Cada versão tem um relatório dedicado em `references/round-X-final-report.md`. O sprint formal completo (Rodadas J a P) está documentado no whitepaper. Veja `journal.txt` para o log cronológico de desenvolvimento.

## Suporte e contribuição

Este projeto é uma skill desenvolvida em colaboração entre o usuário e o Claude (Anthropic). Para questões metodológicas, consulte primeiro:

- `SKILL.md` — fonte da verdade para o comportamento do skill
- `references/whitepaper-sprint-badge-calibration.md` — método de calibração
- `references/round-*-final-report.md` — relatórios das rodadas

Para problemas técnicos no pipeline, verifique:

- `journal.txt` — log de mudanças
- `tests/test_regression.py` — testes de regressão (a partir da Rodada Q5)
