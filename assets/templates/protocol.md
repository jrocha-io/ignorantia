# Protocolo de Revisão Sistemática — Template

**Título:** [Título da SLR]
**Autores:** [Nome 1, Nome 2, ...]
**Versão:** 1.0
**Data:** [DD/MM/AAAA]
**Pré-registro:** [Zenodo / OSF / PROSPERO — adicionar DOI após upload]
**Metodologia:** PRISMA 2020 [+ Kitchenham guidelines, se SE]

---

## 1. Contexto e justificativa

[2–4 parágrafos. Motivar por que a SLR é necessária: lacunas no conhecimento, ausência de revisões anteriores, mudanças recentes no campo. Citar revisões existentes próximas ao tema e explicar como esta difere/complementa.]

## 2. Pergunta de pesquisa

**RQ principal:** [Pergunta única, específica, respondível.]

Decomposição PICO/PICOC:

| Componente | Especificação |
|------------|---------------|
| **P**opulação / problema | |
| **I**ntervenção / objeto de estudo | |
| **C**omparação | (se aplicável) |
| **O**utcome / desfecho | |
| **C**ontexto | (PICOC apenas) |

**Sub-perguntas (opcional):**
- RQ1.1: [...]
- RQ1.2: [...]

## 3. Bases de dados

Lista finita e fechada antes da execução. **Qualquer base adicionada após esta data invalida a pré-registro.**

| Base | Tipo | Acesso | Modo de execução |
|------|------|--------|------------------|
| arXiv | Preprint | Aberto | Direto via API |
| Semantic Scholar | Multidisc. | Aberto | Direto via API |
| dblp | CS bibliográfico | Aberto | Direto via API |
| Crossref | Multidisc. | Aberto | Direto via API |
| ACM Digital Library | CS | Híbrido | Direto + guiado |
| IEEE Xplore | Eng./CS | [Institucional] | Guiado |
| Scopus | Multidisc. | [Institucional] | Guiado |
| Web of Science | Multidisc. | [Institucional] | Guiado |
| SciELO | Multidisc. (Iberoam.) | Aberto | Direto |
| BDTD | Teses BR | Aberto | Direto |
| Google Scholar | Multidisc. | Aberto | Guiado |
| [Outras] | | | |

Justifique a inclusão de cada base. Se uma base canônica do tema foi excluída, justifique também.

## 4. Strings de busca

Uma string por base, na sintaxe da base. Versões abaixo derivam dos termos PICOC + sinônimos.

**Termos-chave:**
- Conceito 1: T1, T1', T1'', ...
- Conceito 2: T2, T2', T2'', ...
- Conceito 3: T3, T3', T3'', ...

### arXiv

```
(abs:"T1" OR abs:"T1'") AND (abs:"T2" OR abs:"T2'") AND submittedDate:[YYYYMMDDhhmm TO YYYYMMDDhhmm]
```

### Semantic Scholar

```
{"query": "T1 T2", "year": "YYYY-YYYY", "fieldsOfStudy": ["..."]}
```

### dblp

```
(T1|T1') (T2|T2') year:YYYY:YYYY type:Conference_and_Workshop_Papers|Journal_Articles
```

### IEEE Xplore (Advanced Search)

```
(("All Metadata":"T1" OR "All Metadata":"T1'") AND 
 ("All Metadata":"T2" OR "All Metadata":"T2'"))
```
Filters: Year YYYY–YYYY, Document Type: Conferences + Journals.

### Scopus

```
TITLE-ABS-KEY( ("T1" OR "T1'") AND ("T2" OR "T2'") ) 
   AND PUBYEAR > YYYY-1 AND PUBYEAR < YYYY+1 
   AND DOCTYPE(ar OR cp)
```

### Web of Science

```
TS=(("T1" OR "T1'") AND ("T2" OR "T2'")) AND PY=YYYY-YYYY 
   AND DT=(Article OR Proceedings Paper)
```

### SciELO

```
(T1_pt OR T1_pt') AND (T2_pt OR T2_pt') AND ano_cluster:("YYYY" OR ... OR "YYYY")
```

