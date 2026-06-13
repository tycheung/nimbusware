# Nimbusware documentation

| Document | Audience | Summary |
|----------|----------|---------|
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Developers | **Canonical** package map, layers, editions, CI (~2,803 unit pytest / 3,663 collected) |
| [architecture.md](architecture.md) | Developers | ADR index (no duplicate architecture body) |
| [operator-settings.md](operator-settings.md) | Operators | Settings catalog and `NIMBUSWARE_*` keys (incl. context-efficiency group) |
| [ide-bridge.md](ide-bridge.md) | Developers | Cursor/IDE MCP bridge (classify, patch, interject, theater, approve); VS Code status extension compiles in `ci_check` |
| [../releasev1features.md](../releasev1features.md) | Maintainers | Release v1 shipped ledger (pointer to local plan §20.29) |
| [deploy/first-install-timing.md](deploy/first-install-timing.md) | Operators | Reference install → first gate pass timing |
| [deploy/pypi-publish.md](deploy/pypi-publish.md) | Ops | PyPI wheel/sdist publish runbook |
| [deploy/vscode-marketplace.md](deploy/vscode-marketplace.md) | Ops | VS Code Marketplace extension publish runbook |
| [deploy/k8s/tls-cert-manager.md](deploy/k8s/tls-cert-manager.md) | Ops | cert-manager TLS + multi-AZ Helm values |
| [deploy/event-store-retention.md](deploy/event-store-retention.md) | Ops | Retention policy, legal hold, purge execute |
| [deploy/headless-patch-ci.md](deploy/headless-patch-ci.md) | CI / platform | Headless patch from GitHub Actions (`work_type_source=ci`) |
| [deploy/external-ci-bridge.md](deploy/external-ci-bridge.md) | Ops | GitHub Checks / GitLab status on integrator, slice.gate, factory.gate |
| [adr/020-unified-chat-work-type-routing.md](adr/020-unified-chat-work-type-routing.md) | Maintainers | Unified Maker chat, work-type routing, patch lane |
| [adr/021-conversation-dag-branching.md](adr/021-conversation-dag-branching.md) | Maintainers | Chat session DAG, fork/branch navigation, congruent thread (`parity_chat_wiring.yaml`, Postgres persistence journey) |
| [adr/006-prompt-tiers.md](adr/006-prompt-tiers.md) | Maintainers | Stable / context / volatile LLM prompt tiers |
| [adr/007-context-compaction.md](adr/007-context-compaction.md) | Maintainers | Campaign handoff compaction and merge-on-recompact |
| [adr/008-context-artifacts-file-cache.md](adr/008-context-artifacts-file-cache.md) | Maintainers | Context artifact JSON file cache (Individual ship) |
| [eval-tuning-guide.md](eval-tuning-guide.md) | Operators | Campaign completion and launch rubric tuning |
| [factory/p0-finding-taxonomy.md](factory/p0-finding-taxonomy.md) | Maintainers | P0 finding categories for factory/maintenance |
| [deploy/fleet-playwright-pool.md](deploy/fleet-playwright-pool.md) | Enterprise ops | Remote Playwright WS pool for PUT E2E |
| [deploy/campaign-soak-runbook.md](deploy/campaign-soak-runbook.md) | Enterprise ops | Long-run autonomous campaign soak |
| [deploy/README.md](deploy/README.md) | Ops | Docker Compose, CI jobs, secrets |
| [deploy/enterprise-integrator-runbook.md](deploy/enterprise-integrator-runbook.md) | Enterprise ops | Integrator gate, live adapter probes, external CI bridge |
| [deploy/production-fleet-redis-secrets.md](deploy/production-fleet-redis-secrets.md) | Enterprise ops | Multi-broker Redis (`NIMBUSWARE_REDIS_FLEET_URLS`) in Helm/K8s |
| [deploy/oidc.md](deploy/oidc.md) | Enterprise ops | Admin OIDC SSO + group → role mapping |
| [deploy/replay-from-runbook.md](deploy/replay-from-runbook.md) | Operators | Replay-from checkpoint (Admin wizard + API) |
| [operator-bundle-catalog-promotion.md](operator-bundle-catalog-promotion.md) | Operators | Bundle catalog candidate promotion |
| [enterprise-research-index.md](enterprise-research-index.md) | Enterprise ops | Tenant research index + egress audit |
| [enterprise-buyer.md](enterprise-buyer.md) | Buyers / security | Enterprise compliance checklist |
| [security-quality-gates.md](security-quality-gates.md) | Maintainers | bandit, pip-audit, CI gates |
| [integrations-external-chat.md](integrations-external-chat.md) | Ops | External chat webhook boundary (§20.5) |
| [operator-interjection-slo.md](operator-interjection-slo.md) | Operators | Interjection drain SLO + Admin timeline explain |
| [deploy/k8s/README.md](deploy/k8s/README.md) | Enterprise ops | Reference Kubernetes manifests |
| [../tests/README.md](../tests/README.md) | Developers | Test layout, CI subsets, Playwright 120s timeout |
| [adr/](adr/) | Maintainers | Architecture decision records |

