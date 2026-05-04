# Manual de auditoria completa do ignorantia

**Documento criado em** 2026-05-04 após auditoria #5 detectar que a abordagem iterativa estava descobrindo categorias novas em cada rodada (auditoria #1 olhou bugs óbvios; #2 achou bugs introduzidos pela #1; #3 achou integração ≠ implementação; #4 achou consistência cruzada; #5 achou paridade mock/real). O usuário observou corretamente que isso é desperdício: 5 rodadas para descobrir 5 dimensões. Este manual lista **todas as dimensões conhecidas** para auditoria em rodada única.

## Filosofia

**Uma auditoria sistemática completa custa 3-5x mais que uma rasa, mas substitui 5+ rodadas rasas.** O custo total é menor.

A abordagem iterativa rasa é boa para *aprender o sistema* (você descobre dimensões progressivamente). Para *fechar o ciclo*, use este manual.

**Princípios operacionais:**

1. **Honestidade analítica** — não bajulação. Reportar achados como achados, não como "oportunidades de melhoria".
2. **Fixação de erros não cria novos** — toda correção precisa de regressão E smoke real do caminho principal.
3. **Documentar achados antes de corrigir** — escrever `audit-N-strategy.md` antes de tocar código.
4. **Generalizar imediatamente** — quando achar um bug, executar a verificação 1 (generalização lateral) **antes** de mover ao próximo. Não acumular pendências.

## Procedimento

### Fase 0 — Inventário cruzado (15 min)

Antes de qualquer verificação, gerar matriz de inventário:

```bash
# Categorias do sistema
echo "Adapters totais: $(ls scripts/searches/search_*.py | wc -l)"
echo "TIER1_RUNNERS registrados: $(python3 -c 'import sys; sys.path.insert(0,"scripts/searches"); import search_orchestrator as so; print(len(so.TIER1_RUNNERS))')"
echo "Renderers: $(ls scripts/render_*.py | wc -l)"
echo "Decisões editoriais: $(grep -c '^### Decisão\|^## Decisão' references/DECISIONS.md)"
echo "DDs: $(grep -c '^### DD-' references/DECISIONS.md)"
echo "Pipeline steps: $(grep -c '^def _step_' scripts/pipeline_finalize.py)"
echo "Áreas suportadas: 7 (saude, educacao, cs_se, ciencias_sociais, humanidades, business, multi)"
echo "Modos: $(ls references/modes/mode-*.md | wc -l)"
echo "Citation styles: $(ls references/citation-styles/*.md | wc -l)"
echo "Tests: $(python3 -m pytest tests/ scripts/comparison/tests/ --collect-only -q 2>&1 | tail -1)"
echo "Profiles YAML: $(find references/profiles -name '*.yaml' | wc -l)"
```

Esses números aparecem em SKILL.md, README, CHANGELOG. **Erros declarativos (DIM 4) aparecem aqui imediatamente** — antes mesmo de começar a auditar dimensões.

---

### As 27 dimensões de auditoria

Cada dimensão tem: **diagnóstico** (como verificar), **exemplo de bug histórico** (quando aplicável), **comando shell ou script** quando há um one-liner.

#### Camada 1 — Correção do código

**DIM 1. Generalização lateral**
> Quando encontrar um bug em um sistema, todos os outros sistemas com design semelhante têm o mesmo bug?

- Bug em `search_arxiv.py`? Verificar `search_crossref/dblp/semantic_scholar.py`.
- Bug em `render_chunks.py`? Verificar `render_v2.py`, `render_docx_abnt.py`, `render_latex.py`.
- Bug em adapter paywall? Verificar os 16 paywall.
- Histórico: B2 (F4 atualizou `render_v2` mas não `render_chunks`); C1+C2 (B4 normalizou só 2 dos 4 retrofitted); D5 (A7 stderr não foi generalizado a 30+ adapters).

**DIM 2. Paridade mock vs real**
> O caminho mock e o caminho real produzem o mesmo schema/comportamento?

