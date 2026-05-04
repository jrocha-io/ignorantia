# Modo 03 — AI-Assisted Systematic Mapping Study

> Camada hierárquica: **PRIMÁRIA** (você sozinho + pesquisa bibliográfica autônoma).

## Caso de uso

Mapeamento sistemático de literatura em CS/SE com classificação categórica em múltiplas dimensões. Apropriado para identificar gaps de pesquisa e mapear estado da arte em campo emergente. Padrão de fato em IEEE TSE, ACM TOSEM, EMSE, IST.

## Layer 1 — Modo

| Dimensão | Especificação |
|---|---|
| **review_type** | `mapping_study` |
| **Reporting guideline primário** | ACM SIGSOFT Empirical Standards (Systematic Review) |
| **Reporting guideline secundário** | Petersen et al. 2008/2015; Kitchenham guidelines (alternativa) |
| **Camada hierárquica** | Primária |
| **Tempo típico de produção** | `user_estimate_15min_unvalidated` |
| **Selo HTML** | `mode-mapping` (roxo) |

## Layer 2 — Reporting guideline

| Dimensão | Especificação |
|---|---|
| **Itens checklist (SIGSOFT)** | 15 itens |
| **Revisores humanos** | 1 (single-reviewer com AI verification aceito por ESS-6) |
| **Pré-registro** | OSF recomendado |
| **Threats to Validity (ESS-14)** | OBRIGATÓRIO 4 tipos: construct, internal, external, conclusion |
| **Replication Package (ESS-15)** | OBRIGATÓRIO |

### Declarações e seções obrigatórias

- Research questions explícitas (RQ1, RQ2, RQ3...) com PICOC ou GQM
- Search string per library (≥3 libraries)
- Snowballing forward+backward (ESS-5)
- Classification scheme bottom-up ou top-down explicitado
- Threats to Validity (4 tipos)
- Replication Package em Zenodo/OSF/GitHub
- AI Disclosure + Funding + COI

## Layer 3 — Venue padrão e alternativas (OA-first)

### Padrão (OA-gratuito, $0 APC)

**Zenodo + arXiv (cs.SE)** + replication package em GitHub. Sem peer review formal mas com DOI persistente e visibilidade alta na comunidade SE.

### Alternativas Qualis BR ($0 APC)

- **Journal of the Brazilian Computer Society (JBCS/SBC)** — A2 BR (não A1, mas único representativo BR em CS), Springer, hybrid (~$1990 APC).
- **JISTEM (USP)** — A2 BR, OJS, $0, EN/PT.
- **Revista Brasileira de Informática na Educação (RBIE)** — B1 BR, $0, PT/EN, especialmente para Mapping Studies em educational technology.

### Alternativas internacionais (peer review hybrid/paywall)

- **IEEE TSE** — Q1, hybrid (~$2500 APC para OA), padrão-ouro CS/SE.
- **ACM TOSEM** — Q1, hybrid, alta visibilidade ACM.
- **Empirical Software Engineering (Springer)** — Q1, hybrid, padrão SE empírico.

## Bases de busca recomendadas

Mínimo: **3 digital libraries** (ESS-3).

Tier 1 (OA, sempre):
- **arXiv (cs.SE/cs.PL/cs.HC)** — Tier 1, $0
- **DBLP** — Tier 1 (metadados livres), $0

Tier 2 (metadados livres):
- **ACM Digital Library** (subset OA disponível; Tier 2-3 conforme)
- **IEEE Xplore** (subset OA; Tier 2-3 conforme)
- **SpringerLink** (subset OA)

Tier 3 (apenas via material fornecido pelo usuário):
- Scopus, WoS, Elsevier ScienceDirect

## Estudos primários esperados

Tipicamente **50-300 estudos incluídos**. Mapping studies são por natureza amplas — número alto é esperado e desejável.

## Custos para o usuário

- **APC**: $0 (Zenodo + arXiv)
- **Software**: opcional
- **Bases pagas**: não exigidas para Tier 1+2; Tier 3 só via institucional do usuário

## Limitações declaradas

- Single-reviewer com AI verification (não substitui 2 revisores humanos).
- Mapping é categórico-descritivo, não meta-analítico.
- Classificação bottom-up sujeita a vieses do classificador.

## Quando NÃO usar

- Saúde com mistura quanti/quali → Modo 9 (Integrative Review)
- Sem foco classificatório → Modo 1 (Scoping)
- Exige meta-análise → Modo 4 (SR estrito)