**P14–P17 operator surfaces (see [../README.md](../README.md)):** TestPyPI bootstrap publish; live theater SSE with optional LLM summary (`NIMBUSWARE_THEATER_LLM_SUMMARY`); Progress parity wiring (`parity_progress_wiring.yaml`); Admin hardware catalog strip; append-only event store integration test; industry critic packs; Admin parity wiring; PUT-preview launch-test journeys with keyboard/mouse fidelity; asyncio-safe sync Playwright; bootstrap wheel install smoke; publish workflow CI guard.

Context-efficiency APIs (see [../README.md](../README.md) § Context efficiency): `GET /v1/runs/{id}/context_budget`, `POST /v1/runs/{id}/compact` (scopes: `all`, `last_n`, `source_refs`), `POST /v1/runs/{id}/compactions/{compaction_id}/revert`, `POST /v1/runs/{id}/replay-from` (re-enqueues campaign tick when applicable), `POST /v1/runs/{id}/context-artifacts/from-compaction`, `POST /v1/runs/{id}/memory-chunks/{chunk_id}/insert`, `GET/POST /v1/projects/{id}/context-artifacts`, `POST .../context-artifacts/{artifact_id}/bridge-memory` (optional `NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD=1`).

Gitignored local planning (not in git) — **two files only:**

| File | Role |
|------|------|
| `nimbusware-orchestrator-local-plan.md` | Normative product contract (§1–§20) |
| `plan_gap.md` | Epics ledger, maturity %, polish queue (gitignored) |
| `e2e-true-variable-launch-testing.md` | §20.24–§20.26 variable PUT launch plan (gitignored) |

Former split docs (autonomous completion, Pi transplant, Streamlit migration) are consolidated into these two (Jun 2026).

## Language / workflow support matrix (Release v1)

| Profile | Patch | micro_slice | factory T0–T3 | Notes |
|---------|-------|-------------|-----------------|-------|
| `patch` | Yes | — | — | Python + web globs default |
| `patch_go` | Yes | — | — | Go modules; fixture `tests/fixtures/repos/tiny_go_app`; `go test` in slice verify; gate-pass journey `tests/e2e/journeys/test_patch_go_jvm_gate_journey.py` (requires `go` on PATH) |
| `patch_jvm` | Yes | — | — | Java/Kotlin; fixture `tests/fixtures/repos/tiny_jvm_app` (`pom.xml` + JUnit); `mvn test` in slice verify; same gate journey (requires `mvn` + `java`) |
| `micro_slice` / `micro_slice_fullstack` | — | Yes | — | Python + JS framework packs |
| `campaign_factory_zero_touch` | — | — | T2 default | Catalog PUT E2E flows |

Full factory and launch eval catalogs: `configs/launch_eval/catalog.yaml`, `configs/factory/flows/`.
