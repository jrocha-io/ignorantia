# Polite-pool outreach — Ignorantia

A maioria das APIs de OA não exige cadastro: basta passar um email
de contato como query parameter (`?email=...` ou `?mailto=...`) para
entrar na "polite pool". Os provedores usam esse email só para
notificar se a operação tiver padrão abusivo. Esta lista cobre
quem usamos no skill `ignorantia` e qual é o canal de cada um.

## Endereço de contato a usar nos parâmetros

Decida **um único endereço** (do projeto ou seu) e use o mesmo nos
quatro provedores abaixo. Sugestão: criar um alias dedicado tipo
`ignorantia-skill@<seu-domínio>` para isolar correspondência da
pool. Para os passos abaixo assume-se `<EMAIL>`.

## Email body

> Envie um exemplar para cada provedor da próxima seção. Só
> Unpaywall/OAButton exige notificação por email; Crossref e
> OpenAlex aceitam apenas o parâmetro na URL — o envio para esses é
> cortesia de comunidade.

**Assunto:** Notification — addition of `<EMAIL>` to your polite
pool for the *Ignorantia* SLR skill

```
Olá,

Sou José Rocha, mantenedor do skill open-source `ignorantia`
(https://github.com/jrocha-io/ignorantia), uma ferramenta para
construção de revisões sistemáticas de literatura PRISMA-2020
executada pelo Claude (Anthropic).

A partir desta semana o skill passa a usar a sua API com o endereço
de contato `<EMAIL>`. O perfil de uso esperado é:

- volume típico: até ~500 requests por execução de SLR (uma SLR
  por usuário, ~1-5 SLRs por dia agregadas);
- backoff: throttle de 1 s entre requests (configurável);
  retry exponencial em 429/5xx até 3 tentativas;
- User-Agent: `ignorantia/<versão> (+https://github.com/jrocha-io/ignorantia)`.

Os requests virão sempre com `?email=<EMAIL>` (ou `?mailto=` para
Crossref/OpenAlex) na query string. Se o padrão de uso parecer
problemático em algum momento, basta responder este email — leio
no mesmo dia e ajustamos throttle / retry.

Obrigado pelo serviço,
José Rocha
mantenedor de `ignorantia`
```

## Lista de destinatários

| # | Provedor | Endereço | Obrigatório? |
|---|---|---|---|
| 1 | Unpaywall / OA.Works | `support@oa.works` | Recomendado — confirmam que estamos na polite pool |
| 2 | Crossref | `support@crossref.org` | Opcional — `?mailto=<EMAIL>` basta; envio é cortesia |
| 3 | OpenAlex | `team@ourresearch.org` | Opcional — mesma política de Crossref |
| 4 | OAButton | `team@oa.works` | Mesma equipe pós-aquisição da Unpaywall; pode ir junto no #1 |

**Mínimo aceitável**: enviar só para `support@oa.works` (#1) — esse
cobre Unpaywall + OAButton e é o único onde a documentação pede
notificação explícita.

## Após enviar

Quando responderem (ou após 7 dias sem resposta — silent acceptance),
me passe o `<EMAIL>` escolhido. Eu faço o PR que injeta na
composition root:

```python
# src/ignorantia/interface/cli/main.py
def build_search_for_studies_use_case() -> SearchForStudiesUseCase:
    factory = AdapterFactory(http=build_http_client())
    # OaResolverFactory consome unpaywall_email; sem ele, "unpaywall"
    # não é registrado e fica acessível só o oa_button (que não
    # exige email).
    return SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))
```

Padrão: ler de `os.environ["IGNORANTIA_CONTACT_EMAIL"]` para não
hardcodar — se ausente, `OaResolverFactory` recusa registrar
`unpaywall` silenciosamente (já é o comportamento implementado em
`infrastructure/search/oa_resolver_factory.py`).
