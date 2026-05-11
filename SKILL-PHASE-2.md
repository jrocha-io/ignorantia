---
name: ignorantia-phase-2
description: Phase 2 da skill bifásica. Roda em Anthropic Cowork. Consome o handoff JSON emitido por Phase 1 (Claude Desktop). Faz retrieval de full-text das DOIs incluídas, lê cada paper, extrai dados com mapeamento claim-to-source, executa snowballing backward, conduz quality appraisal, redige manuscrito em LaTeX com citações rastreáveis, compila para PDF + DOCX, roda 7 gates programáticos sequenciais, e sela o pacote Zenodo. **Não produz nada sem handoff válido de Phase 1.** USE quando o usuário invocar `/ignorantia-execute <handoff.json>` em Cowork, ou pedir para continuar uma SLR a partir de um handoff existente.
---

# ignorantia — Phase 2 (Cowork)

> Phase 2 é o throughput pesado da skill bifásica. Phase 1 (chat) decidiu *o quê*; Phase 2 (Cowork) faz *quanto for preciso* — retrieval, leitura, extração rastreável, síntese e compilação. O artefato final é um pacote Zenodo que, por construção mecânica (7 gates), está pronto para upload sem revisão humana adicional.

## Entrada

Phase 2 começa com **um único arquivo**: `handoff-v<X.Y.Z>.json` produzido por Phase 1, validado contra `schemas/handoff-v1.schema.json`.

Se o handoff é inválido (schema mismatch ou `handoff_hash` não recalcula), **aborte imediatamente** com diagnóstico ao usuário. Phase 2 não recupera de input quebrado — o operador volta para Phase 1.

Comando de invocação típico: `/ignorantia-execute path/to/handoff-v1.0.0.json`.

## Saída

**Único artefato:** `<author-slug>-<area>-<topic>-v<X.Y.Z>.zip`, contendo:

- Pacote acadêmico canônico: `manuscript.tex`, `manuscript.pdf`, `manuscript.docx`, `bibliography.bib`
- Secundários: `protocol.md`, `searches.json`, `screening.csv`, `quality-appraisal.csv`, `extraction.csv`, `prisma-flow.svg/pdf`, `snowballing_backward.json`, `claim_to_source.json`, `gap_report.md`, `citations_to_obtain_<base>.md` (por base sem credencial)
- Compliance: `venue-suggestions.md`, `ai-declaration.md`, `compliance-checklist.md`
- Avaliação: `avaliacao_v<X.Y.Z>.md`
- Sidecars dos 7 gates: `persona_voice_gate.json`, `assessment_gate.json`, `pipeline_invariants_gate.json`, `vocabulary_gate.json`, `claim_source_gate.json`, `citation_graph_gate.json`, `manuscript_substantial_gate.json`
- README com SHA-256 de cada artefato + `LICENSE` (CC-BY-4.0 default)

**Critério mecânico de pronto:** os 7 sidecars de gate existem no `<output_dir>/` com `passed: true`. Phase 2 só sela o ZIP se os 7 estão verdes.

## Filosofia operacional

1. **Sem mistério, sem mágica.** Phase 2 lê o handoff, faz as operações declaradas, registra trace para tudo. Cada citação no manuscrito tem um `claim_id` que mapeia para uma página/seção do paper-fonte.
2. **Determinismo onde possível.** Mesmo handoff + mesmas credenciais + mesma janela de tempo → resultado equivalente (sujeito a estabilidade dos índices). Phase 2 grava timestamps mas não introduz variabilidade.
3. **Falha não-silenciosa.** Cada gate emite sidecar JSON; falha bloqueia o ZIP e o operador vê o que faltou. Sem ZIP "talvez OK".
4. **Honestidade na cobertura.** Itens irrecuperáveis vão para `gap_report.md` com causa explícita; o manuscrito declara as lacunas em §07 (Limitações). Sem inflar cobertura.
5. **Reprodutibilidade audit-grade.** Toda decisão de inclusão/exclusão, toda página citada, todo DOI verificado — tudo registrado em CSVs e JSONs com hash SHA-256 no README.

## Vocabulário de artefatos (vinculante)

Aplica-se a TODO arquivo de prosa que vai pro ZIP: manuscript, protocol, README, compliance, AI declaration, venue suggestions, avaliação, gap report, citations-to-obtain. Cinco regras (idênticas a Phase 1):

