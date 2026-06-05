# Architecture documentation index

**Canonical reference:** [ARCHITECTURE.md](../ARCHITECTURE.md) — nomenclature, layer diagram, package map, editions, import rules, CI/typing, and refactor playbook.

This file is an index only (no duplicate package tables). Full doc map: [README.md](README.md). Use this page for ADRs and related operator docs.

## Architecture decision records

| ADR | Topic |
|-----|--------|
| [001-event-sourced-runs.md](adr/001-event-sourced-runs.md) | Append-only run events |
| [002-edition-gate.md](adr/002-edition-gate.md) | Individual vs Enterprise |
| [003-projections-layer.md](adr/003-projections-layer.md) | `nimbusware_projections` read models |
| [004-api-request-logging.md](adr/004-api-request-logging.md) | Request logging |
| [005-request-correlation-id.md](adr/005-request-correlation-id.md) | Correlation IDs |

## Related docs

| Doc | Purpose |
|-----|---------|
| [operator-settings.md](operator-settings.md) | Settings catalog and env resolution |
| [ide-bridge.md](ide-bridge.md) | MCP IDE bridge (`nimbusware-mcp`) |
| [deploy/README.md](deploy/README.md) | Docker, CI jobs, production checklist |
| [deploy/oidc.md](deploy/oidc.md) | Enterprise Admin OIDC SSO |
| [operator-bundle-catalog-promotion.md](operator-bundle-catalog-promotion.md) | Code Researcher → catalog candidate flow |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | CI parity and conventions |
| [../tests/README.md](../tests/README.md) | Test layout and markers |
