# Nimbusware documentation

| Document | Audience | Summary |
|----------|----------|---------|
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Developers | **Canonical** package map, layers, editions, CI |
| [architecture.md](architecture.md) | Developers | ADR index (no duplicate architecture body) |
| [operator-settings.md](operator-settings.md) | Operators | Settings catalog and `NIMBUSWARE_*` keys (incl. context-efficiency group) |
| [ide-bridge.md](ide-bridge.md) | Developers | Cursor/IDE MCP bridge (`nimbusware_compact_run`, theater, approve) |
| [adr/006-prompt-tiers.md](adr/006-prompt-tiers.md) | Maintainers | Stable / context / volatile LLM prompt tiers |
| [adr/007-context-compaction.md](adr/007-context-compaction.md) | Maintainers | Campaign handoff compaction and merge-on-recompact |
| [deploy/README.md](deploy/README.md) | Ops | Docker Compose, CI jobs, secrets |
| [deploy/oidc.md](deploy/oidc.md) | Enterprise ops | Admin OIDC SSO |
| [operator-bundle-catalog-promotion.md](operator-bundle-catalog-promotion.md) | Operators | Bundle catalog candidate promotion |
| [enterprise-research-index.md](enterprise-research-index.md) | Enterprise ops | Tenant research index + egress audit |
| [enterprise-buyer.md](enterprise-buyer.md) | Buyers / security | Enterprise compliance checklist |
| [security-quality-gates.md](security-quality-gates.md) | Maintainers | bandit, pip-audit, CI gates |
| [integrations-external-chat.md](integrations-external-chat.md) | Ops | External chat webhook boundary (§20.5) |
| [deploy/k8s/README.md](deploy/k8s/README.md) | Enterprise ops | Reference Kubernetes manifests |
| [adr/](adr/) | Maintainers | Architecture decision records |

Context-efficiency APIs (see [../README.md](../README.md) § Context efficiency): `GET /v1/runs/{id}/context_budget`, `POST /v1/runs/{id}/compact`. Package notes: [../packages/nimbusware_mcp/README.md](../packages/nimbusware_mcp/README.md).

Gitignored local ledgers (not in git): `plan_gap.md`, `nimbusware-orchestrator-local-plan.md`, `pi-features-transplant.md`, `nimbusware-autonomous-completion-plan.md`, `MIGRATION AWAY FROM STREAMLIT.md`.