1. **A skill nunca se nomeia no artefato.** O nome `ignorantia` não aparece em nenhum campo visível ao leitor.
2. **Identidade da IA via padrão de segredo industrial.** Phase 2 renderiza o bloco de AI disclosure usando o template-key do handoff (`industrial_secret_cnpq_pt` ou `industrial_secret_icmje_en`).
3. **Voz acadêmica neutra impessoal** ("foi conduzido", "observou-se").
4. **Vocabulário operacional fora dos artefatos.** Antes de gravar qualquer prosa, traduzir labels operacionais via `references/artifact-vocabulary-policy.xml`.
5. **Meta-projeto não vaza.** Nomear projeto específico no §01 do manuscrito; nunca "projeto subjacente" / "as outras N revisões" / "função declaratória/instrumental".

## Workflow Phase 2 (10 etapas)

### Etapa 1 — Validação do handoff

1. Carregar `handoff-v<X.Y.Z>.json`.
2. Validar contra `schemas/handoff-v1.schema.json`. Aborte se inválido.
3. Recomputar `handoff_hash` (SHA-256 do JSON canonicalizado sem o campo). Aborte se diferente.
4. Verificar que toda DOI em `included_for_fulltext[]` tem entrada em `screening.trace_per_doi` com decisão final positiva. Aborte se inconsistente.
5. Criar `<output_dir>/` (timestamp + slug) e gravar uma cópia imutável do handoff em `<output_dir>/handoff.json`.

### Etapa 2 — Full-text retrieval

Para cada item em `included_for_fulltext[]`:

- **Cascade de acesso aberto:** Unpaywall → CORE → Open Access Button → repositório institucional (arXiv/PMC/Zenodo via DOI).
- **Credencial institucional:** se o operador declarou credencial para a base do paper (campo `protocol.bases[].execution_mode = credential_required`), tentar via proxy.
- **Sem retrieval possível:** registrar em `gap_report.md` com `{doi, title, expected_access_tier, attempted_methods, status}`. Item sai do corpus final.

Gravar cada PDF/HTML baixado em `<output_dir>/sources/<doi-slug>.pdf|.html`. Cache de DOIs verificados em `<output_dir>/doi_verification_cache.json`.

### Etapa 3 — Leitura e extração com claim-to-source mapping

Para cada paper recuperado:

1. Extrair texto (PDF parsing ou HTML parsing).
2. Identificar seções relevantes para extração (Introdução, Métodos, Resultados, Limitações).
3. Aplicar formulário de extração (`assets/templates/extraction-form.xml`).
4. **Para cada claim substantivo** que sairá do paper para o manuscrito final, criar um registro em `claim_to_source.json`:

   ```
   {
     "claim_id": "C-S08-001",
     "claim_text": "Reporta speed-up de 58× em screening assistido por IA.",
     "source_doi": "10.1234/example",
     "source_anchor": "p.7 §3.2 ¶2",
     "extracted_at": "<ISO timestamp>"
   }
   ```

   `claim_id` é único; usa um padrão estável (`C-<StudyID>-<seqno>`).

5. Gravar `extraction.csv` com colunas: `study_id`, `doi`, `title`, `year`, `venue`, `study_type`, `area`, `intervention`, `methods`, `findings`, `limitations`, `coi_declared`, `repro_package_available`, `claim_ids` (lista CSV de claim_ids relacionados).

### Etapa 4 — Quality appraisal

Aplicar CASP/DARE (saúde), Kitchenham QA1–QA8 (SE/CS), ou JBI Critical Appraisal (scoping). Score por estudo, por questão, registrado em `quality-appraisal.csv`.

Threshold de QA: estudos abaixo do corte ficam sinalizados na síntese (não excluídos automaticamente — registrar limitação).

### Etapa 5 — Snowballing backward (mini-loop)

Para os 3-10 estudos seed (declarados em `included_for_fulltext[].seed_for_snowballing = true` ou os top-N por relevância):

1. Extrair lista de referências do paper.
2. Recuperar DOIs/metadados das referências via Crossref + OpenAlex.
3. Aplicar **screening rápido por título/abstract** (mesmo critério de Phase 1, simplificado).
4. Para sobreviventes: retrieval full-text → extração → adicionar ao corpus.
5. Cap em **2 níveis** de snowballing (seed → ref → ref-of-ref STOP). Sem recursão infinita.
6. Registrar em `snowballing_backward.json` o trace completo: seed_doi → ref_doi → decisão.

### Etapa 6 — Cross-tabulação obrigatória

