# Sprint Badge — Roadmap de Calibração Formal

**Data**: 2026-04-29 | **Estado**: pré-execução | **Estimativa**: 7 rodadas (J-P)

## Meta global

Coletar **300 SLRs reais** (50 por estrato × 6 estratos: A1, A2, A3, A4, B1, B2) com ground-truth Qualis CAPES 2021-2024 confirmado, rodar pipeline ignorantia em cada uma, validar empiricamente as faixas atuais (heurísticas) e recalibrar thresholds se houver drift sistemático.

## As 7 rodadas

### Rodada J — Definição + coleta de corpus de calibração
- **J1**: Definir critérios canônicos de inclusão (apenas SLRs reais com PRISMA declarado, exclusão de scoping reviews, narrative reviews, meta-análises puras de RCTs).
- **J2**: Mapear venues por estrato Qualis: extrair Plataforma Sucupira CAPES 2021-2024 → tabela `venue → estrato_canônico_por_área_mãe`.
- **J3**: Coleta via API: SciELO (PT-BR), PMC (saúde), arXiv (CS), DOAJ (cobertura geral).
- **J4**: Triagem automatizada por título/abstract para SLRs reais (regex + classificador heurístico).
- **J5**: Inspeção manual por amostragem (20% do corpus) para validar triagem.
- **Output**: `references/calibration-corpus-300.json` (DOI + venue + estrato + texto full + bibliografia normalizada).

**Custo estimado**: alto (rate limits APIs, paywalls). Plano: priorizar acesso aberto. Tempo: ~3-5 sessões.

### Rodada K — Extração padronizada de conteúdo
- **K1**: Pipeline `pdf2text` para conteúdo paywalled disponível institucionalmente.
- **K2**: Conversor automatizado SLR→pacote ignorantia (extrair seções via regex de PRISMA, montar extraction.csv heurístico, gerar QA proxy via texto).
- **K3**: Validação manual de 30 pacotes (10% × 3 estratos representativos).
- **K4**: Refinamento do conversor.
- **Output**: 300 pacotes ignorantia em `/calibration-packages/`.

**Risco**: extração heurística pode falhar em SLRs com formato não-padrão. Plano: descartar SLRs que falham na extração (até 10% perda aceitável).

### Rodada L — Execução em batch
- **L1**: Script orchestrator: roda `assessor.main` + `render_v2` em todos os 300 pacotes.
- **L2**: Tratamento de erros (timeouts, encoding, refs malformadas).
- **L3**: Coleta de outputs em `/calibration-results/` (300 JSONs + métricas agregadas).
- **L4**: Sanity check: distribuição de Conteúdo dentro de cada estrato.
- **Output**: Tabela mestre `calibration-results.csv` (300 linhas × campos: estrato_real, conteúdo, forma, sprint_badge_gerado, ajustes_aplicados, etc.).

**Custo estimado**: baixo (já temos pipeline pronto). Tempo: 1-2 sessões.

### Rodada M — Análise estatística
- **M1**: Box plots de Conteúdo e Forma por estrato Qualis real (qual a média, mediana, IQR, outliers).
- **M2**: Correlação Pearson e Spearman entre nota Conteúdo e estrato (esperado: correlação positiva forte, ρ > 0.6).
- **M3**: Matriz de confusão `estrato_real × estrato_predito` pelo Sprint Badge (validar se a heurística atual classifica corretamente).
- **M4**: Curvas ROC para classificação binária A1-A2 vs B1-B2 (validar discriminação).
- **M5**: Identificar overlaps sistemáticos (ex: se SLRs A2 estão concentradas em 8.5-9.5 mas faixa atual diz 9.0-9.5, há drift).
- **M6**: Análise de subgrupo: por área-mãe (educação, saúde, CS, humanidades) — testa se faixas precisam de calibração separada por área.
- **Output**: Relatório `M-analysis.md` com gráficos + tabelas + achados.

**Tempo**: 1-2 sessões.

