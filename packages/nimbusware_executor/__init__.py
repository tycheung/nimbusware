"""Windows-first execution helpers and egress policy checks."""

from nimbusware_executor.egress import assert_egress_allowed, host_matches_allowlist
from nimbusware_executor.windows import run_subprocess

__all__ = [
    "assert_egress_allowed",
    "host_matches_allowlist",
    "run_subprocess",
]
