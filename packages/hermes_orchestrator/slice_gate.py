"""Per-slice verify → critique → test → gate chain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_orchestrator.micro_slice import SlicePlan


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


def run_slice_gate_chain(
    plan: SlicePlan,
    *,
    verify_ok: bool,
    verify_detail: str = "",
    critique_verdicts: list[str] | None = None,
    tests_passed: bool | None = None,
    test_detail: str = "",
    unanimous_required: bool = True,
) -> SliceGateChainResult:
    """Deterministic per-slice gate: all steps must pass before next slice."""
    steps: list[SliceGateStep] = []
    critique_verdicts = critique_verdicts or []

    v_verdict = "PASS" if verify_ok else "FAIL"
    steps.append(SliceGateStep("slice.verify", v_verdict, verify_detail))

    critique_fail = any(v.upper() == "FAIL" for v in critique_verdicts)
    c_verdict = "FAIL" if critique_fail else "PASS"
    steps.append(
        SliceGateStep(
            "slice.critique",
            c_verdict,
            ", ".join(critique_verdicts) if critique_verdicts else "no critiques",
        ),
    )

    if tests_passed is None:
        t_verdict = "SKIP"
        t_detail = "no scoped tests"
    else:
        t_verdict = "PASS" if tests_passed else "FAIL"
        t_detail = test_detail
    steps.append(SliceGateStep("slice.test", t_verdict, t_detail))

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
    """Heuristic: map implementation paths to pytest node ids (v1)."""
    targets: list[str] = []
    for path in paths:
        p = path.replace("\\", "/")
        if p.endswith(".py") and not p.startswith("tests/"):
            module = p.removesuffix(".py").replace("/", ".")
            targets.append(f"tests/test_{module.split('.')[-1]}.py")
        elif p.startswith("tests/"):
            targets.append(p)
    return list(dict.fromkeys(targets))
