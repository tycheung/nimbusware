# hermes_extensions

Personas, bundles, escalation policy helpers, and YAML-backed extension surfaces consumed by orchestrator and Admin Console config tooling.

## Rules

- Must **not** import `hermes_orchestrator` at module level (enforced by `tests/unit/test_import_graph.py`).
- Prefer pure helpers; side effects belong in orchestrator or API routes.

## Consumers

`hermes_orchestrator` (workflow merge, persona shelves), `nimbusware_console` (config tooling, catalog panels), `nimbusware_api` (admin config routes).

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).
