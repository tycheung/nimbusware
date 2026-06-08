from __future__ import annotations

from uuid import uuid4

from nimbusware_orchestrator.context_artifacts import (
    bridge_artifact_to_memory_index,
    create_context_artifact,
)


def test_bridge_artifact_writes_memory_sidecar(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    artifact = create_context_artifact(
        project_id=uuid4(),
        title="Campaign summary",
        content="Merged handoff context for slice batch",
        kind="compaction",
    )
    from pathlib import Path

    result = bridge_artifact_to_memory_index(artifact, repo_root=tmp_path)
    assert Path(result["bridge_path"]).is_file()
    path = Path(result["bridge_path"])
    assert "Campaign summary" in path.read_text(encoding="utf-8")
