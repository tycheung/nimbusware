# agent_tools

Allowlisted tools for slice implement agent mode. The JIT loop (`agent_loop.py`) calls enabled tools across multiple LLM turns without upfront context preload. Tool results split into `llm_output` (model-facing) and `audit_output` (logs/projections). Stable rules load from `configs/prompts/agent_implement_stable.txt`.

## Consumers

`orchestrator` agent-mode slices; contract tests under `tests/unit/test_agent_tools.py` and `tests/unit/test_agent_tools_runtime_coverage.py`.

## Safety layers

| Layer | Env | Behavior |
|-------|-----|----------|
| Filesystem jail | `NIMBUSWARE_FILESYSTEM_JAIL=1` (default) | Restrict reads/writes to workspace |
| Sandbox backend | `NIMBUSWARE_SANDBOX_BACKEND` | Where shell commands run (see below) |

## Sandbox backends (Individual v1)

| Value | Behavior |
|-------|----------|
| `none` | Shell runs on host inside jail (default) |
| `stub` | No subprocess; returns stub output for tests |
| `docker` | Opt-in: `docker run --rm --network none` with workspace bind-mount |
| `kubernetes` | Fleet: `kubectl exec` into `NIMBUSWARE_SANDBOX_K8S_EXEC_POD` (falls back with prefix if unset) |
| `e2b` | Fleet: remote E2B VM when `NIMBUSWARE_E2B_API_KEY` + optional `e2b` package; host fallback otherwise |

Docker sandbox requires a local Docker CLI. Set `NIMBUSWARE_SANDBOX_DOCKER_IMAGE` (default `python:3.11-slim`). When Docker is unavailable, commands fall back to host execution with a `[sandbox:docker-unavailable]` prefix.

## Autonomous risk caps

Per-slice limits (frozen on `run.created` as `agent_tools_effective.risk_caps`):

| Env | Default | Purpose |
|-----|---------|---------|
| `NIMBUSWARE_AGENT_MAX_TOOL_STEPS` | 20 | Max read/grep/write/shell steps |
| `NIMBUSWARE_AGENT_MAX_SHELL_INVOCATIONS` | 5 | Max shell tool calls |
| `NIMBUSWARE_AGENT_MAX_WRITE_BYTES` | 262144 | Total write + net edit bytes |
| `NIMBUSWARE_AGENT_JIT_LOOP` | 1 | Multi-turn tool loop |
| `NIMBUSWARE_AGENT_TOOLS` | read,write,edit,grep,shell | Comma allowlist (`find`, `ls` optional) |
| `NIMBUSWARE_READ_MAX_CHARS` | 16000 | Read tool cap |
| `NIMBUSWARE_READ_OUTLINE_MIN_LINES` | 200 | Outline mode for large non-target Python files |
| `NIMBUSWARE_SHELL_OUTPUT_MAX_CHARS` | 4000 | Shell output cap |
| `NIMBUSWARE_TOOL_OFFLOAD_CHARS` | 5000 | Spill oversized tool output to `.cache/nimbusware/tool-output/` |
| `NIMBUSWARE_JIT_MICROCOMPACT_TURNS` | 8 | Keep last N tool results when microcompacting |
| `NIMBUSWARE_CONTEXT_DEDUP` | balanced | Supersede duplicate read/grep/shell results in loop history |
| `NIMBUSWARE_AGENT_COMPACT` | 1 / full | Handoff compaction; `full` enables L4 message summarize in loop |

`edit` performs single-occurrence replacements; prefer it over `write` for existing files.

Implementation: [`agent_loop.py`](agent_loop.py), [`tools.py`](tools.py), [`sandbox.py`](sandbox.py), [`filesystem_jail.py`](filesystem_jail.py). Context compaction helpers: `agent_core/tool_output_offload.py`, `agent_core/agent_full_compact.py`.
