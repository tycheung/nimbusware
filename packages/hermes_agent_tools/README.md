# hermes_agent_tools

Allowlisted tools for slice implement agent mode (file reads, bounded shell, etc.). Tool names and schemas are validated before orchestrator dispatch.

## Consumers

`hermes_orchestrator` agent-mode slices; contract tests under `tests/unit/test_agent_tools.py` and `tests/unit/test_agent_tools_runtime_coverage.py`.

## Safety layers

| Layer | Env | Behavior |
|-------|-----|----------|
| Filesystem jail | `HERMES_FILESYSTEM_JAIL=1` (default) | Restrict reads/writes to workspace |
| Sandbox backend | `HERMES_SANDBOX_BACKEND` | Where shell commands run (see below) |

## Sandbox backends (Individual v1)

| Value | Behavior |
|-------|----------|
| `none` | Shell runs on host inside jail (default) |
| `stub` | No subprocess; returns stub output for tests |
| `docker` | Opt-in: `docker run --rm --network none` with workspace bind-mount |
| `kubernetes` | Fleet: `kubectl exec` into `HERMES_SANDBOX_K8S_EXEC_POD` (falls back with prefix if unset) |
| `e2b` | Fleet: reserved E2B hook (`HERMES_E2B_API_KEY`); host fallback until remote API wired |

Docker sandbox requires a local Docker CLI. Set `HERMES_SANDBOX_DOCKER_IMAGE` (default `python:3.11-slim`). When Docker is unavailable, commands fall back to host execution with a `[sandbox:docker-unavailable]` prefix.

## Autonomous risk caps

Per-slice limits (frozen on `run.created` as `agent_tools_effective.risk_caps`):

| Env | Default | Purpose |
|-----|---------|---------|
| `HERMES_AGENT_MAX_TOOL_STEPS` | 20 | Max read/grep/write/shell steps |
| `HERMES_AGENT_MAX_SHELL_INVOCATIONS` | 5 | Max shell tool calls |
| `HERMES_AGENT_MAX_WRITE_BYTES` | 262144 | Total write payload bytes |

Implementation: [`sandbox.py`](sandbox.py), [`filesystem_jail.py`](filesystem_jail.py).
