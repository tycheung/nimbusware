# hermes_agent_tools

Allowlisted tools exposed to slice implement agent mode (file reads, bounded shell, etc.). Tool names and schemas are validated before orchestrator dispatch.

## Consumers

`hermes_orchestrator` agent-mode slices; contract tests under `tests/unit/test_agent_tools.py` and `tests/unit/test_agent_tools_runtime_coverage.py`.

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).