- Adapter `--mock` retorna chaves `{title, authors, year, language, is_oa, url}`. Função `normalize()`/`parse_entry()` real retorna as mesmas chaves?
- Schema de output é idêntico (mesmos campos top-level, mesmos campos item-level)?
- Histórico: D3 (C1 atualizou só os 4 mocks; reais ficaram divergentes).

```bash
# Diagnóstico
python3 scripts/searches/search_X.py --query test --mock --output /tmp/mock.json
python3 scripts/searches/search_X.py --query test --year-start 2023 --year-end 2024 --output /tmp/real.json
diff <(python3 -c "import json; print(sorted(json.load(open('/tmp/mock.json'))['results'][0].keys()))") \
     <(python3 -c "import json; print(sorted(json.load(open('/tmp/real.json'))['results'][0].keys()))")
```

**DIM 3. Integração end-to-end**
> O feature está acessível pelo caminho principal (pipeline, orquestrador, CLI default) ou apenas por chamada direta do módulo?

- Smoke real subprocess do caminho principal, **não** teste unitário em isolamento.
- Renderer recebe o feature? Pipeline propaga? Orquestrador chama com flags certas?
- Histórico: B1+B2 (F4 funcionou em renderers individuais mas pipeline não propagou preâmbulo).

```bash
# Smoke E2E pipeline_finalize completo
mkdir -p /tmp/audit_e2e && cp tests/fixtures/*.json /tmp/audit_e2e/  # ou criar fixtures
python3 scripts/pipeline_finalize.py --output-dir /tmp/audit_e2e \
  --title Test --version 1.0 --skip-pdf --screening-demo \
  --contextual-preamble --preamble-mock
# Verificar features no output
grep -c "<feature>" /tmp/audit_e2e/manuscript.html
```

**DIM 4. Paridade declarativa**
> Documentação, CHANGELOG, README, SKILL.md, docstring e código fonte concordam sobre o que o sistema faz? Contadores numéricos batem com a realidade?

- Validar contadores em SKILL.md/README contra inventário da Fase 0.
- Docstring de função declara `--year-start` mas argparse declara `--start-date`? (Bug A3.)
- README declara v2.21.0 mas código está v2.20.0? (Bug A1.)
- Histórico: A1, A4, B3, B5, B6, C4.

**DIM 5. Schema canônico**
> Existe um padrão definido (dataclass, schema JSON, type)? Todos os sistemas o usam? Se há divergência, por quê?

- `_adapter_base.FetchedItem` define schema. Todos os adapters usam? Apenas paywall (16/61).
- `pipeline_summary.json` tem `schema_version`. Outros outputs JSON também?
- Histórico: D4 (FetchedItem é canônico mas só paywall usa); D1+D2 (legacy adapters têm schemas heterogêneos).

**DIM 6. Edge cases e fallbacks**
> Inputs vazios, malformados, fora de janela temporal, parser não bate, rede timeout — todos tratados?

- HTML não bate padrão de regex → retorna lista vazia honestamente, não blob raw.
- Resposta JSON malformada → fallback HTML.
- Erro HTTP → mensagem útil em stderr E retorno estruturado com `error`.
- Histórico: parser LILACS/CLACSO/Dialnet/Redalyc tratam edge case "HTML não casa" graciosamente.

**DIM 7. Tratamento de erros**
> Exceções engolidas silenciosamente? Mensagens de erro vazias? Exit codes inconsistentes?

- `except Exception: pass` → engole erro silenciosamente.
- `return 0 if not r.get("error") else 1` sem `print(error, file=sys.stderr)` → orquestrador mostra `[warn]` vazio (D5).
- Histórico: A7 (grey_lit stderr); D5 (eric/edarxiv stderr vazio — A7 não foi generalizado).

```bash
# Detectar exceções engolidas
grep -rn "except.*:.*pass\|except.*:\s*$" scripts/ --include="*.py" | grep -v test
# Detectar exit 1 sem stderr (problema D5)
grep -B 2 "return 0 if not r.get" scripts/searches/*.py | grep -B 1 "print.*sys.stderr" | wc -l
```

