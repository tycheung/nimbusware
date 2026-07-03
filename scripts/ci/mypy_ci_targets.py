"""CI mypy path list (single source of truth for ci_check and GitHub Actions)."""

from __future__ import annotations

# Tranche C: core libraries — strict globally; enforced in CI.
_TRANCHE_C = (
    "packages/agent_core",
    "packages/store",
    "packages/config",
    "packages/executor",
    "packages/extensions",
    "packages/memory",
    "packages/iam",
    "packages/env",
)

# Tranche B: leaf read-model / client packages.
_TRANCHE_B = (
    "packages/projections",
    "packages/client",
    "packages/agent_tools",
)

_SERVICES = (
    "packages/console/services",
    "packages/maker/services",
)

_API_PILOT = (
    "packages/api/routes/ollama.py",
    "packages/api/schemas/ollama.py",
    "packages/api/errors.py",
)

# Tranche D (fo732): API list helpers + enterprise routes that pass strict mypy.
_TRANCHE_D = (
    "packages/api/routes/runs/list_helpers.py",
    "packages/api/facade.py",
    "packages/api/deps.py",
    "packages/api/routes/enterprise",
    "packages/api/routes/personas_helpers.py",
)

# UI packages checked under narrowed ignore overrides (not blanket .*).
_UI_STRICT = (
    "packages/console",
    "packages/maker",
)

# Tranche E: orchestrator strict islands (remaining mixins under blanket _pipeline.* ignore).
_TRANCHE_E = (
    "packages/orchestrator/routing/manage.py",
    "packages/orchestrator/routing/user_policy.py",
    "packages/orchestrator/preflight.py",
    "packages/orchestrator/merge.py",
    "packages/orchestrator/workflow/profiles.py",
    "packages/orchestrator/_pipeline/base.py",
    "packages/orchestrator/_pipeline/_helpers.py",
    "packages/orchestrator/_pipeline/_helpers_std.py",
    "packages/orchestrator/_pipeline/_helpers_bundle_critique.py",
    "packages/orchestrator/_pipeline/_helpers_bundle_runtime.py",
    "packages/orchestrator/_pipeline/_helpers_bundle_workflow.py",
    "packages/orchestrator/_pipeline/create_run.py",
    "packages/orchestrator/_pipeline/micro_slice.py",
    "packages/orchestrator/_pipeline/lifecycle_verify.py",
    "packages/orchestrator/_pipeline/writers.py",
    "packages/orchestrator/_pipeline/lifecycle_plan.py",
    "packages/orchestrator/_pipeline/optional_critique.py",
    "packages/orchestrator/_pipeline/escalation.py",
    "packages/orchestrator/_pipeline/critique_gates_helpers.py",
    "packages/orchestrator/_pipeline/critique_gates_optional_emit.py",
    "packages/orchestrator/_pipeline/critique_gates_stage_failed.py",
    "packages/orchestrator/_pipeline/critique_gates.py",
    "packages/orchestrator/_pipeline/lifecycle.py",
    "packages/orchestrator/_pipeline/lifecycle_start.py",
    "packages/orchestrator/_pipeline/optional_stages_research.py",
    "packages/orchestrator/_pipeline/optional_stages_stitch.py",
    "packages/orchestrator/_pipeline/optional_stages_integrator.py",
    "packages/orchestrator/_pipeline/optional_stages_integration.py",
    "packages/orchestrator/_pipeline/optional_stages_self_refinement.py",
    "packages/orchestrator/_pipeline/optional_stages_agent_evaluator.py",
    "packages/orchestrator/_pipeline/optional_stages.py",
    "packages/orchestrator/_pipeline/compose.py",
    "packages/orchestrator/_pipeline/protocol_hosts.py",
    "packages/orchestrator/_pipeline/pipeline_scraper.py",
    "packages/orchestrator/_pipeline/dev_factory.py",
    "packages/orchestrator/_pipeline/__init__.py",
    "packages/orchestrator/_pipeline/campaign_dispatch.py",
    "packages/orchestrator/campaign/driver.py",
    "packages/orchestrator/campaign/campaign.py",
    "packages/orchestrator/campaign/generator.py",
    "packages/orchestrator/completion_evaluator.py",
    "packages/orchestrator/workflow/campaign.py",
    "packages/orchestrator/campaign/safety.py",
    "packages/orchestrator/campaign/slice_selector.py",
    "packages/orchestrator/maintenance_refactor.py",
    "packages/orchestrator/maintenance_architecture.py",
    "packages/orchestrator/context_compaction.py",
)

# Tranche F: orchestrator root modules + API bundles/chat routes.
_TRANCHE_F = (
    "packages/orchestrator/profiles/autopilot_profiles.py",
    "packages/orchestrator/slice/executor.py",
    "packages/orchestrator/slice/plan.py",
    "packages/orchestrator/slice/verify.py",
    "packages/orchestrator/workflow/universal_critique.py",
    "packages/api/routes/bundles.py",
    "packages/api/routes/bundles_helpers.py",
    "packages/api/routes/bundles_search.py",
    "packages/api/routes/chat.py",
    "packages/api/routes/chat_session.py",
)

_TRANCHE_MCP = ("packages/mcp",)

# Services are included via _UI_STRICT whole-package checks (avoid duplicate module paths).
MYPY_CI_TARGETS: tuple[str, ...] = (
    _TRANCHE_B
    + _TRANCHE_C
    + _API_PILOT
    + _TRANCHE_D
    + _UI_STRICT
    + _TRANCHE_E
    + _TRANCHE_F
    + _TRANCHE_MCP
)

if __name__ == "__main__":
    print(*MYPY_CI_TARGETS)
