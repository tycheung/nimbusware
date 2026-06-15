# Operator settings

Environment variables and flags are grouped by **access grain**. Managed values live in Postgres (`operator_settings` namespace); install secrets stay in `.env`.

## Scopes

| Scope | Who edits | Storage | UI |
|-------|-----------|---------|-----|
| **install** | Operator / installer | `.env` only | Admin read-only |
| **system** | Admin | Postgres `operator_settings/system` | Admin Console → Operator settings |
| **user** | Maker | Postgres `operator_settings/user` | Maker → Settings |
| **run** | Per run | `run.created` metadata | `POST /v1/runs` `operator_settings` |
| **internal** | CI/dev only | Not stored | None (audit-allowlisted) |

## Resolution order

For managed keys: **run override → user profile → system defaults → process env → catalog default**.

YAML override knobs (universal critique): only explicit `os.environ` or run overrides replace workflow YAML — catalog defaults do not.

Fail-closed §14 keys (`NIMBUSWARE_SKIP_PREFLIGHT`, `NIMBUSWARE_RUN_BANDIT`, `NIMBUSWARE_OUTBOUND_FETCH_ENABLED`, `NIMBUSWARE_PREFLIGHT_JSON_PROBE`) use raw env reads after Postgres sync on startup.

## API

- `GET /v1/settings/catalog`
- `GET/PATCH /v1/settings/system` (admin)
- `GET/PATCH /v1/settings/me` (user)

## CI guard

`scripts/audit_operator_env.py` runs in `scripts/ci_check.ps1`. Every `NIMBUSWARE_*` / `OLLAMA_HOST` / `PORT` read under `packages/` must be cataloged or in a bootstrap allowlist — including reads via `env_str`, `env_bool`, `env_truthy`, `resolve_str`, and local `_int_env` / `_truthy_env` helpers. `scripts/run_openapi_ts_ci_gate.py` regenerates Admin `schema.d.ts` (and snapshots `openapi.json`) from the FastAPI OpenAPI export.

## Implementation

- Catalog: `packages/nimbusware_env/settings_catalog.py` + `settings_catalog_extended.py` (**234** keys; Ollama URL consolidated Jun 2026 — use `NIMBUSWARE_OLLAMA_BASE_URL`)

### Context budget (`*_MAX_CHARS`)

Slice packet, repo map, symbol sketch, LLM history, handoff, and memory excerpt limits resolve from `NIMBUSWARE_SLICE_BUDGET_PRESET` (`tiny` / `standard` / `careful`). Per-key `*_MAX_CHARS` env overrides are no longer honored. Read/shell output caps stay independent overrides. **26** universal-critique env keys override workflow YAML when explicitly set (panel enable/llm/stub + 3 global gate-fail knobs; see `effective_universal_critique`).

### Redundant / alias keys (prefer one)

| Prefer | Legacy alias | Notes |
|--------|--------------|-------|
| `NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE` | `NIMBUSWARE_WORKFLOW_PROFILE` (internal) | Prefer **DEFAULT**; legacy alias read from `os.environ` only |
| `NIMBUSWARE_API_PORT` | `PORT` (internal legacy) | API bind port |
| `NIMBUSWARE_OLLAMA_BASE_URL` | `OLLAMA_HOST` (internal legacy) | Canonical Ollama endpoint |
| `NIMBUSWARE_CONFIG_FROM_DB=1` | `NIMBUSWARE_CONFIG_FROM_FILES=0` | Mutually exclusive config authority |
| `NIMBUSWARE_API_BASE` | host + `NIMBUSWARE_API_PORT` | Explicit wins; else derived from bind host/port |
| `NIMBUSWARE_RUN_DISPATCH` | — | `memory` or `redis` for campaign worker dispatch |
| `NIMBUSWARE_UNIVERSAL_CRITIQUE_*_ON_GATE_FAIL` (3 keys) | — | Global UC gate-fail env applies all critique panels |
| `NIMBUSWARE_SLICE_BUDGET_PRESET` | `NIMBUSWARE_SLICE_*_MAX_CHARS` (6 removed keys) | Preset drives packet/repo_map/symbol_sketch/history/handoff/memory excerpt caps |

