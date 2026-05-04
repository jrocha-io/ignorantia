# Padrões de design do HTML interativo — ignorantia

Este documento define os padrões visuais e de interação do HTML que o skill produz. Consolidado a partir de duas referências do projeto: `parametros_especificacao_prompts_v1_0_0.html` (estrutura modular numerada, tiers, "limites declarados") e `prompt_engineering_reference_v3_IEEE_3.html` (tabela com filtros, blocos colapsáveis, referências numeradas com tooltip, meta-badges).

## Princípios

1. **Forma serve fundo.** Cada elemento visual existe para ajudar o leitor a entender, navegar ou auditar. Decoração sem função é ruído.
2. **Auditabilidade visível.** Toda referência leva à fonte primária em um clique. Toda decisão metodológica é localizável (busca, filtro, link).
3. **Anti-genérico.** Layout não pode parecer "PDF acadêmico padrão". A combinação tabela-filtrável + camada de anotações + dark mode + numeração explícita já cria identidade.
4. **Acessível.** Contraste WCAG AA mínimo. Navegação por teclado. `prefers-reduced-motion`. Toggles operáveis com ARIA.
5. **Auto-contido.** CSS e JS inline; D3.js v7 via CDN com URL única; nenhum recurso externo bloqueante. Funciona offline depois do primeiro carregamento.

## Estrutura macro

```
<header>           Logo "ignorantia" + título do artigo + subtítulo + badges (versão, idioma, data, área, framework)
<nav.toolbar>      Sticky. Busca | Filtros | Toggles
<main>
  <section §00>    Prólogo / Resumo estruturado
  <section §01>    Introdução
  <section §02>    Background & Theoretical Framework
  <section §03>    Methodology
  <section §04>    Results — descritivos + PRISMA flow + tabela interativa
  <section §05>    Synthesis by RQ
  <section §06>    Discussion / Design Guidelines
  <section §07>    Threats to Validity
  <section §08>    Conclusion & Future Work
  <section §09>    Box "O que esta versão NÃO é"
  <section §10>    References
<footer>           SemVer · Data · Hash · Zenodo DOI · Licença
```

Cada `<section>` tem ID estável (`#sec-00`, `#sec-01`, ...) e cabeçalho clicável que colapsa/expande o conteúdo. Estado de colapso persiste em `localStorage` quando disponível.

## Toolbar fixa

```html
<nav class="toolbar" aria-label="Controles do documento">
  <input type="search" id="q" placeholder="Buscar no manuscrito..." aria-label="Busca textual">
  <fieldset class="filters">
    <select id="filter-section">...</select>
    <select id="filter-rq">...</select>
    <select id="filter-year">...</select>
    <select id="filter-study-type">...</select>
  </fieldset>
  <fieldset class="toggles">
    <button id="toggle-annotations" aria-pressed="false">Anotações</button>
    <button id="toggle-dark" aria-pressed="false">Modo escuro</button>
    <button id="toggle-collapse-all" aria-pressed="false">Colapsar tudo</button>
  </fieldset>
</nav>
```

CSS: `position: sticky; top: 0; z-index: 20; background: var(--bg-primary)`. Borda inferior fina.

Busca: filtra em tempo real os parágrafos via marcação `<mark>` dos termos encontrados; rola para o primeiro hit. Esc limpa a busca.

## Paleta de cores e variáveis CSS

Definir paleta no `<style>` no topo do `<head>`, com variáveis que mudam quando `<html>` recebe `class="dark"`.

```css
:root {
  --bg-primary: #fafaf7;
  --bg-secondary: #f0efea;
  --bg-card: #ffffff;
  --text-primary: #1a1a1a;
  --text-secondary: #555;
  --text-muted: #888;
  --accent: #6b4eff;       /* púrpura ignorantia — pode ajustar por área */
  --accent-soft: #e8e4ff;
  --border: #d8d6d0;
  --border-strong: #aaa;
  --link: #4a3aff;
  --link-visited: #6b4eff;
  --hi: #c93a3a;           /* tier A / impacto alto */
  --med: #d68a1e;          /* tier B/C / impacto médio */
  --lo: #6e7780;           /* tier D/E / impacto baixo */
  --good: #2c8a4f;
  --bad: #c93a3a;
  --annotation-bg: #fff8d4;
  --annotation-border: #d4ba1e;
  --code-bg: #f4f1eb;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
}

html.dark {
  --bg-primary: #14141a;
  --bg-secondary: #1c1c24;
  --bg-card: #1e1e26;
  --text-primary: #e8e6e0;
  --text-secondary: #b0aea8;
  --text-muted: #888;
  --accent: #9b85ff;
  --accent-soft: #2a235c;
  --border: #2e2e38;
  --border-strong: #555;
  --link: #aab8ff;
  --link-visited: #c2b8ff;
  --annotation-bg: #2a2515;
  --annotation-border: #6e5e1e;
  --code-bg: #20202a;
  --shadow: 0 1px 3px rgba(0,0,0,.4);
}
```

