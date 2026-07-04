# Context efficiency

Token-aware caps keep LLM prompts bounded without deleting raw audit events. ADRs: [006](adr/006-prompt-tiers.md), [007](adr/007-context-compaction.md), [008](adr/008-context-artifacts-file-cache.md), [031](adr/031-context-budget-telemetry.md), [032](adr/032-incremental-maker-progress-sse.md), [033](adr/033-structure-over-source-reads.md).

## Key flags

| Flag | Default | Purpose |
|------|---------|---------|
| `NIMBUSWARE_SLICE_BUDGET_PRESET` | standard | Context caps: packet, repo map, symbol sketch, LLM history |
| `NIMBUSWARE_READ_MAX_CHARS` | 16000 | Agent `read` tool output |
| `NIMBUSWARE_SHELL_OUTPUT_MAX_CHARS` | 4000 | Agent `shell` output |
| `NIMBUSWARE_AGENT_JIT_LOOP` | 1 | Multi-turn agent loop vs single-shot |
| `NIMBUSWARE_AGENT_TOOLS` | read,write,edit,grep,shell | Tool allowlist |
| `NIMBUSWARE_AGENT_COMPACT` | 1 | `POST /v1/runs/{id}/compact` and MCP compact |
| `NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED` | 1 | Summarize older handoffs in campaigns |
| `NIMBUSWARE_HANDOFF_LLM_SUMMARY` | 0 | Optional LLM handoff refinement |
| `NIMBUSWARE_THEATER_LLM_SUMMARY` | off | Optional theater summary when enabled |
| `NIMBUSWARE_MEMORY_INDEX_FIRST` | 0 | Inject memory index table before FAISS excerpts |
| `NIMBUSWARE_CONTEXT_DEDUP` | 1 | Dedupe repeated context blocks in agent loop |
| `NIMBUSWARE_OPENAI_PREFIX_REUSE` | 0 | OpenAI-compatible prefix-cache hint header |

Full catalog (264 keys): [operator-settings.md](../operator-settings.md) and `poetry run python scripts/ci/audit_operator_env.py`.

## Cache-aware prompts

`agent_core/prompt_tiers.py` assembles STABLE / CONTEXT / VOLATILE tiers and emits `cache_blocks` (text + tier metadata). The agent loop passes blocks through `ModelBindingResolver.chat_json()` to cloud providers; Anthropic requests use multi-block system content via `orchestrator/llm/prompt_cache.py`. Critique stages share a stable harness prefix in `orchestrator/critique/prompt_assembly.py`.

## Token telemetry

Each provider chat records in-process counters (`agent_core/token_telemetry.py`) and, when a run store is bound, persists rate-limited `context.budget.sampled` events (30s per run/stage) via `orchestrator/llm/budget_sample_emit.py`. Projections aggregate samples in `projections/builders/context_budget.py`.

## Read modes

The agent `read` tool selects `outline`, `digest`, or `full` based on file size and slice targets (`agent_core/read_outline.py`). Python outlines use AST; digest mode summarizes structure without full source. Campaign read staleness is tracked in `agent_core/read_staleness.py`.

## Maker Progress SSE

Run event streams use tail fetch (`store.list_run_events_since`) instead of replaying the full timeline on each poll. The API emits `progress_delta` events; the client merges deltas in `maker_web/static/js/tabs/progress.js`.

## APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/runs/{id}/context_budget` | Advisory budget chip on Maker Progress |
| `POST /v1/runs/{id}/compact` | Compact agent context (scopes: all, last_n, source_refs) |
| `POST /v1/runs/{id}/compactions/{id}/revert` | Revert compaction |
| `POST /v1/runs/{id}/replay-from` | Replay from checkpoint (re-enqueues campaign tick) |
| `GET/POST /v1/projects/{id}/context-artifacts` | Context artifact library |
| `POST /v1/runs/{id}/memory-chunks/{id}/insert` | Insert memory chunk into run |

Shared helpers: `packages/agent_core/context_budget.py`. Stable agent rules: `configs/prompts/agent_implement_stable.txt`. Skills: `configs/skills/`.
