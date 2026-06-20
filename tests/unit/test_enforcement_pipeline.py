from __future__ import annotations

from nimbusware_orchestrator.enforcement_pipeline import (
    active_enforcement_profile,
    e2e_required_for_profile,
    enforcement_wired_for_run,
    normalize_e2e_for_enforcement,
    security_scan_required,
)
from nimbusware_orchestrator.enforcement_profiles import resolve_enforcement_profile
from nimbusware_orchestrator.slice_gate import SliceGateStep, apply_skip_verdict_policy


def test_apply_skip_verdict_policy_fail() -> None:
    steps = (
        SliceGateStep("slice.test", "SKIP", "no scoped tests"),
        SliceGateStep("slice.e2e", "PASS", ""),
    )
    out = apply_skip_verdict_policy(steps, "fail")
    assert out[0].verdict == "FAIL"
    assert out[1].verdict == "PASS"


def test_normalize_e2e_required_when_disabled() -> None:
    profile = resolve_enforcement_profile(level=7)
    passed, detail = normalize_e2e_for_enforcement(None, "", profile, e2e_enabled=False)
    assert passed is False
    assert "required" in detail


def test_enforcement_level_flags() -> None:
    strict = resolve_enforcement_profile(level=6)
    assert security_scan_required(strict)
    assert e2e_required_for_profile(resolve_enforcement_profile(level=7))
    assert not e2e_required_for_profile(strict)


def test_enforcement_wired_when_flag_on(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_ENFORCEMENT_DEPTH", "1")
    assert enforcement_wired_for_run([])
    profile = active_enforcement_profile([])
    assert profile is not None
    assert profile.level >= 0