Cor de **acento** pode ser ajustada por área disciplinar — ex. verde para saúde, azul para CS, ocre para humanidades. Definir por slug de área.

## Numeração de seções

Cada cabeçalho de seção segue o padrão dos documentos de referência:

```html
<section id="sec-03">
  <header class="section-head">
    <span class="section-num">§ 03</span>
    <h2>Methodology</h2>
    <button class="section-collapse" aria-expanded="true" aria-controls="sec-03-body">−</button>
  </header>
  <div id="sec-03-body" class="section-body">
    ...
  </div>
</section>
```

`.section-num` é monoespaçada, em destaque. `<h2>` em peso normal mas tamanho maior.

## Tiers / categorias coloridas

Quando o conteúdo se beneficia de classificação (estudos por tipo, técnicas por categoria, RQ por dimensão), usar **badges** com cor por tier:

```html
<span class="badge badge-tier-a">Tier A · Forma literal</span>
<span class="badge badge-rq1">RQ1</span>
<span class="badge badge-qa-9">QA: 9/10</span>
```

CSS:

```css
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
         font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
         text-transform: uppercase; }
.badge-tier-a { background: var(--hi); color: white; }
.badge-tier-b { background: var(--med); color: white; }
.badge-tier-c { background: #4a78c9; color: white; }
.badge-tier-d { background: var(--good); color: white; }
.badge-tier-e { background: var(--lo); color: white; }
.badge-rq1, .badge-rq2, .badge-rq3, .badge-rq4, .badge-rq5 {
  background: var(--accent-soft); color: var(--accent);
}
.badge-qa-9, .badge-qa-10 { background: var(--good); color: white; }
.badge-qa-7, .badge-qa-8 { background: #4a78c9; color: white; }
.badge-qa-5, .badge-qa-6 { background: var(--med); color: white; }
.badge-qa-low { background: var(--lo); color: white; }
```

## Tabela de estudos incluídos

Render a partir de `extraction.csv`. Colunas mínimas:

| ID | Citação | Ano | Venue | Frameworks | Métodos | RQs | QA |

Recursos:

- **Sticky header** ao rolar.
- **Sort** por click no cabeçalho (toggle asc/desc, indicador visual).
- **Filtro multi-coluna** via inputs/selects abaixo do header (ou na toolbar global).
- **Linha clicável** abre detalhe expandido com extração completa daquele estudo (modal ou detalhe inline).
- **Highlight de QA** colorindo a célula conforme score.
- **DOI clicável** na coluna ID/Citação leva à fonte.

```html
<div class="table-wrap">
  <table id="studies">
    <thead>
      <tr>
        <th data-sort="id">ID</th>
        <th data-sort="cite">Estudo</th>
        <th data-sort="year">Ano</th>
        <th data-sort="venue">Venue</th>
        <th data-sort="frameworks">Frameworks</th>
        <th data-sort="methods">Métodos</th>
        <th data-sort="rqs">RQs</th>
        <th data-sort="qa">QA</th>
      </tr>
      <tr class="filters-row">
        <th></th>
        <th><input type="search" data-col="cite" placeholder="filtrar..."></th>
        <th><select data-col="year">...</select></th>
        ...
      </tr>
    </thead>
    <tbody>
      <tr data-id="S01" data-rqs="rq1,rq2" data-qa="10">
        <td>S01</td>
        <td><a href="https://doi.org/10.1109/TVCG.2011.185">Bostock et al. (2011)</a></td>
        <td>2011</td>
        <td>TVCG</td>
        <td><span class="badge">D3</span></td>
        <td>Notational efficiency</td>
        <td><span class="badge badge-rq1">RQ1</span> <span class="badge badge-rq2">RQ2</span></td>
        <td><span class="badge badge-qa-10">10</span></td>
      </tr>
      ...
    </tbody>
  </table>
</div>
```

## Referências numeradas com tooltip

