# hermes_agent_tools

Allowlisted tools exposed to slice implement agent mode (file reads, bounded shell, etc.). Tool names and schemas are validated before orchestrator dispatch.

## Consumers

`hermes_orchestrator` agent-mode slices; contract tests under `tests/agent_tools/`.

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).
