# nimbusware_config

Versioned YAML config documents (workflows, personas, bundles) with Postgres materializer and optimistic concurrency for Admin Console edits.

When `NIMBUSWARE_CONFIG_FROM_DB=1`, `ConfigMaterializer` is the runtime source of truth; repo `configs/` YAML is exported for gitops review (`export_config_to_repo`).

## Layout

| Area | Role |
|------|------|
| `documents/` | Typed config document models |
| `materializer.py` | YAML ↔ Postgres sync |
| `store.py` | Read/write with expected-version checks |

## Consumers

`nimbusware_api` admin routes, `nimbusware_console` config tooling, `nimbusware_orchestrator` workflow merge at run start.

Normative Nimbusware contract: gitignored `nimbusware-orchestrator-local-plan.md` at repo root.
