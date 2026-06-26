from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.refactor_proposal import (
    build_refactor_proposal,
    orphan_gate_exceeded,
)
from nimbusware_orchestrator.refactor_stage import emit_refactor_stage_and_critique
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.workflow_refactor import RefactorWorkflowBlock
from nimbusware_store.memory import InMemoryEventStore

_REPO = Path(__file__).resolve().parents[2]


def test_orphan_gate_exceeded() -> None:
    assert orphan_gate_exceeded({"orphan_count": 3}, orphan_gate_max=2) is True
    assert orphan_gate_exceeded({"orphan_count": 2}, orphan_gate_max=2) is False
    assert orphan_gate_exceeded({"orphan_count": 99}, orphan_gate_max=None) is False


def test_build_refactor_proposal_orphan_target(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    pkg = ws / "packages" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "used.py").write_text("import demo.helper\n", encoding="utf-8")
    (pkg / "helper.py").write_text("A = 1\n", encoding="utf-8")
    (pkg / "lonely.py").write_text("B = 2\n", encoding="utf-8")

    proposal = build_refactor_proposal(
        ws,
        ws,
        RefactorWorkflowBlock(enabled=True, stub_only=False),
    )
    assert proposal["proposal_kind"] == "orphan_fixup"
    assert proposal["orphan_count"] >= 1
    assert proposal["patch_artifact"] not in ("[]", "")


def test_refactor_orphan_gate_fails_critique(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    pkg = ws / "packages" / "demo"
    pkg.mkdir(parents=True)
    for idx in range(3):
        (pkg / f"orphan_{idx}.py").write_text(f"V{idx} = {idx}\n", encoding="utf-8")

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_REPO / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _REPO / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    failed = emit_refactor_stage_and_critique(
        store,
        registry,
        router,
        run_id=run_id,
        block=RefactorWorkflowBlock(enabled=True, stub_only=False, orphan_gate_max=0),
        workspace=ws,
    )
    assert failed is True
    rows = store.list_run_events(str(run_id))
    gate = next(
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "refactor.critique"
    )
    assert str((gate.get("payload") or {}).get("verdict")).upper() == "FAIL"


def test_refactor_llm_patch_path(monkeypatch: object, tmp_path: Path) -> None:
    from uuid import uuid4

    from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
    from nimbusware_orchestrator.refactor_stage import emit_refactor_stage_and_critique
    from nimbusware_orchestrator.registry import RoleRegistry
    from nimbusware_store.memory import InMemoryEventStore

    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "orphan.py").write_text("X = 1\n", encoding="utf-8")

    def _fake_ollama(**_kwargs: object) -> dict[str, object]:
        return {
            "summary": "Wire orphan module",
            "target_paths": ["orphan.py"],
            "patch_artifact": [{"op": "add", "path": "orphan.py", "value": "# wired"}],
        }

    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setattr(
        "nimbusware_orchestrator.llm.common.ollama_chat_json_via_plan_patch",
        _fake_ollama,
    )
    monkeypatch.setattr(
        "nimbusware_env.env_flags.nimbusware_use_llm_enabled",
        lambda: True,
    )

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_REPO / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _REPO / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    emit_refactor_stage_and_critique(
        store,
        registry,
        router,
        run_id=run_id,
        block=RefactorWorkflowBlock(enabled=True, stub_only=False, llm_enabled=True),
        workspace=ws,
    )
    started = next(
        r
        for r in store.list_run_events(str(run_id))
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "refactor"
    )
    meta = (started.get("metadata") or {}).get("refactor") or {}
    assert meta.get("mode") == "llm_patch"
    assert meta.get("patch_artifact") not in ("[]", "")
