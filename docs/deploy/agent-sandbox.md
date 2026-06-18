# Agent sandbox backends (Individual + Enterprise)

Nimbusware agent `shell` tool execution can run on the host (with filesystem jail), in a local Docker container, or on enterprise fleet isolation backends.

## Individual edition

| `NIMBUSWARE_SANDBOX_BACKEND` | Behavior |
|------------------------------|----------|
| `none` (default) | Host shell with `NIMBUSWARE_FILESYSTEM_JAIL=1` path denylist |
| `stub` | No-op sandbox for tests |
| `docker` | `docker run` with workspace bind-mount; requires local Docker CLI |

Set `NIMBUSWARE_SANDBOX_DOCKER_IMAGE` (default `python:3.11-slim`). When Docker is unavailable, commands fall back to host execution with a `[sandbox:docker-unavailable]` prefix.

Configure in Maker **Settings** or `.env` (see [env vars reference](../../docs/reference/env-vars.md)).

## Enterprise fleet

| Backend | Required configuration |
|---------|------------------------|
| `kubernetes` | `NIMBUSWARE_SANDBOX_K8S_EXEC_POD`, optional `NIMBUSWARE_SANDBOX_K8S_NAMESPACE`, `NIMBUSWARE_SANDBOX_K8S_WORKDIR` |
| `e2b` | `NIMBUSWARE_E2B_API_KEY` (install scope) |

Implementation: `packages/nimbusware_agent_tools/fleet_sandbox.py`. When fleet pod or E2B is unavailable, commands fall back to host+jail with a stderr prefix so operators can detect misconfiguration.

## Security notes

- Filesystem jail blocks `.env`, `.git`, and common secret paths regardless of sandbox backend.
- Fleet backends are **install-scoped** (not end-user toggles) to prevent cross-tenant escape in shared clusters.
- Docker sandbox is Individual v1 only; multi-tenant VM sandboxes remain a deferred v2 track (see `CONTRIBUTING.md`).

## Related docs

- [Enterprise buyer checklist](../enterprise-buyer.md)
- [Run dispatch fleet runbook](../../scripts/runbooks/run_dispatch_fleet_runbook.md)
- Package reference: [nimbusware_agent_tools README](../../packages/nimbusware_agent_tools/README.md)
