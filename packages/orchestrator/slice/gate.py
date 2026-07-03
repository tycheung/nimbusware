from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orchestrator.profiles.enforcement_profiles import EnforcementProfile
from orchestrator.slice.micro_slice import SlicePlan


@dataclass(frozen=True)
class SliceGateStep:
    name: str
    verdict: str
    detail: str = ""


@dataclass(frozen=True)
class SliceGateChainResult:
    slice_id: str
    passed: bool
    steps: tuple[SliceGateStep, ...]
    status: str

    def to_metadata(self) -> dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "slice_gate_verdict": "PASS" if self.passed else "FAIL",
            "slice_status": self.status,
            "slice_gate_steps": [
                {"name": s.name, "verdict": s.verdict, "detail": s.detail} for s in self.steps
            ],
        }


def apply_skip_verdict_policy(
    steps: tuple[SliceGateStep, ...],
    policy: str,
) -> tuple[SliceGateStep, ...]:
    if policy == "pass":
        return steps
    out: list[SliceGateStep] = []
    for step in steps:
        if step.verdict != "SKIP":
            out.append(step)
            continue
        if policy == "fail":
            out.append(
                SliceGateStep(
                    step.name,
                    "FAIL",
                    step.detail or "skipped step blocked by enforcement depth",
                ),
            )
        elif policy == "warn":
            out.append(
                SliceGateStep(
                    step.name,
                    "PASS",
                    f"warn: {step.detail or 'skipped'}",
                ),
            )
        else:
            out.append(step)
    return tuple(out)


def run_slice_gate_chain(
    plan: SlicePlan,
    *,
    verify_ok: bool,
    verify_detail: str = "",
    critique_verdicts: list[str] | None = None,
    tests_passed: bool | None = None,
    test_detail: str = "",
    e2e_passed: bool | None = None,
    e2e_detail: str = "",
    unanimous_required: bool = True,
    autopilot_level: int = 5,
    enforcement_profile: EnforcementProfile | None = None,
    resolution_callback: Any | None = None,
) -> SliceGateChainResult:
    steps: list[SliceGateStep] = []
    critique_verdicts = critique_verdicts or []

    v_verdict = "PASS" if verify_ok else "FAIL"
    steps.append(SliceGateStep("slice.verify", v_verdict, verify_detail))

    critique_fail = any(
        v.upper() == "FAIL" or v.upper().endswith(":FAIL") for v in critique_verdicts
    )
    resolution_detail = ""
    if critique_fail:
        from orchestrator.resolution_council import run_resolution_council

        findings = []
        for v in critique_verdicts:
            if v.upper() == "FAIL" or ":FAIL" in v.upper():
                kind = v.split(":", 1)[0] if ":" in v else "critic"
                findings.append({"kind": kind, "message": v, "severity": "info"})
        if resolution_callback is not None:
            resolution = resolution_callback(findings)
        else:
            resolution = run_resolution_council(findings=findings, autopilot_level=autopilot_level)
        if resolution.verdict.accord and not resolution.verdict.hard_block:
            critique_fail = False
            resolution_detail = resolution.verdict.detail
    c_verdict = "FAIL" if critique_fail else "PASS"
    critique_msg = ", ".join(critique_verdicts) if critique_verdicts else "no critiques"
    if resolution_detail:
        critique_msg = f"{critique_msg}; resolution={resolution_detail}"
    steps.append(
        SliceGateStep(
            "slice.critique",
            c_verdict,
            critique_msg,
        ),
    )

    if tests_passed is None:
        t_verdict = "SKIP"
        t_detail = "no scoped tests"
    else:
        t_verdict = "PASS" if tests_passed else "FAIL"
        t_detail = test_detail
    steps.append(SliceGateStep("slice.test", t_verdict, t_detail))

    if e2e_passed is None and not e2e_detail:
        e_verdict = "SKIP"
        e_detail = "e2e disabled"
    elif e2e_passed is None:
        e_verdict = "SKIP"
        e_detail = e2e_detail or "e2e skipped"
    else:
        e_verdict = "PASS" if e2e_passed else "FAIL"
        e_detail = e2e_detail
    steps.append(SliceGateStep("slice.e2e", e_verdict, e_detail))

    if enforcement_profile is not None:
        steps = list(
            apply_skip_verdict_policy(tuple(steps), enforcement_profile.skip_verdict_policy),
        )
    else:
        steps = list(steps)

    failing = [s for s in steps if s.verdict == "FAIL"]
    if unanimous_required and failing:
        passed = False
        status = "blocked"
    elif any(s.verdict == "FAIL" for s in steps):
        passed = False
        status = "blocked"
    else:
        passed = True
        status = "completed"

    steps.append(
        SliceGateStep(
            "slice.gate",
            "PASS" if passed else "FAIL",
            "unanimous" if unanimous_required else "majority",
        ),
    )
    return SliceGateChainResult(
        slice_id=plan.slice_id,
        passed=passed,
        steps=tuple(steps),
        status=status,
    )


def map_paths_to_test_targets(paths: tuple[str, ...]) -> list[str]:
    """Heuristic: map implementation paths to stack test files (v1)."""
    targets: list[str] = []
    for path in paths:
        p = path.replace("\\", "/")
        if p.endswith(".go") and not p.endswith("_test.go"):
            stem = p.removesuffix(".go").split("/")[-1]
            parent = "/".join(p.split("/")[:-1])
            candidate = f"{parent}/{stem}_test.go" if parent else f"{stem}_test.go"
            targets.append(candidate)
        elif p.endswith("_test.go"):
            targets.append(p)
        elif p.endswith(".java") and "src/main/java/" in p:
            test_path = p.replace("src/main/java/", "src/test/java/").removesuffix(".java")
            targets.append(f"{test_path}Test.java")
        elif p.endswith("Test.java"):
            targets.append(p)
        elif p.endswith(".py") and not p.startswith("tests/"):
            module = p.removesuffix(".py").replace("/", ".")
            targets.append(f"tests/test_{module.split('.')[-1]}.py")
        elif p.startswith("tests/"):
            targets.append(p)
    return list(dict.fromkeys(targets))
