# Context efficiency

Token-aware caps keep LLM prompts bounded without deleting raw audit events. ADRs: [006](adr/006-prompt-tiers.md), [007](adr/007-context-compaction.md), [008](adr/008-context-artifacts-file-cache.md).

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

Full catalog (243 keys): [operator-settings.md](../operator-settings.md) and `poetry run python scripts/ci/audit_operator_env.py`.

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