**DIM 8. Recursos e performance**
> File descriptors fechados? Memory leaks? Loops com complexidade alta? Timeouts tratados?

- `open()` sem `with` → ResourceWarning (B8: 182 → 2).
- Loops O(n²) ou pior em datasets grandes.
- Subprocess sem `timeout=` → trava.
- Histórico: B8 (182 ResourceWarnings em test_v21_modes).

```bash
python3 -W default -m pytest tests/ 2>&1 | grep -c ResourceWarning
```

**DIM 9. Concorrência e estado**
> Variáveis globais mutáveis? Caches obsoletos? Race conditions em paralelismo?

- `sys.path.insert` em scripts diferentes pode criar ordem dependente.
- Estado em módulo (variáveis no top-level) compartilhado entre testes.
- Pipeline_finalize injeta `args._preamble_html` como side-effect — pattern frágil.

#### Camada 2 — Convenções e nomenclatura

**DIM 10. Convenções de domínio inconsistentes**
> Mesmo conceito tem múltiplas representações?

- `Tier 1` (espaço) vs `tier1` (junto) vs `tier_1` (underscore) — encontradas 56+46+0 ocorrências respectivamente.
- `pt-BR` vs `pt` vs `por` — encontradas 52+56+7.
- `lareferencia` vs `la_referencia` (F11/v2.19.0).
- `n` vs `total_results` (B4/v2.21.0).
- `url` vs `url_for_pdf` (D1/v2.22.0+).
- Histórico: F11, B4, B6, D1.

```bash
# Procurar variantes de termos do domínio
grep -rn "Tier 1\|tier1\|tier_1" scripts/ --include="*.py" | head
grep -rn '"pt-BR"\|"pt"\|"por"' scripts/ --include="*.py" | head
```

**DIM 11. Versões hardcoded e deriva**
> Constantes de versão duplicadas em vários lugares? Versão única é a fonte de verdade?

- `USER_AGENT = "ignorantia-skill/2.10.0"` em adapter A.
- `USER_AGENT = "ignorantia-skill/2.11.0"` em adapter B.
- `VERSION` em `contextual_preamble.py` está em 2.22.0.
- Cada adapter fossiliza versão diferente. Solução: derivar de uma constante única.

```bash
grep -rn "USER_AGENT = " scripts/ --include="*.py" | awk -F: '{print $3}' | sort -u
```

**DIM 12. Defaults inconsistentes**
> CLI flags têm defaults consistentes entre adapters similares?

- `throttle` em arxiv = 3.0; em doaj = 1.0; em `_adapter_base` `DEFAULT_THROTTLE` = ?
- `timeout` varia entre 30, 60, default urllib.
- `max_results` default = 100 em alguns, 500 em outros, 1000 em arxiv.

#### Camada 3 — Especificação vs implementação

**DIM 13. Decisões/DDs declaradas vs aplicadas**
> Cada decisão editorial e DD está realmente implementada?

- `references/DECISIONS.md` tem 33 decisões + 13 DDs declaradas. Cada uma é referenciada no código? Tem teste? Tem smoke?
- Quanto tempo desde a última verificação de que a decisão está aplicada?

```bash
# Decisões e DDs declaradas
grep -c '^### Decisão\|^## Decisão' references/DECISIONS.md
grep -c '^### DD-' references/DECISIONS.md
# Decisões referenciadas no código
grep -rn "Decisão [0-9]\|DD-[0-9]" scripts/ --include="*.py" | wc -l
# Listar decisões nunca referenciadas em código → gap declarativo
```

**DIM 14. PRISMA-2020 e padrões formais**
> Os 27 itens do PRISMA-2020 estão tratados? ACM SIGSOFT empirical standards? Outros padrões mencionados?

- Cada modo (scoping, rapid, mapping, etc.) declara aderência a um padrão. Validar item por item.
- `references/prisma-2020.md` tem cobertura completa? Ou só lista os itens?

**DIM 15. Profiles YAML — schema validation**
> 81 profiles YAML; todos seguem schema? Schema declarado em `references/profiles/_schema/`?