Gerar ≥1 tabela cruzando duas dimensões metodologicamente relevantes (ex: modelo de IA × fase do PRISMA; ou intervenção × outcome × país). Registrar a tabela em `cross_tab.json` (estrutura) + Markdown para inserção no manuscrito.

### Etapa 7 — Síntese narrativa

Redigir o manuscrito em LaTeX (`manuscript.tex`) seguindo IMRaD adaptado por modo:

- §00 Declaração de propósito (com tradução do `review_purpose` enum para prosa)
- §01 Declaração de CoI (nomeando o projeto específico do `protocol.authors[]`/handoff context)
- §02 Introdução
- §03 Pergunta de pesquisa (PCC + sub-perguntas)
- §04 Métodos (descrevendo PRISMA, bases sem labels Tier, screening sem "Decisão N")
- §05 Resultados (PRISMA flow + tabelas + cross-tab)
- §06 Discussão (por RQ)
- §07 Conclusões
- §08 Evidência contrária encontrada
- §09 Limitações
- Refs (formatadas pela norma do `protocol.citation_style`)

**Cada claim substantivo no manuscrito é citado com `\cite{claim_C-XX-NNN}`** ou marcador equivalente que mapeia para `claim_to_source.json`. O Gate 5 (claim-source coverage) verifica que 100% dos claims têm mapeamento.

Bloco "Declaração de uso de IAG" / "Declaration of AI use" inserido em §03.x conforme `protocol.ai_disclosure.template`.

### Etapa 8 — Compilação

1. `pdflatex manuscript.tex` (1ª passada)
2. `bibtex manuscript` (resolve referências)
3. `pdflatex manuscript.tex` (2ª passada — labels)
4. `pdflatex manuscript.tex` (3ª passada — final)
5. `pandoc manuscript.tex -o manuscript.docx --bibliography=bibliography.bib`

Logs em `<output_dir>/compile.log`. Falha de compilação → Gate 7 (manuscript-substantial) detecta.

### Etapa 9 — 7 Gates sequenciais

Executar via shell short-circuit `&&`:

```
python3 scripts/check_persona_voice.py manuscript.tex --strict && \
python3 scripts/generate_assessment.py --package-dir <output_dir> --gate-min-score 7.0 && \
python3 scripts/check_pipeline_invariants.py <output_dir> && \
python3 scripts/check_decision_19_vocabulary.py --all <output_dir> --gate-sidecar --quiet && \
python3 scripts/check_claim_source_coverage.py <output_dir> && \
python3 scripts/check_citation_graph.py <output_dir> --verify-dois && \
python3 scripts/check_manuscript_substantial.py <output_dir>
```

Cada gate exit 2 em falha → ZIP não é selado.

| Gate | Verifica | Bloqueia se |
|---|---|---|
| 1. persona-voice | Voz acadêmica neutra | "Phase N invocou X.py" / vocabulário operacional |
| 2. assessment | Nota ≥ 7.0, zero eliminatórios | Manuscrito declaradamente inaceitável |
| 3. pipeline-invariants | Sem ad-hoc search, ≥3 bases, sem steps em ERROR | Pipeline malformado |
| 4. vocabulary | Zero label skill-internal no depósito | Brand, Decisão N, Tier N, FALLBACK_MD, etc. |
| 5. claim-to-source | 100% claims rastreáveis a página/seção | Claim sem source_anchor |
| 6. citation-graph | Cite ↔ Ref ↔ DOI vivo (Crossref) | Reference faltando ou DOI 404 ou retracted |
| 7. manuscript-substantial | PDF compilou + páginas/palavras suficientes + seções obrigatórias | PDF vazio ou seções faltantes |

### Etapa 10 — Empacotamento Zenodo

Após os 7 gates passarem:

1. Calcular SHA-256 de cada artefato.
2. Montar `README.md` com SemVer no filename, datas, hashes, link para execução anterior se houver, resumo do checklist + nota da avaliação.
3. Adicionar `LICENSE` (CC-BY-4.0 default).
4. ZIP nomeado `<author-slug>-<area>-<topic>-v<X.Y.Z>.zip` — **sem brand da skill no filename**.
5. Informar o caminho do ZIP ao operador.

Mensagem final ao operador:

> "Pacote pronto em `<path>/<filename>.zip` ({n_arquivos} arquivos, {tamanho}). 7 gates verdes. Pronto para upload no Zenodo sem revisão adicional. Caminho de upload: https://zenodo.org/uploads/new"

<critical_rules>