### Google Scholar

```
("T1" OR "T1'") ("T2" OR "T2'") -termoExcluído
```
Filtros: ano YYYY–YYYY; idioma se aplicável.

## 5. Critérios de inclusão (CI)

- **CI1:** [Tipo de estudo aceito, ex.: peer-reviewed empirical]
- **CI2:** [Período: YYYY–YYYY]
- **CI3:** [Idioma: PT-BR e/ou EN e/ou ES]
- **CI4:** [Domínio: estudo aborda diretamente RQ]
- **CI5:** [Disponibilidade do full-text]
- **CI6:** [...]

## 6. Critérios de exclusão (CE)

- **CE1:** Tutorial, editorial, opinião sem dados primários.
- **CE2:** Resumo expandido sem manuscrito completo.
- **CE3:** Estudo não pertinente à RQ (mesmo termos coincidindo).
- **CE4:** Duplicata.
- **CE5:** Versão preliminar de paper depois publicado em venue mais maduro.
- **CE6:** Score < X em quality appraisal.
- **CE7:** [...]

## 7. Quality appraisal

**Instrumento:** [DARE | CASP | Kitchenham QA1–QA5 | Dyba-Dingsoyr 11Q | outro]

[Listar as questões QA1...QAN explicitamente. Escala (0/0.5/1 ou 0/1). Threshold para inclusão na síntese.]

## 8. Formulário de extração de dados

Campos a extrair de cada estudo incluído:

- ID interno (S01, S02, ...)
- Citação completa (na norma do projeto)
- DOI / URL
- Ano
- Venue / periódico
- Tipo de estudo (empírico, teórico, revisão, ...)
- País / contexto
- População / amostra
- Intervenção / objeto
- Comparador
- Outcomes / achados primários
- Métodos / design
- Limitações declaradas pelos autores
- QA score
- RQ que o estudo responde
- Notas do revisor

## 9. Procedimento de seleção

1. Execução das buscas em todas as bases listadas em data ÚNICA (registrar data por base).
2. Exportação para gerenciador (Zotero / Mendeley / planilha).
3. Deduplicação por DOI > título normalizado > primeiro autor + ano.
4. Screening de título/abstract por dois revisores independentes.
5. Resolução de conflitos: discussão; se persistir, terceiro revisor.
6. Cohen's kappa calculado e reportado.
7. Recuperação do full-text dos sobreviventes; OA via Unpaywall, restritos via instituição.
8. Screening full-text por dois revisores; mesma resolução de conflitos + kappa.
9. Quality appraisal por dois revisores; mesma resolução de conflitos + kappa.
10. Extração de dados por um revisor, conferida pelo segundo (full-coverage check).

## 10. Síntese

[Narrativa? Temática? Quantitativa/meta-análise? Justificar.]

Estratégia de agrupamento dos estudos: [por RQ, por intervenção, por domínio, ...].

## 11. Cronograma

| Fase | Início | Fim | Responsável |
|------|--------|-----|-------------|
| Protocolo | | | |
| Buscas | | | |
| Screening T/A | | | |
| Recuperação FT | | | |
| Screening FT | | | |
| QA | | | |
| Extração | | | |
| Síntese | | | |
| Redação | | | |
| Revisão | | | |
| Submissão | | | |

## 12. Equipe

- **Revisor 1:** [Nome, vínculo, papel]
- **Revisor 2:** [Nome, vínculo, papel]
- **Revisor de desempate:** [Nome]
- **Coordenador:** [Nome]

## 13. Disseminação

- Pré-registro: Zenodo / OSF (adicionar DOI quando obtido).
- Manuscrito: [periódico-alvo, conferência].
- Dados, scripts, planilhas: Zenodo (mesma comunidade).
- Licença: CC-BY-4.0.

## 14. Mudanças no protocolo

Qualquer alteração após o pré-registro deve ser registrada nesta seção com data, descrição e justificativa.

| Versão | Data | Mudança | Justificativa |
|--------|------|---------|---------------|
| 1.0 | | Protocolo inicial | — |
