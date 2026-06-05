"""Read auto-escalation thresholds from ``configs/escalation/policy.yaml``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.merge import load_yaml


def _escalation_policy_raw(
    repo_root: Path,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            return config_materializer.get_escalation_policy()
        except KeyError:
            return None
    path = repo_root / "configs" / "escalation" / "policy.yaml"
    if not path.is_file():
        return None
    return load_yaml(path)


def load_auto_escalate_after_cumulative_findings(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> int | None:
    raw = _escalation_policy_raw(repo_root, config_materializer)
    if raw is None:
        return None
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return None
    n = ver.get("auto_escalate_after_cumulative_findings")
    if isinstance(n, int) and n >= 1:
        return n
    return None


def load_notice_escalate_at_cumulative_findings(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> int | None:
    """Optional softer signal: emit ``run.escalated`` once at this cumulative finding count."""
    raw = _escalation_policy_raw(repo_root, config_materializer)
    if raw is None:
        return None
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return None
    n = ver.get("notice_escalate_at_cumulative_findings")
    if isinstance(n, int) and n >= 1:
        return n
    return None


def load_escalate_after_cumulative_stage_failures(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> int | None:
    """Emit one ``run.escalated`` when cumulative ``stage.failed`` reaches this count."""
    raw = _escalation_policy_raw(repo_root, config_materializer)
    if raw is None:
        return None
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return None
    n = ver.get("escalate_after_cumulative_stage_failures")
    if isinstance(n, int) and n >= 1:
        return n
    return None


def load_escalate_after_cumulative_gate_failures(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> int | None:
    """Emit one ``run.escalated`` when cumulative FAIL ``gate.decision.emitted`` reaches this."""
    raw = _escalation_policy_raw(repo_root, config_materializer)
    if raw is None:
        return None
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return None
    n = ver.get("escalate_after_cumulative_gate_failures")
    if isinstance(n, int) and n >= 1:
        return n
    return None


def load_escalate_after_cumulative_high_severity_findings(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> int | None:
    """Emit one ``run.escalated`` when cumulative HIGH/BLOCKER ``finding.created`` reaches this."""
    raw = _escalation_policy_raw(repo_root, config_materializer)
    if raw is None:
        return None
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return None
    n = ver.get("escalate_after_cumulative_high_severity_findings")
    if isinstance(n, int) and n >= 1:
        return n
    return None