- Validar cada profile contra `venue_profile.schema.json`.
- Quais chaves são obrigatórias vs opcionais? Conjunto comum visto: `hard_requirements, metadata, taxonomy`. Outras chaves (`ai_disclosure_policy`, `oa_first_compatibility`, `reproducibility`, `scope`, `soft_signals`) são presentes em quantos profiles?

```bash
# Validação JSON Schema (jsonschema package)
python3 -c "
import yaml, json, jsonschema
from pathlib import Path
schema = json.loads(Path('references/profiles/_schema/venue_profile.schema.json').read_text())
errors = []
for p in Path('references/profiles').rglob('*.yaml'):
    if '_schema' in str(p) or '_guidelines' in str(p): continue
    try:
        jsonschema.validate(yaml.safe_load(p.read_text()), schema)
    except jsonschema.ValidationError as e:
        errors.append((p.name, str(e)[:80]))
print(f'Errors: {len(errors)}')
for name, err in errors[:5]: print(f'  {name}: {err}')
"
```

**DIM 16. Output validation contra schema**
> JSONs gerados por adapters/pipeline são validados contra schema declarado?

- 78 ocorrências de `json.dump` no código; 0 ocorrências de `jsonschema.validate`.
- Schema drift silencioso quando código muda.

#### Camada 4 — Reprodutibilidade e auditabilidade

**DIM 17. Reprodutibilidade**
> Mesma entrada gera mesma saída? Timestamps, seeds aleatórias, ordem não-determinística?

- 22 usos de `datetime.now()` em outputs de scripts — torna outputs não-determinísticos byte-a-byte.
- `set` em vez de `list` ordenado em sort por chave — ordem não-determinística.
- `random.seed` configurado? (0 ocorrências.)

**DIM 18. Reprodutibility manifest**
> Pipeline registra todas as decisões/parâmetros para reprodução? Decisão 22 cumprida?

- `reproducibility_manifest.yaml` é gerado pelo pipeline?
- Inclui versões de dependências, parâmetros, fixtures usados?
- Histórico: D6 (orquestrador NÃO gera summary final agregado).

**DIM 19. Auditabilidade — logs em duas camadas**
> DD-10 declarada. Camada 1 nativa? Camada 2 do screening?

- 16 paywall têm `log_camada1` (validado em smoke).
- Adapters legacy não têm — gap honesto declarado em SKILL.md.

#### Camada 5 — Compatibilidade e portabilidade

**DIM 20. Encoding e charset**
> UTF-8 explícito em todas as I/O? BOM tratado? Line endings consistentes?

- 151 ocorrências de `encoding="utf-8"` — bom.
- `Path().read_text(encoding="utf-8")` vs `.read_text()` (default platform). Consistência?

