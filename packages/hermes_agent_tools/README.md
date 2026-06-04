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

Docker sandbox requires a local Docker CLI. Set `HERMES_SANDBOX_DOCKER_IMAGE` (default `python:3.11-slim`). When Docker is unavailable, commands fall back to host execution with a `[sandbox:docker-unavailable]` prefix.

Multi-tenant VM / k8s / E2B-style fleet sandboxes are **deferred** — docker covers Individual edition v1 (`HERMES_SANDBOX_BACKEND=docker`).

Implementation: [`sandbox.py`](sandbox.py), [`filesystem_jail.py`](filesystem_jail.py).
