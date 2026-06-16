from __future__ import annotations

from nimbusware_env.env_flags import nimbusware_workflow_profile

_PRODUCTION_PROFILE = "nimbusware_production"


def default_workflow_profile() -> str:
    return nimbusware_workflow_profile(default=_PRODUCTION_PROFILE)