**DIM 21. Portabilidade de path**
> Path separators (`/` vs `\`)? `os.sep`? `pathlib.Path` em vez de strings?

- Hardcoded `/tmp/` em 3 lugares — sandbox-specific.
- Uso de `Path(__file__).parent` consistente.

**DIM 22. Versão de Python e dependências**
> `python3.12+` obrigatório? Imports condicionais para fallback?

- `python-docx` é dependência opcional (renderer docx é opcional).
- `pyyaml` requerido para profiles YAML — declaração explícita?

#### Camada 6 — Segurança e privacidade

**DIM 23. Credentials hardcoded**
> API keys, tokens, paths sensíveis em código?

- `os.environ.get("DIALNET_API_KEY")` é o padrão correto.
- Verificar `default=` em argparse `--api-key`. Não pode ter valor hardcoded.

**DIM 24. Input validation**
> Inputs do usuário validados antes de processar?

- `--query` é string livre — usado em URL? Sanitização? (`urllib.parse.quote`)
- Path traversal em `--output-dir`?

#### Camada 7 — Lifecycle e manutenção

**DIM 25. Código morto / TODOs antigos**
> Funções não usadas? Imports não utilizados? TODOs de >1 ano?

- 30 TODOs em scripts/. Quais são pré-existentes vs ativos?
- `render_manuscript.py` (DEPRECATED): 595 linhas. Pode ser removido em v3.0.0.
- Funções nunca chamadas em outros módulos → candidato a remoção.

**DIM 26. Versionamento (SemVer)**
> CHANGELOG completo? Breaking changes em minor/patch? Deprecations com timeline?

- Cada release entrada no CHANGELOG.
- DEPRECATED → quando será removido? `render_manuscript` declara "v3.0.0".
- Atualizações de schema (B4: `n` → `total_results`) seguem SemVer? Fizeram alias para retrocompat?

**DIM 27. Auditoria iterativa — meta**
> A auditoria está cobrindo dimensões novas a cada rodada (ineficiente) ou exaustiva em uma rodada?

- Se a auditoria N+1 acha bugs **introduzidos pela auditoria N**: indica que correções não tiveram regressão E2E. **Categoria de bug: pressa.**
- Se a auditoria N+1 acha bugs **pré-existentes em dimensão não coberta pela #N**: indica que esta lista de dimensões está incompleta. **Categoria de bug: cobertura.**
- Se a auditoria N+1 acha **0 bugs**: sistema convergiu (ou auditoria foi superficial).

---

## Prompt completo para auditoria sistemática

> Faça auditoria completa do projeto cobrindo as **27 dimensões** documentadas em `references/audits/AUDIT_PROCEDURE.md`. Para cada dimensão:
>
> 1. Aplique o diagnóstico declarado.
> 2. Documente achados (com referência a arquivo:linha) ou marque "OK" explicitamente.
> 3. Se achar bug, **antes** de mover à próxima dimensão: aplicar verificações 1 (generalização lateral), 2 (paridade mock vs real), e 3 (integração E2E) sobre o achado. Não acumular pendências.
>
> **Inventário inicial obrigatório** (Fase 0): rodar comandos da seção "Inventário cruzado" e validar que números em SKILL.md/README batem com realidade. Discrepâncias aparecem aqui antes de começar dimensões.
>
> **Princípios:**
> - Honestidade analítica, não bajulação. Reportar bugs como bugs.
> - Toda correção precisa de regressão verde E smoke E2E real do caminho principal.
> - Documentar achados em `references/audits/audit-N-strategy.md` antes de tocar código.
> - Generalizar imediatamente — quando achar um bug, aplicar dim 1+2+3 antes de mover ao próximo.
>
> **Saída esperada:**
> - Relatório com achados priorizados (P0 crítico, P1 importante, P2/P3 refinamento).
> - Plano de N sprints fechados em uma única release consolidada (não múltiplas releases incrementais).
> - Análise meta: quais dimensões geraram achados, quais ficaram OK, e se a lista de 27 ainda está completa ou precisa expansão.

---

## Histórico do uso deste manual

| Auditoria | Versão | Dimensões com achados | Achados |
|---|---|---|---|
| #1 (improvisada) | v2.18.0 → v2.19.0 | DIM 1, 4, 6, 7, 21 | 17 |
| #2 (improvisada) | v2.19.0 → v2.20.0 | DIM 1, 4, 6 | 9 (2 introduzidos pela #1) |
| #3 (improvisada) | v2.20.0 → v2.21.0 | DIM 3, 4, 5, 7 | 13 |
| #4 (improvisada) | v2.21.0 → v2.22.0 | DIM 1, 5, 4 | 8 |
| #5 (improvisada) | v2.22.0 → v2.23.0 | DIM 2, 5, 7, 18 | 6 (1 introduzido pela #4) |
| #6+ | v2.23.0+ | usar **este manual** | esperado: convergência |

## Reflexão final

Os 27 itens são o estado atual do conhecimento. **Auditoria #6 que use este manual e ache bugs em dimensões não listadas indica gap deste documento** — atualizar este arquivo nesse caso.

Sistemas de software não convergem para "zero bugs" — convergem para "bugs apenas nas dimensões ainda não conceitualizadas". Este manual é uma **vacina contra reaprendizado**: futuras auditorias não precisam redescobrir as dimensões que já conhecemos.
