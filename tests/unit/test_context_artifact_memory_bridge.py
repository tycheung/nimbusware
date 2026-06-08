from __future__ import annotations

from uuid import uuid4

from nimbusware_memory.faiss_index import memory_faiss_index_ready
from nimbusware_memory.manifest import default_memory_index_dir
from nimbusware_orchestrator.context_artifacts import (
    bridge_artifact_to_memory_index,
    create_context_artifact,
    maybe_rebuild_memory_faiss_from_bridges,
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
    assert "faiss_rebuild" not in result


def test_faiss_rebuild_from_bridge_when_env_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("NIMBUSWARE_MEMORY_INDEX_DIR", str(tmp_path / "mem-index"))
    monkeypatch.setenv("NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD", "1")
    project_id = uuid4()
    artifact = create_context_artifact(
        project_id=project_id,
        title="Bridge chunk",
        content="Context artifact excerpt for vector search",
        kind="compaction",
    )
    bridge_artifact_to_memory_index(artifact, repo_root=tmp_path)
    rebuilt = maybe_rebuild_memory_faiss_from_bridges(str(project_id), repo_root=tmp_path)
    assert rebuilt is not None
    assert rebuilt.get("rebuilt") is True
    index_dir = default_memory_index_dir(tmp_path)
    assert memory_faiss_index_ready(index_dir) or (index_dir / "manifest.json").is_file()


def test_faiss_rebuild_skipped_without_env(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD", raising=False)
    assert maybe_rebuild_memory_faiss_from_bridges("proj", repo_root=tmp_path) is None
