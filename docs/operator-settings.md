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

`scripts/audit_operator_env.py` runs in `scripts/ci_check.ps1`. Every `NIMBUSWARE_*` / `OLLAMA_HOST` / `PORT` read under `packages/` must be cataloged or in a bootstrap allowlist — including reads via `env_str`, `env_bool`, `env_truthy`, `resolve_str`, and local `_int_env` / `_truthy_env` helpers.

## Implementation

- Catalog: `packages/nimbusware_env/settings_catalog.py` + `settings_catalog_extended.py` (**238** keys; Jun 2026 orphan-key closure + fleet/scraper/memory groups)

### Redundant / alias keys (prefer one)

| Prefer | Legacy alias | Notes |
|--------|--------------|-------|
| `NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE` | `NIMBUSWARE_WORKFLOW_PROFILE` | `env_flags.nimbusware_workflow_profile()` checks both |
| `NIMBUSWARE_API_PORT` / `PORT` | — | Bind port; use one in `.env` |
| `NIMBUSWARE_OLLAMA_BASE_URL` | `OLLAMA_HOST` | Ollama endpoint |
| `NIMBUSWARE_CONFIG_FROM_DB=1` | `NIMBUSWARE_CONFIG_FROM_FILES=0` | Mutually exclusive config authority |

**Tri-state system keys** (empty = follow workflow YAML): optional stages and universal-critique panel overrides. Prefer workflow profile YAML in `configs/workflows/` for defaults; use env only for operator overrides.

**Parallelism:** `NIMBUSWARE_PARALLEL_WRITERS` (system), `NIMBUSWARE_MAX_PARALLEL_WRITERS` (user governor) — different layers; not duplicates.
- Store: `packages/nimbusware_env/settings_store.py`
- Resolver: `packages/nimbusware_env/settings_resolve.py`
- Helpers: `packages/nimbusware_env/env_flags.py`

Add new tunables to the catalog first, then read via `env_flags` / `settings_resolve`.

## Context efficiency (group: User — context efficiency)

| Key | Default | Notes |
|-----|---------|-------|
| `NIMBUSWARE_LLM_HISTORY_MAX_CHARS` | 2000 | Critique logs, tool history |
| `NIMBUSWARE_READ_MAX_CHARS` | 16000 | Agent read tool |
| `NIMBUSWARE_SHELL_OUTPUT_MAX_CHARS` | 4000 | Agent shell output |
| `NIMBUSWARE_AGENT_JIT_LOOP` | 1 | Multi-turn agent implement |
| `NIMBUSWARE_AGENT_TOOLS` | read,write,edit,grep,shell | Tool allowlist (`find`, `ls` optional) |
| `NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS` | 1 | Theater/timeline agent tool pruning |
| `NIMBUSWARE_AGENT_COMPACT` | 1 | Manual compaction API/MCP gate |
| `NIMBUSWARE_HANDOFF_MAX_CHARS` | 4000 | Cross-slice handoff cap |
| `NIMBUSWARE_HANDOFF_LLM_SUMMARY` | 0 | Optional LLM handoff merge |
| `NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED` | 1 | Campaign compaction |
| `NIMBUSWARE_CAMPAIGN_KEEP_RECENT_TOKENS` | 12000 | Recent verbatim window (HW override when unset) |
| `NIMBUSWARE_CAMPAIGN_RESERVE_TOKENS` | 8000 | Output reservation |
| `NIMBUSWARE_MEMORY_RETRIEVAL_K` | 5 | Memory chunks per slice (YAML may override) |
| `NIMBUSWARE_MEMORY_EXCERPT_MAX_CHARS` | 4000 | Injected memory excerpt cap |
| `NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD` | 0 | Rebuild FAISS after context-artifact bridge |
| `NIMBUSWARE_AXE_ENABLED` | 0 | axe-core in human-fidelity suite |
| `NIMBUSWARE_DEFAULT_MODEL` | (empty) | Fallback Ollama model when stage model unset |

**Fleet / scraper (system):** `NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_DEPTH` (100), `NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_IN_FLIGHT` (20), `NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE` (0).

Helpers: `agent_core.context_budget`, `nimbusware_orchestrator.prompt_tiers`, `nimbusware_orchestrator.context_compaction`.
