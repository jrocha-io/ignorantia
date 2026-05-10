# Ignorantia v3

> Construção de revisões sistemáticas de literatura (SLR)
> PRISMA-2020 do mais alto nível, com saída em HTML interativo
> auto-contido, versionada e auditável.

This site hosts the v3 API reference + curated guides. The
top-level `README.md` in the repository is still the entry point
for the project at large.

## Where to start

| If you are… | Read… |
|---|---|
| New to Ignorantia | [Tutorial — 30 min walkthrough](TUTORIAL.md) |
| Migrating from v2 | [Migration guide v2 → v3](MIGRATION_v2_TO_v3.md) |
| Looking for the architecture | [C4 diagrams](architecture/C4_DIAGRAMS.md) and [`V3_ARCHITECTURE_PLAN.xml`](https://github.com/jrocha-io/ignorantia/blob/main/dev-docs/V3_ARCHITECTURE_PLAN.xml) |
| Composing use cases programmatically | [API reference](api/index.md) |

## v3 in one paragraph

Ignorantia v3 is a Clean-Architecture rewrite of the v2 script
collection. Five bounded contexts (search / render / pipeline /
compliance / audit) sit under
`src/ignorantia/domain/`. Use cases under
`src/ignorantia/application/use_cases/` compose those contexts
through ports. A single Click-based CLI under
`src/ignorantia/interface/cli/` translates `argv` to Command DTOs
and prints schema-validated Result DTOs — no domain entity ever
crosses the interface boundary. v2 callers keep working through
the `ignorantia.legacy` compatibility shim with a documented
deprecation timeline.
