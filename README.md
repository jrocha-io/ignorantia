# ignorantia

> Construção de revisões sistemáticas de literatura (SLR) PRISMA-2020 do mais alto nível, com saída em HTML interativo auto-contido, versionada e auditável.

**Versão:** 2.23.0 · **Status:** estável (cobertura premium completa; pipeline integra preâmbulo contextual; schema unificado mock vs real; source_tier Liskov-conforme; USER_AGENT centralizado; orquestrador gera summary; pipeline com registry de steps)

**Estado quantitativo:** 62 adapters de busca · 57 TIER1_RUNNERS · 7 áreas · 16 paywall com cascata legal · 6 etapas no pipeline_finalize · 13 DDs (todas implementadas) · 33 decisões editoriais · 359+ testes regressão verde.

Ver `SKILL.md` para entry point ao Claude, `CHANGELOG.md` para histórico SemVer, `journal.txt` para log cronológico de desenvolvimento, e `references/` para documentação operacional (decisões editoriais, modos hierárquicos, perfis de venues, auditorias iterativas, plano v3.0.0).

## O que é

`ignorantia` é uma skill executada pelo Claude (Anthropic) que conduz uma SLR completa, do protocolo pré-registrado ao manuscrito final. O ponto de partida é a **ignorância declarada do usuário** sobre um tema — o resultado é um artigo do mais alto nível, reprodutível e auditável.

## Arquitetura (v2.23.0)

- **Domain-aware**: 7 áreas (saúde, educação, cs_se, ciências sociais, humanidades, business, multi).
- **62 adapters de busca** com schema canônico unificado (mock = real, source_tier Liskov-conforme).
- **6 etapas pipeline** com registry Open/Closed (`PIPELINE_STEPS`).
- **3 renderers**: chunks (canônico, HTML interativo D3), docx (ABNT), latex (PDF).
- **Cascata paywall legal**: KEY → PROXY → FALLBACK_MD → MOCK em 16 adapters premium.
- **Decisão 22 (reproducibility manifest)** + **DD-10 (logs em duas camadas)**.

## Princípios

- **Honestidade epistêmica**: skill nunca inventa dados; falhas são declaradas.
- **Rigor metodológico**: PRISMA-2020 executado, não apenas citado.
- **Imutabilidade SemVer**: cada saída é versão fechada.
- **Auditabilidade total**: toda referência tem link clicável; manifest reproducibility versiona dependências e fixtures.
- **Engajamento do leitor**: forma e fundo importam — HTML interativo com gráficos D3.js, filtros, anotações, dark mode.

## Plano v3.0.0

Clean Architecture/DDD/bounded contexts/ports & adapters detalhado em `references/V3_ARCHITECTURE_PLAN.md`. TDD estrito, mypy --strict, cobertura ≥90% em domain. Cowork adiado para v4.

## Manual de auditoria

`references/audits/AUDIT_PROCEDURE.md` documenta 27 dimensões de erro em 7 camadas (correção, convenções, especificação, reprodutibilidade, compatibilidade, segurança, lifecycle). Auditoria sistemática que substitui ~5 rodadas improvisadas.

## Licença

CC-BY-4.0 (default).

## Citação sugerida

> Skill `ignorantia` v2.23.0 (2026). Anthropic Claude. Sprint formal de calibração empírica documentado em `references/whitepaper-sprint-badge-calibration.md`.
