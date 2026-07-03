# Agent runtime

The orchestrator (`orchestrator`, `agent_core`) drives adversarial agentic workflows: multi-role pipeline, unanimous gates, verifiers, and optional Ollama-backed LLM stages.

## Core loop

- **Run lifecycle** — `run.created` → plan → micro-slice loop (plan → implement → verify → critique → test → gate); when all slices pass, optional integrator gate, integration-adapter writer, agent evaluator, and self-refinement markers run before terminal `enforcement.gate`
- **Adversarial critics** — domain-bound critique stages (security, performance, resilience, refactor)
- **Unanimous gates** — stage progression blocked until critics/verifiers pass (escalation anti-deadlock)
- **Parallel writers** — frontend/backend/test writers with `asyncio.gather`
- **Bundle integrator** — catalog search, FAISS ranking, integrator gate with live adapter probe
- **Personas** — business + development shelves, probation automation
- **Self-refinement** — gated/ungated loops with optional LLM critique

## Workflow profiles

| Profile | Use |
|---------|-----|
| `patch` | Hotfix lane — one bounded slice, minimal stage graph |
| `patch_go` / `patch_jvm` | Go/Java patch variants |
| `micro_slice` | Bounded files/LOC per slice, verify → critique → test → optional `slice.e2e` → gate |
| `micro_slice_fullstack` | Full-stack + launch-test writer/critic stages |
| `campaign_micro_slice` | Autonomous campaign — heuristic or LLM backlog → one slice/tick → completion |
| `campaign_factory_zero_touch` | Factory scaffold T0–T3 with PUT E2E |

Configs: [`configs/workflows/`](../../configs/workflows/). Default: `micro_slice` (all verify passes run the micro-slice loop; `nimbusware_production` remains for extended YAML flags).

## Notable subsystems

- **Slice implement agent** — JIT tool loop (`read`, `edit`, `write`, `grep`, `shell`, optional `browser_act`)
- **Cross-slice handoffs** — deterministic `slice.handoff` summaries with `surface_id`, `stack_id`, and contract refs in handoff + context packets
- **Campaign backlog** — heuristic decomposition from `business_prompt` (CRM/todo/API templates, repo paths) or optional LLM via `NIMBUSWARE_BACKLOG_GENERATOR_MODEL`
- **Campaign compaction** — summarize older handoffs in long runs
- **Factory scaffold** — PUT preview runtime, factory tiers, interaction surface map, PUT E2E flows
- **Persistent dev env** — session supervisor, incremental regression, UI controller (ADRs [009](adr/009-persistent-dev-environment.md), [010](adr/010-ui-controller.md))
- **Launch testing** — variable PUT flows, framework packs, human-fidelity checks (ADR [011](adr/011-human-fidelity-e2e.md))
- **Operator interjection + autopilot** — trust slider 0–10, interjection queue with surface steers (`[steer:web]`, `@api`) (ADRs [013](adr/013-operator-interjection.md)–[015](adr/015-custom-autopilot-profiles.md))
- **Enforcement depth** — second 0–10 axis for workspace verify/gate strictness; presets in `configs/enforcement/presets.yaml`, wired into `micro_slice_verify` and `slice.gate` via `enforcement_pipeline.py`; terminal `enforcement.gate` for level-10 parity; API `GET/PUT /v1/runs/{id}/enforcement`; enterprise fleet min/max via `GET/PUT /v1/enterprise/tenants/{ref}/enforcement-policy`; Maker Progress dual-slider (ADR [026](adr/026-enforcement-depth-slider.md))
- **Code intelligence** — code graph (v2 bundle), entrypoint-aware orphans/route reachability, deterministic refactor patches (+ optional LLM patch when `refactor.llm_enabled`), improvement/resolution councils, variant arena (ADRs [016](adr/016-repo-exploration-variants.md)–[019](adr/019-debate-first-resolution.md))
- **Preflight** — Ollama/model health at run start
- **Scraper stage** — role-gated HTTP fetch with artifact retention
- **Retrieval memory** — index findings/gate failures; replay harness

## Refactor stage

When `refactor.enabled` and `stub_only: false` (production default), the pipeline loads a **code-intel bundle** (`.nimbusware/code_intel/{fingerprint}.json`, schema v2) and emits a proposal with a non-empty **JSON patch** for orphan or route-reachability findings. `refactor.critique` fails when the orphan gate is exceeded or when a non-`noop` proposal has an empty patch. Optional `refactor.llm_enabled` requests an LLM-generated patch via Ollama (`NIMBUSWARE_USE_LLM=1`) and falls back to deterministic patches.

## Fast slice

`fast_slice: true` or `NIMBUSWARE_FAST_SLICE` skips optional universal critic matrix when max finding severity is below HIGH.

## Parallel critics (mesh)

When `hardware_tier=strong`, set `NIMBUSWARE_ALLOW_PARALLEL_CRITICS=1` to run security/performance/network critique stages concurrently on remote mesh workers when a session uses compute sharing. Host merges `replay_events` and critic `gate_fail` from work-unit completion payloads.

## Configuration

Workflow YAML, personas, roles, `model-routing.yaml`, bundles, critic packs, and skills live under [`configs/`](../../configs/). With Postgres, operator edits persist to `config_document` and materialize at API startup.

Critic packs: `GET /v1/config/critic-packs/{id}/workflows` for blast-radius preview.
