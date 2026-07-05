# Architecture documentation index

**Canonical reference:** [ARCHITECTURE.md](../ARCHITECTURE.md) — nomenclature, layer diagram, package summary, editions, import rules, CI/typing, and refactor playbook. **Package catalog:** [packages/README.md](../packages/README.md).

This file is an index only (no duplicate package tables). Full doc map: [README.md](README.md). Use this page for ADRs and related operator docs.

## Architecture decision records

| ADR | Topic |
|-----|--------|
| [001-event-sourced-runs.md](adr/001-event-sourced-runs.md) | Append-only run events |
| [002-edition-gate.md](adr/002-edition-gate.md) | Individual vs Enterprise |
| [003-projections-layer.md](adr/003-projections-layer.md) | `projections` read models |
| [004-api-request-logging.md](adr/004-api-request-logging.md) | Request logging |
| [005-request-correlation-id.md](adr/005-request-correlation-id.md) | Correlation IDs |
| [006-prompt-tiers.md](adr/006-prompt-tiers.md) | Stable/context/volatile LLM prompt tiers |
| [007-context-compaction.md](adr/007-context-compaction.md) | Campaign handoff compaction |
| [008-context-artifacts-file-cache.md](adr/008-context-artifacts-file-cache.md) | Context artifact JSON file cache |
| [009-persistent-dev-environment.md](adr/009-persistent-dev-environment.md) | Persistent dev env sessions |
| [010-ui-controller.md](adr/010-ui-controller.md) | BrowserController + UI flow DSL |
| [011-human-fidelity-e2e.md](adr/011-human-fidelity-e2e.md) | Human-fidelity E2E checks |
| [012-diagnose-fix-learn.md](adr/012-diagnose-fix-learn.md) | Diagnose-fix-learn loop |
| [013-operator-interjection.md](adr/013-operator-interjection.md) | Interjection queue |
| [014-autopilot-presets.md](adr/014-autopilot-presets.md) | Autopilot slider presets |
| [015-custom-autopilot-profiles.md](adr/015-custom-autopilot-profiles.md) | Custom checkpoint profiles |
| [016-repo-exploration-variants.md](adr/016-repo-exploration-variants.md) | Code graph + variant arena |
| [017-simplification-refactor.md](adr/017-simplification-refactor.md) | Simplification metrics |
| [018-improvement-council.md](adr/018-improvement-council.md) | Continuous improvement council |
| [019-debate-first-resolution.md](adr/019-debate-first-resolution.md) | Debate-first gate resolution |
| [020-unified-chat-work-type-routing.md](adr/020-unified-chat-work-type-routing.md) | Unified Maker chat, work-type routing, patch lane |
| [021-conversation-dag-branching.md](adr/021-conversation-dag-branching.md) | Persistent conversation DAG, fork/branch navigation |
| [022-per-role-model-routing.md](adr/022-per-role-model-routing.md) | Per-role `ModelBindingResolver`, provider vault, mid-chat swap |
| [023-collaborative-chat-sessions.md](adr/023-collaborative-chat-sessions.md) | Multi-participant chat sessions (opt-in) |
| [024-install-profiles.md](adr/024-install-profiles.md) | Recommended vs barebones install profiles |
| [027-install-setup-bundles.md](adr/027-install-setup-bundles.md) | Default vs enterprise setup bundles |
| [025-distributed-compute-mesh.md](adr/025-distributed-compute-mesh.md) | Compute node registry and work-unit mesh MVP |
| [026-enforcement-depth-slider.md](adr/026-enforcement-depth-slider.md) | Enforcement depth 0–10 (workspace CI strictness) |
| [028-package-directory-depth.md](adr/028-package-directory-depth.md) | Package depth vs breadth; orchestrator domain subpackages |
| [026-host-transfer.md](adr/026-host-transfer.md) | Collaborative session host transfer MVP |
| [031-context-budget-telemetry.md](adr/031-context-budget-telemetry.md) | Rate-limited `context.budget.sampled` events |
| [032-incremental-maker-progress-sse.md](adr/032-incremental-maker-progress-sse.md) | Tail event fetch + `progress_delta` SSE |
| [033-structure-over-source-reads.md](adr/033-structure-over-source-reads.md) | Agent read modes: outline, digest, full |
| [034-standards-platform-rollout.md](adr/034-standards-platform-rollout.md) | Standards platform v1 rollout (parallel CI, gate, UI) |
| [029-standards-ci-streams.md](adr/029-standards-ci-streams.md) | Named CI streams, verdict modes, stream runner |
| [030-standards-bundles-mart.md](adr/030-standards-bundles-mart.md) | Standards bundles, facades, mart tiers |

Tier 3 context-efficiency (EFF track **complete** Jul 2026): ADRs 006, 007, 031–033; operator reference [reference/context-efficiency.md](reference/context-efficiency.md). **Standards platform v1** (Jul 2026): parallel CI stream matrix + aggregate, `slice.standards` gate, Maker/Admin UI, MCP/fleet (ADRs 029–030, 034). Backlog: local `PLAN_GAP.md`.

## v1.2 operator docs

| Doc | Purpose |
|-----|---------|
| [model-hub.md](model-hub.md) | Model Hub UI, API connections vault, Ollama install |
| [install-profiles.md](install-profiles.md) | Recommended vs barebones installer |
| [hybrid-routing-migration.md](hybrid-routing-migration.md) | Legacy `stage_providers` → resolver shim |
| [collaborative-chat.md](collaborative-chat.md) | Collab sessions, participants, host transfer |
| [compute-mesh.md](compute-mesh.md) | Node registry, worker policy, session compute opt-in |
| [audits/llm-call-sites.md](audits/llm-call-sites.md) | LLM dispatch audit matrix |

## Related docs

| Doc | Purpose |
|-----|---------|
| [operator-settings.md](operator-settings.md) | Settings catalog and env resolution |
| [ide-bridge.md](ide-bridge.md) | MCP IDE bridge (`nimbusware-mcp`) |
| [integrations-external-chat.md](integrations-external-chat.md) | Maker Chat workspace + external webhook steering |
| [deploy/README.md](deploy/README.md) | Docker, CI jobs, production checklist |
| [deploy/oidc.md](deploy/oidc.md) | Enterprise Admin OIDC SSO |
| [operator-bundle-catalog-promotion.md](operator-bundle-catalog-promotion.md) | Code Researcher → catalog candidate flow |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | CI parity and conventions |
| [../tests/README.md](../tests/README.md) | Test layout and markers |