### Rodada N — Recalibragem dos thresholds
- **N1**: Ajustar faixas baseado em M5: se SLRs A2 reais estão em 8.5-9.5, mover threshold A2 de 9.0 → 8.5.
- **N2**: Cross-validation 5-fold: separar 80% do corpus para calibração, 20% para teste. Repetir 5×.
- **N3**: Sensitivity analysis: como ajustes (−0.5/+0.3) afetam classificação? Talvez magnitudes precisem ajuste.
- **N4**: Decisão sobre calibração por área-mãe vs unificada (decisão epistemológica relevante para o doc).
- **N5**: Validação dos 4 casos atuais (smoke/corpus18+/ghostwriter/H) — devem permanecer estáveis nos achados qualitativos.
- **Output**: Novos thresholds em `sprint_badge.py` + justificativa quantitativa.

**Tempo**: 1 sessão.

### Rodada O — Implementação dos thresholds calibrados
- **O1**: Atualizar `TIER_TABLE` em `sprint_badge.py` com thresholds calibrados.
- **O2**: Atualizar magnitudes de ajustes se N3 indicar (ex: −0.5 vira −0.3 se análise mostrar penalização excessiva).
- **O3**: Adicionar (opcional) calibração por área-mãe: parâmetro `area_motha` no `compute_sprint_badge` que selecione tabela apropriada.
- **O4**: Regressão completa nos 4 casos atuais + 9 cenários do mini-Sprint Rodada I.
- **O5**: Bump versão para `v2.1.0` (mudança não-retrocompatível justifica minor bump por SemVer).
- **Output**: `v2.1.0` empacotado.

**Tempo**: 1 sessão.

### Rodada P — Documentação final + paper técnico
- **P1**: Atualizar `sprint-badge-calibration.md` com resultados empíricos (substituir "heurístico" por "calibrado em 300 SLRs").
- **P2**: Escrever paper técnico sobre o método (`docs/sprint-badge-method.md`): protocolo de calibração, estatística, limitações persistentes.
- **P3**: Disponibilizar dataset de calibração em `/calibration-corpus-300.json` (apenas DOIs + métricas, não texto full por copyright).
- **P4**: Atualizar README + journal.
- **Output**: docs final + dataset reproduzível.

**Tempo**: 1 sessão.

## Critérios de sucesso

- [ ] 300 SLRs com ground-truth Qualis confirmado coletadas
- [ ] Pipeline batch sem erros em ≥90% dos casos
- [ ] Correlação Pearson nota↔estrato ≥ 0.60
- [ ] Faixas Sprint Badge classificam corretamente ≥70% das SLRs no estrato declarado (matriz de confusão)
- [ ] Drift residual ≤ ±0.3 em cada threshold após calibração
- [ ] Decisão documentada sobre calibração por área-mãe vs unificada
- [ ] 4 casos atuais permanecem estáveis em status qualitativo (Smoke=NÃO-CLASS, Caso H≈B3, etc.)

## Riscos identificados

1. **Acesso fechado**: SLRs paywalled em editoras não-OA (Elsevier, Springer fechado). Plano: priorizar OA, documentar viés residual.
2. **Ground-truth Qualis frágil**: estrato muda por área-mãe. Plano: registrar estrato canônico (mais alto entre áreas-mãe relevantes).
3. **SLRs não-PRISMA**: muitas "revisões sistemáticas" não seguem PRISMA-2020. Plano: triagem manual rejeita.
4. **Drift por idioma**: SLRs em PT-BR podem ter perfis diferentes de EN. Plano: estratificar análise por idioma se sample-size permitir.
5. **Drift por época**: Qualis muda a cada 4 anos. Plano: limitar corpus a venues estáveis no ciclo 2021-2024.

## Dependências externas

- Plataforma Sucupira CAPES (gratuito, API instável)
- SciELO API (gratuito, OA)
- PMC API (gratuito, OA)
- arXiv API (gratuito, mas rate-limits agressivos vistos hoje)
- DOAJ API (gratuito, OA)

Nenhuma dependência paga, mas tempo de coleta limitado por rate limits.

## Total estimado

**7 rodadas** (J-P) × ~1-3 sessões cada = **8-12 sessões totais** dedicadas exclusivamente ao Sprint formal, mais tempo de espera para coletas via API.

**Outputs principais**:
- Dataset de calibração reproduzível
- `v2.1.0` com thresholds calibrados empiricamente
- Paper técnico documentando o método
