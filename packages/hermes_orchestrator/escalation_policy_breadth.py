"""Escalation policy breadth metrics for operators (§14 #19)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from hermes_orchestrator.merge import load_yaml

_VERIFICATION_KEYS = (
    "auto_escalate_after_cumulative_findings",
    "notice_escalate_at_cumulative_findings",
    "escalate_on_first_verifier_failure",
    "escalate_after_cumulative_stage_failures",
    "escalate_after_cumulative_gate_failures",
    "escalate_after_cumulative_high_severity_findings",
)


def escalation_policy_breadth(repo_root: Path) -> dict[str, Any]:
    """Summarize how many escalation triggers are configured in policy YAML."""
    path = repo_root / "configs" / "escalation" / "policy.yaml"
    if not path.is_file():
        return {
            "policy_path_exists": False,
            "active_verification_triggers": 0,
            "anti_deadlock_enabled": False,
        }
    try:
        raw = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError) as err:
        return {
            "policy_path_exists": True,
            "policy_load_error": str(err),
            "active_verification_triggers": 0,
            "anti_deadlock_enabled": False,
        }
    verification = raw.get("verification")
    active = 0
    if isinstance(verification, dict):
        for key in _VERIFICATION_KEYS:
            val = verification.get(key)
            if val is True or (isinstance(val, int) and val > 0):
                active += 1
    ad = raw.get("anti_deadlock")
    ad_enabled = isinstance(ad, dict) and bool(ad.get("enabled", False))
    stall = int(raw.get("deadlock_escalation_after_minutes", 0) or 0)
    return {
        "policy_path_exists": True,
        "active_verification_triggers": active,
        "anti_deadlock_enabled": ad_enabled,
        "deadlock_escalation_after_minutes": stall if stall > 0 else None,
        "max_retries_per_stage": raw.get("max_retries_per_stage"),
    }
