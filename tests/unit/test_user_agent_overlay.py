from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_maker.user_agent_overlay import (
    load_user_agent_overlays,
    prompt_addon_for_run_claims,
    prompt_extension_for_taxonomy_key,
    save_user_agent_overlay,
)


def test_save_and_load_agent_overlay(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "configs" / "collab").mkdir(parents=True)
    (repo / "configs" / "collab" / "disciplines.yaml").write_text(
        """
disciplines:
  - id: backend
    display_name: Backend
    taxonomy_key: backend_writer
""",
        encoding="utf-8",
    )
    save_user_agent_overlay(
        "user-1",
        "backend",
        prompt_extension="Prefer FastAPI idioms.",
        repo_root=repo,
    )
    body = load_user_agent_overlays("user-1", repo_root=repo)
    assert body["overlays"]["backend"]["prompt_extension"] == "Prefer FastAPI idioms."


def test_prompt_extension_for_taxonomy_key(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "configs" / "collab").mkdir(parents=True)
    (repo / "configs" / "collab" / "disciplines.yaml").write_text(
        """
disciplines:
  - id: frontend
    display_name: Frontend
    taxonomy_key: frontend_writer
""",
        encoding="utf-8",
    )
    save_user_agent_overlay(
        "user-2",
        "frontend",
        prompt_extension="Use accessible React patterns.",
        repo_root=repo,
    )
    ext = prompt_extension_for_taxonomy_key("user-2", "frontend_writer", repo_root=repo)
    assert "React" in ext


def test_prompt_addon_for_run_claims_dedupes(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "configs" / "collab").mkdir(parents=True)
    (repo / "configs" / "collab" / "disciplines.yaml").write_text(
        """
disciplines:
  - id: backend
    display_name: Backend
    taxonomy_key: backend_writer
""",
        encoding="utf-8",
    )
    save_user_agent_overlay(
        "user-3",
        "backend",
        prompt_extension="Keep handlers thin.",
        repo_root=repo,
    )
    addon = prompt_addon_for_run_claims({"backend_writer": "user-3"}, repo_root=repo)
    assert "handlers thin" in addon


def test_save_unknown_discipline_raises(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "configs" / "collab").mkdir(parents=True)
    (repo / "configs" / "collab" / "disciplines.yaml").write_text(
        "disciplines: []\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unknown discipline"):
        save_user_agent_overlay("user-4", "not-a-discipline", prompt_extension="x", repo_root=repo)
