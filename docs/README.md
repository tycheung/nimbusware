# Nimbusware documentation

Canonical architecture: [ARCHITECTURE.md](../ARCHITECTURE.md). Quick install: [getting-started.md](getting-started.md).

## Start here

| Document | Audience |
|----------|----------|
| [getting-started.md](getting-started.md) | Everyone — install, bootstrap, run, Docker |
| [product/maker.md](product/maker.md) | Makers — Chat, Progress, Review, Model Hub |
| [product/admin.md](product/admin.md) | Operators — Admin Console, fleet, metrics |
| [product/editions.md](product/editions.md) | Individual vs Enterprise, auth scopes |
| [product/api-overview.md](product/api-overview.md) | API route map (user vs admin) |
| [agent-runtime.md](agent-runtime.md) | Pipeline, workflow profiles, critics, gates |
| [operator-settings.md](operator-settings.md) | Settings catalog (246 `NIMBUSWARE_*` keys) |

## Reference

| Document | Topic |
|----------|-------|
| [reference/cli.md](reference/cli.md) | CLI commands and ops scripts |
| [reference/env-vars.md](reference/env-vars.md) | Common environment variables |
| [reference/context-efficiency.md](reference/context-efficiency.md) | Context budget, compaction, artifacts |
| [reference/benchmarks.md](reference/benchmarks.md) | SWE-bench harness, intent→patch snapshots |
| [reference/launch-eval.md](reference/launch-eval.md) | Workspace quality rubric |
| [architecture.md](architecture.md) | ADR index |
| [eval-tuning-guide.md](eval-tuning-guide.md) | Campaign completion and launch tuning |

## Features (v1.2)

| Document | Topic |
|----------|-------|
| [model-hub.md](model-hub.md) | Model Hub, API connections vault |
| [install-profiles.md](install-profiles.md) | Recommended vs barebones install |
| [hybrid-routing-migration.md](hybrid-routing-migration.md) | Legacy routing → resolver shim |
| [collaborative-chat.md](collaborative-chat.md) | Multi-participant chat sessions |
| [collaborative-chat-threat-model.md](collaborative-chat-threat-model.md) | Collab security model |
| [conversation-library.md](conversation-library.md) | Folders, groups, tags, ACL |
| [compute-mesh.md](compute-mesh.md) | Distributed compute nodes |
| [ide-bridge.md](ide-bridge.md) | MCP IDE bridge |

## Operators & enterprise

| Document | Topic |
|----------|-------|
| [enterprise-buyer.md](enterprise-buyer.md) | Buyer / security checklist |
| [enterprise-research-index.md](enterprise-research-index.md) | Research index + egress audit |
| [operator-bundle-catalog-promotion.md](operator-bundle-catalog-promotion.md) | Bundle catalog promotion |
| [operator-interjection-slo.md](operator-interjection-slo.md) | Interjection drain SLO |
| [integrations-external-chat.md](integrations-external-chat.md) | External webhook steering |
| [security-quality-gates.md](security-quality-gates.md) | bandit, pip-audit, CI gates |
| [factory/p0-finding-taxonomy.md](factory/p0-finding-taxonomy.md) | Factory P0 finding categories |

## Deploy & ops

| Document | Topic |
|----------|-------|
| [deploy/README.md](deploy/README.md) | Docker Compose, CI jobs, checklist |
| [deploy/k8s/README.md](deploy/k8s/README.md) | Kubernetes manifests |
| [deploy/helm.md](deploy/helm.md) | Helm chart |
| [deploy/first-install-timing.md](deploy/first-install-timing.md) | Install → first gate pass timing |
| [deploy/launcher.md](deploy/launcher.md) | Desktop launcher builds & releases |
| [deploy/enterprise-integrator-runbook.md](deploy/enterprise-integrator-runbook.md) | Integrator gate |
| [deploy/production-fleet-redis-secrets.md](deploy/production-fleet-redis-secrets.md) | Multi-broker Redis |
| [deploy/oidc.md](deploy/oidc.md) | Admin OIDC SSO |
| [deploy/agent-sandbox.md](deploy/agent-sandbox.md) | Agent sandbox backends |
| [deploy/event-store-retention.md](deploy/event-store-retention.md) | Event retention & purge |
| [deploy/external-ci-bridge.md](deploy/external-ci-bridge.md) | GitHub Checks / GitLab status |
| [deploy/headless-patch-ci.md](deploy/headless-patch-ci.md) | Headless patch from CI |
| [deploy/replay-from-runbook.md](deploy/replay-from-runbook.md) | Replay-from checkpoint |
| [deploy/campaign-soak-runbook.md](deploy/campaign-soak-runbook.md) | Campaign soak |
| [deploy/fleet-playwright-pool.md](deploy/fleet-playwright-pool.md) | Remote Playwright pool |
| [deploy/live-writers-soak.md](deploy/live-writers-soak.md) | Live-writer validation |
| [deploy/pypi-publish.md](deploy/pypi-publish.md) | PyPI publish |
| [deploy/vscode-marketplace.md](deploy/vscode-marketplace.md) | VS Code extension publish |
| [deploy/v1.1-ship-checklist.md](deploy/v1.1-ship-checklist.md) | v1.1 ship checklist |

Runbooks: [`scripts/runbooks/`](../scripts/runbooks/).

## Architecture decisions

All ADRs: [architecture.md](architecture.md) → [adr/](adr/).

## Audits

| Document | Topic |
|----------|-------|
| [audits/llm-call-sites.md](audits/llm-call-sites.md) | LLM dispatch audit matrix |
| [audits/parallel-inventory.md](audits/parallel-inventory.md) | Parallelism inventory |

## Development

| Document | Topic |
|----------|-------|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | CI parity, conventions |
| [../tests/README.md](../tests/README.md) | Test layout, markers, Playwright |
| [../benchmarks/README.md](../benchmarks/README.md) | Benchmark snapshot formats |

## Language / workflow matrix

| Profile | Patch | micro_slice | factory | Notes |
|---------|-------|-------------|---------|-------|
| `patch` | Yes | — | — | Python + web globs |
| `patch_go` / `patch_jvm` | Yes | — | — | Go/Java fixtures |
| `micro_slice` / `micro_slice_fullstack` | — | Yes | — | Framework packs |
| `campaign_factory_zero_touch` | — | — | T2 | Catalog PUT E2E |

Catalogs: `configs/launch_eval/catalog.yaml`, `configs/factory/flows/`.

## Local planning (gitignored)

Normative product contract and maturity backlog live outside git:

- `nimbusware-orchestrator-local-plan.md`
- `PLAN_GAP.md`
