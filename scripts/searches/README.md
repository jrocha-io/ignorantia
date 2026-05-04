# scripts/searches/ — Ferramentas auxiliares de busca

> Coleção de scripts CLI para o pesquisador construir o pacote inicial de uma SLR antes de invocar o pipeline `assessor`.

Estes scripts são **opcionais** e **independentes** do pipeline principal. Eles permitem que o pesquisador (ou o Claude orquestrador) execute buscas em bases bibliográficas individuais, agregue os resultados, deduplique, e produza o `searches.json` que o `assessor` consome na Fase 3 do fluxo.

## Política operacional de tiers OA (v2.1+)

A partir da v2.1, os scripts seguem a constraint OA-first do projeto, descrita em `references/databases/oa-tiers.md`:

- **Tier 1 — sempre OA, sempre buscar.** Bases que disponibilizam full-text gratuito (arXiv, SciELO, PubMed Central, EuropePMC, ERIC OA, DOAJ, OpenAlex com filtro `is_oa=true`, Crossref com filtro de licença OA, OSF Preprints, Zenodo, etc.). **Os scripts deste diretório implementam predominantemente Tier 1.**
- **Tier 2 — metadados livres, full-text pode requerer fornecimento.** Bases que permitem busca livre por metadados mas o full-text pode estar em paywall (Crossref geral, OpenAlex geral, Semantic Scholar, PubMed completo, etc.). Os scripts deste diretório também cobrem alguns Tier 2 — declare explicitamente a limitação de full-text no manuscrito final.
- **Tier 3 — apenas via material fornecido pelo usuário.** Bases atrás de paywall completo (Scopus, Web of Science, Embase, IEEE Xplore subset paywall, ACM DL subset paywall, etc.). **Os scripts NÃO acessam Tier 3 diretamente.** O usuário, se tem acesso institucional, exporta CSV/RIS e fornece como input via `--user-supplied-tier3` no orquestrador.

## Orquestrador `search_orchestrator.py` (novo na v2.1)

Recomendado para uso de bases múltiplas em série, com transparência ao usuário:

```bash
python3 search_orchestrator.py \
    --query "letramento digital idosos" \
    --year-start 2020 --year-end 2026 \
    --area saude \
    --mode scoping_review \
    --output-dir search_results/
```

O orquestrador:
1. Imprime **disclosure pré-busca** ao usuário (quais bases serão consultadas, em que tier, quais NÃO serão).
2. Executa scripts Tier 1 para a área especificada.
3. Aceita opcionalmente `--user-supplied-tier3 path/to/scopus_export.csv` quando o usuário fornece material Tier 3.
4. Imprime **disclosure pós-busca** com contagens por tier.
5. Gera `search_summary.json` com checks de compliance vs requisitos do modo.
6. Falha com exit code 2 se o modo exige mais bases Tier 1 do que foram efetivamente buscadas.

**Áreas reconhecidas**: `saude`, `educacao`, `cs_se`, `multi`.

**Modos reconhecidos**: todos os 10 modos da v2.1 (scoping_review, rapid_review, mapping_study, systematic_review_with_2_reviewers, integrative_review, realist_review, software_paper, position_paper, technical_report, white_paper).

## Quando usar estes scripts

- **Construindo um pacote real do zero**: você está fazendo uma SLR sobre um tema novo, precisa executar buscas em múltiplas bases, e quer artefatos auditáveis com timestamp, query exata, e número de hits brutos.
- **Como apoio à Fase 3** do fluxo PRISMA-2020 do skill `ignorantia`. Os scripts produzem JSON normalizado que pode ser consolidado em `searches.json`.

**Não use** estes scripts:
- Para o conversor `slr_to_package.py` (que constrói pacotes mínimos a partir de DOIs já conhecidos via Crossref+OpenAlex — fluxo interno da calibração).
- Em substituição ao protocolo pré-registrado: estes scripts executam buscas; o protocolo deve estar fechado e validado pelo usuário ANTES de qualquer busca.
- Para burlar paywall: bases pagas (Scopus, WoS, IEEE Xplore, ScienceDirect) não são acessíveis aqui; consulte `references/databases/international.md` para alternativas legítimas via Portal CAPES/CAFe.

## Scripts disponíveis

Cada script aceita uma query booleana + filtros e produz JSON normalizado com os campos: `id`, `title`, `authors`, `year`, `venue`, `doi`, `url`, `abstract` (quando disponível), `source` (nome da base), `query_used`, `fetched_at`.

### `search_crossref.py` — Crossref REST

API gratuita, sem auth obrigatória. Cobre virtualmente todos os DOIs registrados (~140M). Política polite-pool: passe `--email` para acessar o pool prioritário.

