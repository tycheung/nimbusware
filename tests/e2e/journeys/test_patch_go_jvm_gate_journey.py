from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def _gate_failure_detail(journey_client: JourneyClient) -> str:
    for ev in reversed(journey_client.timeline()):
        meta = ev.get("metadata") or {}
        if meta.get("slice_gate_steps"):
            return str(meta.get("slice_gate_steps"))
        if meta.get("slice_gate_verdict") == "FAIL":
            return str(meta)
    return "no slice gate metadata in timeline"


def _fix_go_calculator(ws: Path) -> None:
    target = ws / "calculator.go"
    target.write_text(
        "package calculator\n\nfunc Add(a, b int) int {\n\treturn a + b\n}\n",
        encoding="utf-8",
    )


def _fix_jvm_calculator(ws: Path) -> None:
    target = ws / "src/main/java/com/example/Calculator.java"
    target.write_text(
        "package com.example;\n\npublic final class Calculator {\n"
        "    private Calculator() {}\n\n"
        "    public static int add(int a, int b) {\n"
        "        return a + b;\n"
        "    }\n}\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("fixture_name", "profile", "failing_test", "fix_fn"),
    [
        (
            "tiny_go_app",
            "patch_go",
            "calculator_test.go",
            _fix_go_calculator,
        ),
        (
            "tiny_jvm_app",
            "patch_jvm",
            "src/test/java/com/example/CalculatorTest.java",
            _fix_jvm_calculator,
        ),
    ],
)
def test_patch_stack_gate_pass_on_fixed_fixture(
    journey_client: JourneyClient,
    tmp_path: Path,
    fixture_name: str,
    profile: str,
    failing_test: str,
    fix_fn,
) -> None:
    if fixture_name == "tiny_go_app" and shutil.which("go") is None:
        pytest.skip("go toolchain not installed")
    if fixture_name == "tiny_jvm_app" and (
        shutil.which("mvn") is None or shutil.which("java") is None
    ):
        pytest.skip("maven/java toolchain not installed")

    ws = copy_fixture_repo(fixture_name, tmp_path / fixture_name)
    fix_fn(ws)
    journey_client.attach_project(ws, name=f"PatchGate-{fixture_name}")
    run_resp = journey_client.client.post(
        "/v1/runs",
        json={
            "workflow_profile": profile,
            "project_id": journey_client.project_id,
            "requirements": {"business_prompt": f"Fix failing test in {fixture_name}"},
            "patch_context": {"failing_test": failing_test},
        },
    )
    assert run_resp.status_code == 200, run_resp.text
    journey_client.run_id = str(run_resp.json()["run_id"])

    pending = journey_client.get_pending()
    if pending.get("plan_approved") is False:
        journey_client.approve_plan()
    prep = journey_client.prepare_slice()
    if prep.get("status") != "awaiting_approval":
        pytest.skip(f"no pending slice in this environment: {prep}")
    slice_id = prep["pending"]["slice_id"]
    applied = journey_client.apply_slice(slice_id)
    assert applied["status"] == "applied"
    assert applied.get("gate_passed") is True, _gate_failure_detail(journey_client)