**Tri-state system keys** (empty = follow workflow YAML): optional stages and universal-critique panel overrides. Prefer workflow profile YAML in `configs/workflows/` for defaults; use env only for operator overrides.

**Parallelism:** `NIMBUSWARE_PARALLEL_WRITERS` (system), `NIMBUSWARE_MAX_PARALLEL_WRITERS` (user governor) — different layers; not duplicates.
- Store: `packages/nimbusware_env/settings_store.py`
- Resolver: `packages/nimbusware_env/settings_resolve.py`
- Helpers: `packages/nimbusware_env/env_flags.py`

Add new tunables to the catalog first, then read via `env_flags` / `settings_resolve`.

## Context efficiency (group: User — context efficiency)

Preset `NIMBUSWARE_SLICE_BUDGET_PRESET` (`tiny` / `standard` / `careful`) drives packet, repo map, symbol sketch, LLM history, handoff, and memory excerpt caps. Legacy per-key `*_MAX_CHARS` env overrides are no longer read.

| Key | Default | Notes |
|-----|---------|-------|
| `NIMBUSWARE_SLICE_BUDGET_PRESET` | standard | Context cap bundle for micro-slice prompts |
| `NIMBUSWARE_READ_MAX_CHARS` | 16000 | Agent read tool |
| `NIMBUSWARE_SHELL_OUTPUT_MAX_CHARS` | 4000 | Agent shell output |
| `NIMBUSWARE_AGENT_JIT_LOOP` | 1 | Multi-turn agent implement |
| `NIMBUSWARE_AGENT_TOOLS` | read,write,edit,grep,shell | Tool allowlist (`find`, `ls` optional) |
| `NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS` | 1 | Theater/timeline agent tool pruning |
| `NIMBUSWARE_AGENT_COMPACT` | 1 | Manual compaction API/MCP gate |
| `NIMBUSWARE_HANDOFF_LLM_SUMMARY` | 0 | Optional LLM handoff merge |
| `NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED` | 1 | Campaign compaction |
| `NIMBUSWARE_CAMPAIGN_KEEP_RECENT_TOKENS` | 12000 | Recent verbatim window (HW override when unset) |
| `NIMBUSWARE_CAMPAIGN_RESERVE_TOKENS` | 8000 | Output reservation |
| `NIMBUSWARE_MEMORY_RETRIEVAL_K` | 5 | Memory chunks per slice (YAML may override) |
| `NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD` | 0 | Rebuild FAISS after context-artifact bridge |
| `NIMBUSWARE_AXE_ENABLED` | 0 | axe-core in human-fidelity suite |
| `NIMBUSWARE_DEFAULT_MODEL` | (empty) | Fallback Ollama model when stage model unset |

## Git outputs (run metadata)

Campaign and factory runs on git-backed workspaces receive `run.created` metadata:

| Key | Default | Notes |
|-----|---------|-------|
| `git.native_outputs` | `true` when workspace has `.git` | Branch/commit helpers in `git_outputs.py` |
| `git.open_pr_on_complete` | `true` for campaign/factory on git workspaces | After terminal gate pass, Maker Review shows **Open PR** when `gh` / git-pr CLI is configured |

Patch and micro-slice runs do not set `open_pr_on_complete` by default. Global fallback: `NIMBUSWARE_GIT_PR_ON_COMPLETE`. See [external-ci-bridge.md](deploy/external-ci-bridge.md) and Maker Review git panel.

**Fleet / scraper (system):** `NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_DEPTH` (100), `NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_IN_FLIGHT` (20), `NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE` (0).

**Install secrets:** `NIMBUSWARE_AUDIT_EXPORT_SIGNING_KEY` (audit bundle HMAC).

Helpers: `agent_core.context_budget`, `nimbusware_orchestrator.prompt_tiers`, `nimbusware_orchestrator.context_compaction`.
