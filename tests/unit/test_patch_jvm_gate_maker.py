from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from maker.intent.requirements import build_requirements_artifact
from maker.slice_workflow import (
    apply_pending_slice,
    approve_run_plan,
    prepare_next_pending_slice,
)
from orchestrator.pipeline import make_dev_orchestrator

_REPO = Path(__file__).resolve().parents[2]
_JVM_FIXTURE = _REPO / "tests/fixtures/repos/tiny_jvm_app"


@pytest.mark.skipif(
    shutil.which("mvn") is None or shutil.which("java") is None,
    reason="maven/java toolchain not installed",
)
def test_patch_jvm_stub_apply_passes_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SLICE_IMPLEMENT", "stub")
    monkeypatch.setenv("NIMBUSWARE_SLICE_AUTO_ADVANCE", "0")
    monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", "1")

    ws = tmp_path / "tiny_jvm_app"
    shutil.copytree(_JVM_FIXTURE, ws)
    orch, store = make_dev_orchestrator(_REPO)
    run_id = orch.create_run(
        "patch_jvm",
        requirements=build_requirements_artifact(
            business_prompt="Fix failing JVM calculator test",
        ),
        project_id=uuid4(),
        project_name="PatchJVM",
        project_workspace_path=str(ws),
        project_template="attach",
        patch_context={"failing_test": "src/test/java/com/example/CalculatorTest.java"},
    )
    approve_run_plan(orch, run_id)
    prep = prepare_next_pending_slice(orch, run_id)
    assert prep["status"] == "awaiting_approval"
    slice_id = prep["pending"]["slice_id"]
    os.environ["NIMBUSWARE_SKIP_PREFLIGHT"] = "1"
    result = apply_pending_slice(orch, run_id, slice_id)
    assert result["status"] == "applied"
    assert result.get("gate_passed") is True, store.list_run_events(str(run_id))[-3:]
