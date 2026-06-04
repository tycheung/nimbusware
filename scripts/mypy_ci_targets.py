"""CI mypy path list (single source of truth for ci_check and GitHub Actions)."""

from __future__ import annotations

# Tranche C: core libraries — strict globally; enforced in CI.
_TRANCHE_C = (
    "packages/agent_core",
    "packages/hermes_store",
    "packages/nimbusware_config",
    "packages/hermes_executor",
    "packages/hermes_extensions",
    "packages/hermes_memory",
    "packages/nimbusware_iam",
    "packages/nimbusware_env",
)

# Tranche B: leaf read-model / client packages.
_TRANCHE_B = (
    "packages/nimbusware_projections",
    "packages/nimbusware_client",
    "packages/hermes_agent_tools",
)

_SERVICES = (
    "packages/nimbusware_console/services",
    "packages/nimbusware_maker/services",
)

_API_PILOT = (
    "packages/nimbusware_api/routes/ollama.py",
    "packages/nimbusware_api/schemas/ollama.py",
    "packages/nimbusware_api/errors.py",
)

# Tranche D (fo732): API read layer + enterprise routes that pass strict mypy.
_TRANCHE_D = (
    "packages/nimbusware_api/read_models",
    "packages/nimbusware_api/facade.py",
    "packages/nimbusware_api/deps.py",
    "packages/nimbusware_api/routes/enterprise",
    "packages/nimbusware_api/routes/personas_helpers.py",
)

# UI packages checked under narrowed ignore overrides (not blanket .*).
_UI_STRICT = (
    "packages/nimbusware_console",
    "packages/nimbusware_maker",
)

# Tranche E: orchestrator strict islands (remaining mixins under blanket _pipeline.* ignore).
_TRANCHE_E = (
    "packages/hermes_orchestrator/ollama_manage.py",
    "packages/hermes_orchestrator/ollama_user_policy.py",
    "packages/hermes_orchestrator/preflight.py",
    "packages/hermes_orchestrator/merge.py",
    "packages/hermes_orchestrator/workflow_profiles.py",
    "packages/hermes_orchestrator/_pipeline/base.py",
    "packages/hermes_orchestrator/_pipeline/_helpers.py",
    "packages/hermes_orchestrator/_pipeline/create_run.py",
    "packages/hermes_orchestrator/_pipeline/micro_slice.py",
    "packages/hermes_orchestrator/_pipeline/lifecycle_verify.py",
    "packages/hermes_orchestrator/_pipeline/writers.py",
    "packages/hermes_orchestrator/_pipeline/lifecycle_plan.py",
    "packages/hermes_orchestrator/_pipeline/optional_critique.py",
    "packages/hermes_orchestrator/_pipeline/escalation.py",
    "packages/hermes_orchestrator/_pipeline/critique_gates_helpers.py",
    "packages/hermes_orchestrator/_pipeline/critique_gates_optional_emit.py",
    "packages/hermes_orchestrator/_pipeline/critique_gates_stage_failed.py",
    "packages/hermes_orchestrator/_pipeline/critique_gates.py",
    "packages/hermes_orchestrator/_pipeline/lifecycle.py",
    "packages/hermes_orchestrator/_pipeline/lifecycle_start.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages_research.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages_stitch.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages_integrator.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages_integration.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages_self_refinement.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages_agent_evaluator.py",
    "packages/hermes_orchestrator/_pipeline/optional_stages.py",
    "packages/hermes_orchestrator/_pipeline/compose.py",
    "packages/hermes_orchestrator/_pipeline/protocol_hosts.py",
    "packages/hermes_orchestrator/_pipeline/pipeline_scraper.py",
    "packages/hermes_orchestrator/_pipeline/dev_factory.py",
    "packages/hermes_orchestrator/_pipeline/__init__.py",
)

# Services are included via _UI_STRICT whole-package checks (avoid duplicate module paths).
MYPY_CI_TARGETS: tuple[str, ...] = (
    _TRANCHE_B + _TRANCHE_C + _API_PILOT + _TRANCHE_D + _UI_STRICT + _TRANCHE_E
)

if __name__ == "__main__":
    print(*MYPY_CI_TARGETS)
