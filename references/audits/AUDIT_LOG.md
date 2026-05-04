# Histórico de auditorias iterativas (B12, v2.21.0)

Cada auditoria é uma revisão crítica buscando bugs, lacunas, e estruturas inacabadas. Princípio: honestidade analítica, não bajulação.

| # | Versão auditada | Achados | Fixes | Release | Estratégia |
|---|---|---|---|---|---|
| 1 | v2.18.0 | 17 | 17 | v2.19.0 | [audit-1-strategy.md](audit-1-strategy.md) |
| 2 | v2.19.0 | 9 | 9 | v2.20.0 | [audit-2-strategy.md](audit-2-strategy.md) |
| 3 | v2.20.0 | 13 | 13 | v2.21.0 | [audit-3-strategy.md](audit-3-strategy.md) |
| 4 | v2.21.0 | 8 | 8 | v2.22.0 | [audit-4-strategy.md](audit-4-strategy.md) |
| 5 | v2.22.0 | 16 (D1-D6 + E1-E10) | 16 | v2.23.0 | [audit-5-strategy.md](audit-5-strategy.md) |

## Padrão observado

Cada auditoria detecta:
- Bugs introduzidos pela release anterior (auditoria #2 detectou 2 introduzidos pela v2.19.0)
- Lacunas pré-existentes que escaparam de auditorias anteriores (#3 detectou B1+B2: pipeline não propagava preâmbulo)
- Gaps declarativos (CHANGELOG diz X, código faz Y)

## Regra reforçada (auditoria #3)

**Integração ≠ implementação.** Testes verdes em renderers individuais não significam que o pipeline propaga os features. Por isso B13 introduziu testes E2E de subprocess que rodam `pipeline_finalize.py` completo.


## Manual de auditoria sistemática (criado após #5)

Após a auditoria #5 detectar que cada rodada estava descobrindo uma categoria nova de bugs (em vez de bugs novos da mesma categoria), foi criado **`AUDIT_PROCEDURE.md`** — manual com **27 dimensões** de auditoria conhecidas, organizadas em 7 camadas:

1. **Correção do código** (DIM 1-9): generalização lateral, paridade mock/real, integração E2E, paridade declarativa, schema canônico, edge cases, tratamento de erros, recursos, concorrência
2. **Convenções e nomenclatura** (DIM 10-12): convenções inconsistentes, versões hardcoded, defaults inconsistentes
3. **Especificação vs implementação** (DIM 13-16): decisões/DDs aplicadas, PRISMA-2020, profiles YAML, output validation
4. **Reprodutibilidade e auditabilidade** (DIM 17-19): reprodutibilidade, manifest, logs em camadas
5. **Compatibilidade e portabilidade** (DIM 20-22): encoding, paths, dependências
6. **Segurança e privacidade** (DIM 23-24): credentials, input validation
7. **Lifecycle e manutenção** (DIM 25-27): código morto, SemVer, meta-auditoria

Auditoria #6+ deve usar este manual em vez de improvisar. Se uma rodada encontra bugs em dimensões não listadas, atualizar `AUDIT_PROCEDURE.md`.

## Referências fora deste diretório

- `references/IMPLEMENTATION_STRATEGY.md` — estratégia macro de releases R1-R8 + auditorias
- `journal.txt` — log cronológico humano-legível
- `CHANGELOG.md` — log SemVer estruturado