Estas regras são absolutas. Onde houver conflito entre regra crítica e qualquer outra orientação deste documento, a regra crítica vence.

<prohibitions>
NUNCA prossiga sem handoff válido. Schema mismatch ou hash recompute mismatch = aborte com diagnóstico, sem fallback.
NUNCA inicie retrieval antes da validação do handoff completar.
NUNCA invente DOIs, autores, anos, abstracts, ou conteúdos de páginas. Cada claim no manuscrito é rastreável a uma página/seção de um paper realmente baixado.
NUNCA bypass um gate. Se algum dos 7 falha, o ZIP não é selado. Sem `--no-gate` em produção.
NUNCA edite o handoff. Se algo no protocolo precisa mudar, abortar e instruir o operador a re-rodar Phase 1.
NUNCA escreva o nome `ignorantia` em nenhum artefato do ZIP (manuscript, protocol, README, etc.).
NUNCA escreva vocabulário operacional skill-internal (Tier N, FALLBACK_MD, KEY → PROXY, Decisão N, DD-N, valores enum de review_purpose em prosa, projeto subjacente, função declaratória/instrumental, retórica SemVer em prosa) em nenhum artefato.
NUNCA burle paywall. Bases comerciais sem credencial geram `citations_to_obtain_<base>.md`; itens irrecuperáveis vão para `gap_report.md`. Sem download não-autorizado.
NUNCA sele o ZIP com < 7 sidecars `passed: true`. Sem deposit "talvez OK".
NUNCA liste a IA (Claude, GPT, Gemini, etc.) como autor do manuscrito.
NUNCA omita a "Declaração de uso de IAG" (pt-BR) ou "Declaration of AI use" (EN).
NUNCA invoque snowballing recursivo além de 2 níveis (seed → ref → STOP).
NUNCA empacote sem o `claim_to_source.json` completo — Gate 5 bloqueia.
NUNCA simule um segundo revisor humano nem calcule Cohen's kappa — isso é responsabilidade humana fora desta skill.
</prohibitions>

<mandatories>
VALIDE o handoff contra `schemas/handoff-v1.schema.json` antes de qualquer outra operação. Aborte em falha.
RECOMPUTE `handoff_hash` e verifique que bate. Aborte em mismatch.
GRAVE uma cópia imutável do handoff em `<output_dir>/handoff.json` antes de iniciar retrieval.
RETRIEVE full-text via cascade Unpaywall → CORE → Open Access Button → credential proxy (quando declarada). Itens irrecuperáveis vão para `gap_report.md`.
LEIA cada paper baixado. Não extraia apenas de abstract.
CRIE `claim_to_source.json` com `{claim_id, claim_text, source_doi, source_anchor}` para cada claim substantivo que aparecerá no manuscrito.
APLIQUE quality appraisal CASP/DARE/Kitchenham/JBI por estudo, por questão.
EXECUTE snowballing backward limitado a 2 níveis (seed → ref → STOP). Registre trace completo em `snowballing_backward.json`.
GERE cross-tabulação obrigatória em `cross_tab.json` + Markdown.
LEIA `references/artifact-vocabulary-policy.xml` ANTES de gravar QUALQUER prosa.
LEIA `assets/templates/persona-voice.xml` ANTES de redigir o manuscrito. O scaffold de voz é vinculante.
REDIJA o manuscrito em LaTeX seguindo IMRaD adaptado. Cada claim substantivo cita um `claim_id`.
INSIRA o bloco de AI disclosure em §03.x conforme `protocol.ai_disclosure.template`.
COMPILE: pdflatex → bibtex → pdflatex × 2 → pandoc para DOCX. Logs em `compile.log`.
EXECUTE os 7 gates sequenciais via `&&`. Cada gate emite sidecar JSON em `<output_dir>/`.
NOMEIE o ZIP como `<author-slug>-<area>-<topic>-v<X.Y.Z>.zip` — sem brand da skill no filename.
INCLUA hash SHA-256 de cada artefato no README.
PARE depois de informar o caminho do ZIP. Não invoque Zenodo upload, não envie email, não contate autores. A skill produz o artefato; depósito é manual.
</mandatories>

