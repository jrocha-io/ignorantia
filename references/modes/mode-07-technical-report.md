# Modo 07 — Technical Report

> Camada hierárquica: **SECUNDÁRIA** (você sozinho + dados/processos/métodos fornecidos).

## Caso de uso

Documento técnico padronizado documentando dados, processos, métodos, ou descobertas internas. Sem peer review formal mas com DOI persistente quando depositado em Zenodo/arXiv. Audiência: indústria, comunidade técnica, formuladores de política, pesquisa futura.

## Layer 1 — Modo

| Dimensão | Especificação |
|---|---|
| **review_type** | `technical_report` |
| **Reporting guideline primário** | ANSI/NISO Z39.18-2005 (R2010) |
| **Camada hierárquica** | Secundária |
| **Tempo típico de produção** | `user_estimate_15min_unvalidated` |
| **Selo HTML** | `mode-technical-report` (cinza-azulado) |

## Layer 2 — Reporting guideline (ANSI/NISO Z39.18)

| Dimensão | Especificação |
|---|---|
| **Itens checklist** | 14 itens |
| **Revisores humanos** | 1 (autor; revisão interna institucional opcional) |
| **AI Disclosure** | OBRIGATÓRIO |
| **Comprimento** | variável (10-100 páginas tipicamente) |
| **Section 508** | recomendado se depósito EUA |

### Pré-requisitos

- Dados/processos/métodos prontos para documentar
- Audiência alvo declarada
- Decisão sobre destino do depósito

### Estrutura obrigatória ANSI/NISO Z39.18

1. Cover/Title page
2. Abstract (200-500 palavras)
3. Keywords (máx 10)
4. Executive Summary (recomendado para tomadores de decisão)
5. Introduction (background, scope, audience)
6. Methodology
7. Results / Findings
8. Discussion
9. Conclusion
10. Recommendations (obrigatório se prescritivo)
11. References
12. Appendices (recomendado: dados brutos, scripts)
13. AI Disclosure (OBRIGATÓRIO)

## Layer 3 — Venue padrão e alternativas (OA-first)

### Padrão (OA-gratuito, $0 APC)

**Zenodo** (Technical Report category):
- $0 APC, DOI persistente
- Sem peer review tradicional (revisão interna apenas)
- Neutralidade institucional
- Indexado pelo Google Scholar e OpenAIRE

### Alternativas

- **arXiv** (cs.SE/cs.HC/cs.CY conforme área): $0, alta visibilidade comunidade CS, sem peer review
- **OSF Preprints**: $0, integra com OSF Registries
- **NIST Technical Series**: apenas autores afiliados ao NIST
- **Repositório institucional do autor**: para vínculos universitários

## Bases de busca

Variável conforme tópico do relatório. Para technical reports descritivos (documentando processo interno), busca bibliográfica é mínima ou não-aplicável. Para technical reports analíticos, segue as mesmas bases Tier 1+2 dos modos primários.

## Estudos primários esperados

Variável. Não há mínimo formal — depende da natureza do relatório.

## Custos para o usuário

- **APC**: $0 (Zenodo/arXiv/OSF)
- **Software**: nenhum
- **Tempo**: depende do volume de dados/processos a documentar

## Limitações declaradas

- Não é peer-reviewed (não pode ser citado como evidência peer-reviewed).
- DOI persistente garante citabilidade mas não chancela acadêmica.

## Quando NÃO usar

- Conteúdo prescritivo dirigido a policymakers → Modo 8 (White Paper)
- Documento sobre software → Modo 5 (Software Paper)
- Argumentação filosófica → Modo 6 (Position Paper)
- Síntese sistemática de literatura → modos primários (1-3, 9, 10)
