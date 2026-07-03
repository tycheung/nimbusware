from __future__ import annotations

from orchestrator.context_artifacts import (
    clear_context_artifacts_memory,
    create_context_artifact,
    list_context_artifacts_for_actor,
)
from orchestrator.launch.launch_evaluator import evaluate_workspace_rubric


def test_list_context_artifacts_for_actor_filters_private() -> None:
    clear_context_artifacts_memory()
    pid = "proj-1"
    create_context_artifact(
        project_id=pid,
        title="mine",
        content="private note",
        owner_user_id="alice",
        visibility="private",
    )
    create_context_artifact(
        project_id=pid,
        title="shared",
        content="team note",
        owner_user_id="bob",
        visibility="project",
    )
    alice_rows = list_context_artifacts_for_actor(pid, "alice")
    assert any(r.title == "mine" for r in alice_rows)
    assert any(r.title == "shared" for r in alice_rows)
    bob_rows = list_context_artifacts_for_actor(pid, "bob")
    assert not any(r.title == "mine" for r in bob_rows)
    assert any(r.title == "shared" for r in bob_rows)


def test_launch_eval_plain_summary(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# app", encoding="utf-8")
    card = evaluate_workspace_rubric(tmp_path)
    assert card.plain_summary
    assert "launch" in card.plain_summary.lower()
