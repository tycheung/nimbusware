from __future__ import annotations

from env.env_flags import nimbusware_workflow_profile

_DEFAULT_PROFILE = "micro_slice"


def default_workflow_profile() -> str:
    return nimbusware_workflow_profile(default=_DEFAULT_PROFILE)