In-text: `<a class="ref" href="#ref-12" data-ref="12">[12]</a>`.

Lista de referências:

```html
<section id="sec-references">
  <header class="section-head">...References...</header>
  <ol class="references">
    <li id="ref-12">
      Munzner, T. (2014). <em>Visualization analysis and design</em>. CRC Press.
      <a class="ref-link" href="https://www.crcpress.com/9781466508910" rel="external">↗</a>
    </li>
    ...
  </ol>
</section>
```

JS popula um Map<num, html-da-li>. Hover em `.ref` mostra tooltip via CSS (`::after` com `attr(data-tooltip)`) ou via JS criando um `<div class="tooltip">` posicionado.

Click na referência rola até a entry e a destaca por 2s (`.target { animation: pulse 2s; }`).

Toda referência com DOI **deve** ter URL completa e clicável (`https://doi.org/10.xxxx/yyyy`). Toda referência arXiv **deve** ter URL `https://arxiv.org/abs/XXXX.XXXXX`. Toda referência com URL canônica de fonte primária **deve** linkar à fonte.

## Camada de anotações estilo professor

Anotações são comentários laterais que aparecem por toggle. São o equivalente das marcas de caneta vermelha no trabalho de um aluno — conexões, perguntas, observações que fazem o leitor pensar.

```html
<p class="annotated" data-annotation-id="ann-3">
  ... Munzner's What/Why/How decomposition... is most often invoked at two specific D3 layers ...
</p>

<aside class="annotation" id="ann-3" data-anchor="annotated:nth(3)">
  <span class="annotation-author">— Prof.</span>
  Atenção: o artigo de Munzner (2014) cobre <em>What</em>, <em>Why</em>, <em>How</em> em três camadas distintas, mas os papers do corpus
  reduzem a decomposição a duas. Vale ler também Brehmer & Munzner (2013) para a tipologia completa.
</aside>
```

CSS:

```css
.annotation { display: none; }
html.show-annotations .annotation {
  display: block;
  position: absolute;
  right: -300px;
  width: 280px;
  background: var(--annotation-bg);
  border-left: 3px solid var(--annotation-border);
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.4;
  font-family: "Caveat", "Patrick Hand", cursive;  /* opcional, para "feel" de manuscrito */
  box-shadow: var(--shadow);
}
@media (max-width: 1100px) {
  html.show-annotations .annotation {
    position: static;
    margin: 8px 0;
    border-left: none;
    border-top: 3px solid var(--annotation-border);
  }
}
```

Toggle: `document.documentElement.classList.toggle('show-annotations')`.

JS deve calcular posição vertical do `<aside>` baseado no `<p data-annotation-id>` âncora — usar `getBoundingClientRect` no toggle on, e ao redimensionar.

Anotações podem ter sub-tipos por cor:

- **observação** (amarelo padrão)
- **conexão** (verde claro) — "isto se relaciona com §05"
- **pergunta** (azul claro) — "quem testou isto em 2025+?"
- **alerta** (vermelho claro) — "amostra pequena, generalização frágil"

```html
<aside class="annotation annotation-conexao" ...>
```

## Dark mode

Toggle:

```js
function toggleDark() {
  const root = document.documentElement;
  const isDark = root.classList.toggle('dark');
  try { localStorage.setItem('ignorantia-dark', isDark ? '1' : '0'); } catch(e) {}
  document.querySelectorAll('[aria-pressed]').forEach(b => {
    if (b.id === 'toggle-dark') b.setAttribute('aria-pressed', isDark);
  });
}
// On load
try {
  if (localStorage.getItem('ignorantia-dark') === '1') {
    document.documentElement.classList.add('dark');
  } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.classList.add('dark');
  }
} catch(e) {}
```

Em ambientes onde `localStorage` não está disponível (alguns sandboxes de artifact), o try/catch cai silenciosamente e o estado fica em memória.

## D3.js — gráficos a embutir

Sempre incluir:

1. **PRISMA flow diagram** — gerado por `scripts/prisma_flow.py` como SVG inline. NÃO requer D3 em runtime.
2. **Distribuição temporal** dos estudos incluídos — bar chart ou histograma com escala temporal.
3. **Heatmap de QA** — eixo Y: estudos; eixo X: questões QA1–QA5/8; cor: score 0/0.5/1. Permite ver padrões de qualidade.
4. **Matriz framework × RQ** — quais frameworks teóricos são invocados em cada RQ, intensidade pela contagem.

