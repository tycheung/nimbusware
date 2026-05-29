"""Windows-first execution helpers and egress policy checks ."""

from hermes_executor.egress import assert_egress_allowed, host_matches_allowlist
from hermes_executor.windows import run_subprocess

__all__ = [
    "assert_egress_allowed",
    "host_matches_allowlist",
    "run_subprocess",
]