```bash
python3 search_crossref.py \
    --query "systematic review AND digital literacy AND elderly" \
    --year-start 2018 --year-end 2026 \
    --type journal-article \
    --email seu@email.org \
    --output crossref_results.json
```

**Limitações conhecidas**: ~50% das SLRs não têm abstract no metadata Crossref (Lancet/BMJ/JAMA não depositam). Use `enrich_abstracts_openalex.py` (fluxo interno do skill) ou complemente com Semantic Scholar.

### `search_semantic_scholar.py` — Semantic Scholar Graph API

Cobertura ampla (~200M papers), inclui abstracts via OpenAccess. Rate limit gratuito: 100 req/5min sem API key; passe `--api-key` se tiver uma para limites maiores.

```bash
python3 search_semantic_scholar.py \
    --query "digital literacy elderly" \
    --year-start 2018 --year-end 2026 \
    --fields-of-study "Education,Computer Science,Medicine" \
    --max-results 1000 \
    --api-key $S2_API_KEY \
    --output s2_results.json
```

### `search_arxiv.py` — arXiv

Para preprints em CS/Math/Physics/Stats/Econ/Bio. API ATOM gratuita, sem auth.

```bash
python3 search_arxiv.py \
    --query "all:\"digital literacy\" AND cat:cs.HC" \
    --start-date 2018-01-01 --end-date 2026-12-31 \
    --max-results 500 \
    --output arxiv_results.json
```

### `search_dblp.py` — dblp

Específica para Computer Science: conferências, journals, artigos peer-reviewed. Não tem abstracts mas tem metadata de alta qualidade.

```bash
python3 search_dblp.py \
    --query "systematic review software engineering" \
    --max-results 1000 \
    --output dblp_results.json
```

### `search_scielo.py` — SciELO

Para SLRs e estudos publicados em periódicos lusófonos/ibero-americanos. Útil para complementar bases internacionais com produção brasileira/latina.

```bash
python3 search_scielo.py \
    --query "letramento digital idosos" \
    --year-start 2020 --year-end 2026 \
    --lang pt \
    --max-results 200 \
    --output scielo_results.json
```

## Fluxo recomendado

1. **Protocolo fechado** (Fase 2 do skill). Query booleana definida, lista finita de bases declarada, critérios I/E numerados.
2. **Execute cada base** com seu script correspondente. Salve cada output JSON com timestamp e versão da query.
3. **Consolide** em `searches.json` único (pode usar `jq` ou um script ad-hoc):
   ```bash
   jq -s '{databases: map(.source), per_database: ., total_hits: (map(.results | length) | add)}' \
       crossref_results.json s2_results.json arxiv_results.json scielo_results.json > searches.json
   ```
4. **Deduplique** com `scripts/deduplicate.py` (DOI > arXiv ID > título+autor+ano).
5. **Screening** L1 (título/abstract) e L2 (full-text).
6. **Quality appraisal** (CASP/DARE) sobre os incluídos.
7. **Extração** + **Síntese**.
8. **Avaliação** via `scripts/assessor/main.py`.

## Notas sobre rate limits e ética

- **Sempre** passe `--email` ou `--api-key` quando o serviço aceitar. Evita ban e respeita políticas de uso.
- **Espere entre requisições**: todos os scripts têm delays internos (1-3s entre páginas). Não os remova.
- **Cache**: se vai rodar múltiplas vezes, considere salvar respostas brutas e iterar offline.
- **Reprodutibilidade**: salve `query_used` e `fetched_at` em cada output. Crucial para o protocolo PRISMA.

## Limitações declaradas

- **Cobertura desigual entre bases**: Crossref e OpenAlex são as mais inclusivas; arXiv é restrito a STEM-preprints; SciELO foca em ibero-américa.
- **Sem acesso a paywall**: Scopus, WoS, IEEE Xplore, ScienceDirect, Springer Link não são alcançados aqui. Use Portal CAPES/CAFe para acesso institucional.
- **Não substitui o pesquisador humano**: estes scripts executam queries e agregam resultados; a validação metodológica (relevância, escopo, viés de publicação) é responsabilidade do pesquisador.
- **Abstracts faltantes**: alguns publishers (Lancet/BMJ/JAMA) não depositam abstracts em Crossref. Complemente com OpenAlex inverted-index quando precisar.

## Para mais informações

- Pilha de fontes confirmada empiricamente (Rodada J-recovery): Crossref REST + OpenAlex + Europe PMC + Unpaywall — todos com endpoints documentados.
- **Não use** scraping HTML do `doi.org` ou `www.scielo.br` (retornam 403 por WAF).
- Sintaxe específica de cada base em `references/databases/international.md` e `references/databases/portuguese.md`.
- Documentação do PRISMA-2020 em `references/prisma-2020.md`.
