from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.escalation_policy_breadth import escalation_policy_breadth

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_escalation_policy_breadth_reads_repo_policy() -> None:
    b = escalation_policy_breadth(ROOT)
    assert b["policy_path_exists"] is True
    assert b["anti_deadlock_enabled"] is True
    assert isinstance(b["active_verification_triggers"], int)


def test_escalation_policy_breadth_malformed_yaml(tmp_path: Path) -> None:
    pol = tmp_path / "configs" / "escalation"
    pol.mkdir(parents=True)
    (pol / "policy.yaml").write_text(": bad\n", encoding="utf-8")
    b = escalation_policy_breadth(tmp_path)
    assert b.get("policy_load_error")


def test_anti_deadlock_escalation_includes_policy_breadth_metadata() -> None:
    from unittest.mock import patch

    from nimbusware_orchestrator.pipeline import make_dev_orchestrator

    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 1, 99),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch._maybe_emit_anti_deadlock_escalation(rid)  # noqa: SLF001
    esc = [r for r in mem.list_run_events(str(rid)) if r.get("event_type") == "run.escalated"]
    assert esc
    meta = esc[-1].get("metadata") or {}
    breadth = meta.get("escalation_policy_breadth") or {}
    assert breadth.get("policy_path_exists") is True