Gráficos opcionais conforme natureza:

5. **Rede de co-citação** — `d3-force` com nós = estudos, arestas = co-citações. Para corpus suficientemente conectado.
6. **Sankey de fluxo** identificação → screening → incluídos por base — `d3-sankey`.
7. **Treemap por venue ou domínio** — `d3-hierarchy.treemap`.

Padrão de embutir:

```html
<figure id="fig-temporal">
  <figcaption>Figura 1. Distribuição temporal dos estudos incluídos.</figcaption>
  <div id="chart-temporal"></div>
</figure>

<script>
  const data_temporal = [{"year":2007, "n":3}, {"year":2008, "n":2}, ...]; // pre-renderizado
  // D3 code para bar chart
</script>
```

Os dados são **pre-renderizados** no HTML — não dependem de fetch externo. O HTML viaja com seus dados.

D3.js v7 via CDN único, com integrity hash:

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7" integrity="..." crossorigin="anonymous"></script>
```

## Tipografia

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto",
               "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  max-width: 820px;            /* leitura confortável */
  margin: 0 auto;
  padding: 24px 32px;
}
h1 { font-size: 28px; font-weight: 700; line-height: 1.2; margin: 0 0 8px; }
h2 { font-size: 22px; font-weight: 600; }
h3 { font-size: 18px; font-weight: 600; }
.section-num { font-family: "JetBrains Mono", "Menlo", "Consolas", monospace;
               font-size: 14px; color: var(--text-muted);
               text-transform: uppercase; letter-spacing: 0.05em; }
code, pre { font-family: "JetBrains Mono", "Menlo", "Consolas", monospace;
            background: var(--code-bg); border-radius: 3px;
            padding: 2px 4px; font-size: 14px; }
pre { padding: 12px; overflow-x: auto; }
```

Em layouts com camada de anotações ativa, expandir o `max-width` para 1100px e reservar coluna direita para `.annotation`.

## "Box O que esta versão NÃO é"

Bloco fixo ao final do método (antes de Resultados ou imediatamente antes das Referências), no estilo do v1.0.0 de parametros_especificacao_prompts:

```html
<div class="not-this-version">
  <h3>O que esta versão NÃO é</h3>
  <ul>
    <li>Não é uma metanálise quantitativa — heterogeneidade do corpus desaconselha pooling.</li>
    <li>Não inclui literatura cinzenta (white papers, blog posts) salvo quando explicitamente referenciada por estudos peer-reviewed.</li>
    <li>Não simula segundo revisor; o cálculo de Cohen's kappa é responsabilidade da revisão humana posterior.</li>
    <li>Não cobre publicações em chinês ou japonês — limitação do skill no idioma de busca.</li>
  </ul>
</div>
```

Estilo: borda esquerda destacada, fundo levemente diferente, sem ser intimidante.

## Acessibilidade

- Contraste mínimo WCAG AA: 4.5:1 para texto normal, 3:1 para texto grande/elementos UI.
- Toda função alcançável por teclado: Tab, Enter, Space, setas para tabela.
- ARIA: `role`, `aria-label`, `aria-pressed`, `aria-expanded` corretos.
- `prefers-reduced-motion: reduce` desliga transições de colapso e D3 animations.
- Imagens (gráficos D3 SVG) com `<title>` e `<desc>`. PRISMA flow gerado já tem `<text>` legível.
- Skip-links no topo: "Pular para conteúdo", "Pular para tabela de estudos", "Pular para referências".

## Footer canônico

```html
<footer>
  <p>
    <strong>ignorantia</strong> · v1.0.0 · 2026-04-28 · pt-BR · ABNT
    · <a href="https://doi.org/10.5281/zenodo.XXXXXXX">Zenodo DOI</a>
    · <a href="LICENSE">CC-BY-4.0</a>
    · <span title="SHA-256 do HTML">hash: a3f2c8…</span>
  </p>
  <p>
    Versão anterior: <a href="https://doi.org/10.5281/zenodo.YYYYYYY">v0.0.0 (rascunho)</a> ·
    Próxima versão prevista: v1.1.0 (após snowballing forward)
  </p>
</footer>
```

## Fonte do tema visual

A combinação macro = manuscrito acadêmico clássico (numeração de seções, tipografia legível, max-width controlado) + UI moderna (toolbar sticky, badges, filtros, dark mode, anotações tipo Hypothesis) + D3.js inline. O leitor sente que está lendo um artigo sério mas explorando um documento vivo.
