"""CI mypy path list (single source of truth for ci_check and GitHub Actions)."""

from __future__ import annotations

# Tranche C (fo730): core libraries — strict globally; enforced in CI.
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

# Tranche B (fo720): leaf read-model / client packages.
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

MYPY_CI_TARGETS: tuple[str, ...] = _SERVICES + _TRANCHE_B + _TRANCHE_C + _API_PILOT

if __name__ == "__main__":
    print(*MYPY_CI_TARGETS)