<verifiable_acceptance_criteria>
O handoff foi validado contra schema e o hash recomputado.
`<output_dir>/handoff.json` é cópia byte-for-byte do handoff de entrada.
Toda DOI em `included_for_fulltext[]` teve tentativa de retrieval registrada (sucesso, gap, ou citation-list).
Cada paper baixado tem entrada em `extraction.csv`.
`claim_to_source.json` tem ≥1 entrada por linha de `extraction.csv` que contribuiu para a síntese.
Manuscrito compila sem erros para PDF (verificável via `manuscript.pdf` no `<output_dir>/`).
Os 7 sidecars de gate existem com `passed: true`.
ZIP nomeado conforme `<author-slug>-<area>-<topic>-v<X.Y.Z>.zip` (zero brand).
README lista SHA-256 de cada artefato + a versão SemVer + checklist de compliance + nota da avaliação automática.
A IA não está listada como autor no manuscrito.
Bloco de declaração de uso de IA presente em §03.x.
Zero menções de `ignorantia` em qualquer prosa do ZIP.
Zero label skill-internal (Tier N, FALLBACK_MD, Decisão N, etc.) em qualquer prosa do ZIP.
</verifiable_acceptance_criteria>

</critical_rules>

## Compliance ético e legal

Phase 2 implementa o que Phase 1 declarou no `protocol.ai_disclosure.template`.

### Manuscritos em pt-BR

Renderizar bloco "Declaração de uso de Inteligência Artificial Generativa" em §03.x:

> Em conformidade com a Portaria CNPq nº 2.664/2026, art. 9, declara-se:
>
> 1. Ferramenta(s) utilizada(s): algoritmo particular do autor — não-divulgado por segredo industrial — com modelo de linguagem da Anthropic, Claude (versão Opus 4.7), acessado via interface web claude.ai.
> 2. Versão e data de acesso: ... 
> 3. Etapas em que houve uso da ferramenta: [marcar conforme `protocol.ai_disclosure.stages_used`]
> ...

Aplicar simultaneamente: Portaria CNPq, Documentos de Área CAPES, CEP/CONEP (quando aplicável), LGPD, Lei de Direitos Autorais (LDA).

Carregue `references/compliance-ptbr.xml` para o checklist completo + bloco padrão.

### Manuscritos internacionais (EN)

Renderizar bloco "Declaration of AI use" conforme COPE + ICMJE 2024 update, usando o mesmo padrão de segredo industrial em inglês.

Carregue `references/compliance-international.xml`.

### Acesso legítimo a bases pagas

Para cada base declarada em `protocol.bases[].execution_mode = credential_required`:

1. Se o operador forneceu credencial: tentar via proxy institucional.
2. Caso contrário: gerar `citations_to_obtain_<base>.md` com a lista cruzada de itens identificados via Crossref/OpenAlex + 4 opções de obtenção (Portal CAPES com CAFe, biblioteca institucional, contato com autor, COMUT).

A skill **NÃO burla paywall**.

## Sugestão de venues para submissão

Antes do empacotamento, gerar lista de **3-5 venues** alinhados ao tema, idioma, e preferência por publishers de elite. Para cada venue:

- Nome (periódico ou conferência)
- Publisher / sociedade
- ISSN ou identificador
- URL da política de IA do publisher
- Indicador de qualidade (JIF/CiteScore ou Qualis)
- Modelo de acesso (subscription, hybrid, OA Gold com APC, OA Diamond)
- Estimativa de ciclo editorial
- Justificativa breve da adequação ao tema

Salvar em `venue-suggestions.md`. Lista canônica por área em `references/compliance-international.xml`.

## Arquivos de referência

- `docs/BIPHASIC-ARCHITECTURE.md` — **vinculante** — contrato Phase 1 ↔ Phase 2
- `schemas/handoff-v1.schema.json` — **vinculante** — schema de entrada
- `references/artifact-vocabulary-policy.xml` — **vinculante** — tabela de tradução de labels operacionais → prosa científica
- `references/quality-rubric.xml` — rubrica do Gate 2 (assessment)
- `references/citation-styles/{ieee,vancouver,apa,abnt}.xml` — normas
- `references/compliance-ptbr.xml` / `compliance-international.xml` — blocos de compliance + AI disclosure
- `references/output-design-patterns.xml` — padrões de design do HTML interativo (subcomando opcional `html-wiki`)
- `assets/templates/persona-voice.xml` — **vinculante** — scaffold de voz acadêmica
- `assets/templates/extraction-form.xml` — schema de extração
- `assets/templates/quality-appraisal.xml` — instrumentos CASP/DARE/Kitchenham
- `assets/templates/modes/*.xml` — protocolo-scaffold por modo de revisão (para referência; o modo já vem decidido no handoff)
