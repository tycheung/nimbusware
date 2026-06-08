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
| [deploy/enterprise-integrator-runbook.md](deploy/enterprise-integrator-runbook.md) | Enterprise ops | Integrator gate, live adapter probes, external CI bridge |
| [deploy/production-fleet-redis-secrets.md](deploy/production-fleet-redis-secrets.md) | Enterprise ops | Multi-broker Redis (`NIMBUSWARE_REDIS_FLEET_URLS`) in Helm/K8s |
| [deploy/oidc.md](deploy/oidc.md) | Enterprise ops | Admin OIDC SSO |
| [operator-bundle-catalog-promotion.md](operator-bundle-catalog-promotion.md) | Operators | Bundle catalog candidate promotion |
| [enterprise-research-index.md](enterprise-research-index.md) | Enterprise ops | Tenant research index + egress audit |
| [enterprise-buyer.md](enterprise-buyer.md) | Buyers / security | Enterprise compliance checklist |
| [security-quality-gates.md](security-quality-gates.md) | Maintainers | bandit, pip-audit, CI gates |
| [integrations-external-chat.md](integrations-external-chat.md) | Ops | External chat webhook boundary (§20.5) |
| [deploy/k8s/README.md](deploy/k8s/README.md) | Enterprise ops | Reference Kubernetes manifests |
| [adr/](adr/) | Maintainers | Architecture decision records |

Context-efficiency APIs (see [../README.md](../README.md) § Context efficiency): `GET /v1/runs/{id}/context_budget`, `POST /v1/runs/{id}/compact`, `POST /v1/runs/{id}/compactions/{compaction_id}/revert`. Package notes: [../packages/nimbusware_mcp/README.md](../packages/nimbusware_mcp/README.md).

Gitignored local planning (not in git) — **two files only:**

| File | Role |
|------|------|
| `nimbusware-orchestrator-local-plan.md` | Normative product contract (§1–§20) |
| `plan_gap.md` | Epics ledger, maturity %, polish queue |

Former split docs (autonomous completion, Pi transplant, Streamlit migration) are consolidated into these two (Jun 2026).
