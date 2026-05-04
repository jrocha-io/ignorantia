# Modo 08 — White Paper / Policy Brief

> Camada hierárquica: **SECUNDÁRIA** (você sozinho + problema + recomendações fornecidas).

## Caso de uso

Documento prescritivo dirigido a formuladores de política pública, indústria, sociedade civil. Combina síntese de evidência relevante com recomendações acionáveis. Audiência primária NÃO é academia peer-reviewed — é tomadores de decisão.

## Layer 1 — Modo

| Dimensão | Especificação |
|---|---|
| **review_type** | `white_paper` (alias: `policy_brief`) |
| **Reporting guideline primário** | WHITE-PAPER-GENERIC (Brookings/RAND/Carnegie/ICCT-style) |
| **Camada hierárquica** | Secundária |
| **Tempo típico de produção** | `user_estimate_15min_unvalidated` |
| **Selo HTML** | `mode-white-paper` (bege institucional) |

## Layer 2 — Reporting guideline (WHITE-PAPER-GENERIC)

| Dimensão | Especificação |
|---|---|
| **Itens checklist** | 13 itens |
| **Revisores humanos** | 1 (autor); peer review formal não exigido |
| **AI Disclosure** | OBRIGATÓRIO |
| **Comprimento** | 4-30 páginas (Policy Briefs ~4 págs; White Papers ~10-30 págs) |

### Pré-requisitos (declarações iniciais do usuário)

- Problema de política pública abordado
- Audiência alvo específica (federal/estadual/municipal/indústria/sociedade civil)
- Recomendações principais
- Limitações reconhecidas

### Estrutura obrigatória

1. **Executive Summary (1 página máximo — assinatura do formato)**
2. Background / Problem Statement
3. Findings (síntese de evidência relevante)
4. **Policy Recommendations (prescritivas, acionáveis, com ator + timeframe)**
5. Target audience explicit
6. **Limitations (OBRIGATÓRIO — sem isso vira propaganda)**
7. References (mistura: peer-reviewed + relatórios + dados oficiais)
8. AI Disclosure
9. Funding + COI declarados
10. Plain Language Summary (recomendado)

## Layer 3 — Venue padrão e alternativas (OA-first, ALL FREE)

White Papers são por natureza coerentes com OA-first — o objetivo é alcance, não chancela acadêmica.

### Padrão (OA-gratuito, $0 APC)

**Zenodo** (White Paper / Policy Brief category):
- $0, DOI persistente, neutralidade institucional
- Indexado pelo OpenAIRE, Google Scholar
- Versionável (v1 → v1.1 → v2 conforme atualização da posição)

### Alternativas (também $0)

- **OSF Preprints (Policy section)**: $0, integra com OSF Registries
- **SciELO Preprints**: $0, alta visibilidade Latam — especialmente para temas brasileiros
- **SSRN (Public Policy Network)**: $0, alta visibilidade ciências sociais e política pública
- **Repositório institucional do autor**: para uso interno organizacional ou universitário

Nenhuma alternativa exige APC.

## Bases de busca

Mínimo: **1-3 bases + grey literature** (Tier 1).

- **Saúde**: PubMed Central + LILACS + relatórios OMS/Banco Mundial/ANVISA
- **Educação**: ERIC OA + SciELO + relatórios UNESCO/OECD/INEP/MEC/BNCC
- **Tecnologia**: arXiv + relatórios NIST/W3C/ITU-T/ITU-R
- **Política pública geral**: SSRN + relatórios think tanks (Brookings, RAND, Carnegie, IPEA, FGV)

10-30 fontes citadas tipicamente, com mistura honesta de tipos.

## Estudos primários esperados

**Não aplicável** como número rígido. White Paper sintetiza evidência seletivamente para fundamentar recomendações.

## Custos para o usuário

- **APC**: $0 em todas as alternativas listadas
- **Software**: nenhum
- **Tempo**: trabalho intelectual humano predominante (formulação de recomendações)

## Caso particular do projeto base

White Paper é o **formato natural** para o caso "IA e jogos educacionais não substituem professor" do projeto:
- Audiência: formuladores de política educacional brasileira (MEC, Secretarias estaduais/municipais, gestores escolares)
- Versão PT-BR em SciELO Preprints + Zenodo
- Versão EN possivelmente em SSRN para visibilidade internacional
- Combinação com Modo 10 (Realist Review) prévio para fundamentar recomendações

## Limitações declaradas (OBRIGATÓRIO)

- Não é peer-reviewed.
- Não pode ser citado como evidência primária peer-reviewed.
- Não reivindica status de "consenso científico".
- Limitações de escopo (geográfico, temporal, populacional) explícitas.
- Limitações da base de evidência consultada (apenas OA? até data X?).

## Quando NÃO usar

- Documento descritivo sem prescrição → Modo 7 (Technical Report)
- Argumentação filosófica acadêmica → Modo 6 (Position Paper) com submissão a venue peer-reviewed
- Síntese sistemática de evidência → modos primários (1-3, 9, 10) — pode preceder o White Paper
