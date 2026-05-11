# Quality rubric — historical removed criteria (developer-only)

This is the "Critérios removidos da rubrica" section cut from
`references/quality-rubric.xml` during Fix 20 audience-separation. The
table carried `Decisão N`, `RS-42 v1.0.0` and version-trajectory
references that leaked developer history into the operator surface.

The operator (Claude scoring a manuscript against the rubric) needs
only the CURRENT criteria — the rationale for *why* old criteria were
removed across versions is engineering history.

---

## Critérios removidos da rubrica (v2.8.0 e posteriores)

Auditoria do RS-42 v1.0.0 identificou critérios que penalizavam o autor por
situações que não são lacunas reais de qualidade. Os seguintes critérios
foram **removidos** da rubrica:

| Critério antigo | Razão da remoção |
|---|---|
| **"Spot-check humano nas exclusões da Fase 4 não foi conduzido"** (D1) | Decisão 21: ao prosseguir do screening para a extração, o autor já está aceitando as exclusões; auditoria separada é redundante. O `reproducibility_manifest.yaml` registra `phase4_exclusions_review: implicit_consent` automaticamente. |
| **"Vinculação bidirecional Zenodo ↔ projeto subjacente é Categoria B"** (D2) | Decisão editorial pós-depósito, fora do escopo do skill. O skill não tem como avaliar isso porque acontece após a entrega do pacote. |
| **"Bases Tier 3 (Scopus, WoS, IEEE Xplore subset, Embase) não consultadas"** como lacuna a aceitar | Reescrito na v2.9.0 (Decisão 24): essas bases passam a ser **prioridade 0** via Tier 0 routing (Unpaywall + OAB + CORE + CAFe + gap report). Não-consulta deixa de ser "limitação aceitável" e vira erro de configuração quando o usuário tinha como acessar. |
| **"SciELO direto deveria ter sido consultado"** como limitação aceita | Reescrito na v2.9.0 (Decisão 25): SciELO + LA Referencia + Redalyc + CLACSO + BDTD + Scioteca + DOAJ + Periódicos CAPES + LILACS/BVS são **obrigatórias** na pesquisa pt-BR/es-LA. Não-consulta é defeito, não limitação. |
| **"Apenas X% dos elegíveis foram extraídos com profundidade"** | Decisão 26 (v2.9.0): todo elegível recebe extração com mesmo rigor de SR, independente do modo. Esse critério deixa de existir. |
| **"Idiomas restritos a EN/PT/ES"** | EN+PT+ES é **obrigação** da skill (Decisão 27, v2.9.0), não limitação a declarar. Critério removido. |
| **"Gráficos D3.js dinâmicos não implementados"** (D5) | Removido: visualização interativa não é evidência de mérito científico. |
| **"Camada de rabiscos for fun não implementada"** (D5) | Decisão 30 (v2.8.0): feature foi removida da skill. Critério já não se aplica. |
| **"Manuscrito formal opcional (.docx ABNT) não gerado"** | Reescrito na v2.10.0: `.docx` ABNT, `.tex` e `.pdf` passam a ser **obrigatórios** no pacote final, dentro do critério "pacote completo" da D5. |
| **"Snowballing executado e documentado" (D1, 0.2 pts)** + **"Snowballing forward + backward" como bonus (+0.1)** | Removido na v2.10.1: Decisão 23 (v2.9.0) já tornou snowballing backward + forward **obrigatório**. Os 0.2 pts de D1 foram redistribuídos para o critério de bases consultadas (que cobre a expansão Tier 1 da Decisão 25). Bonificação de +0.1 era duplicação. |
