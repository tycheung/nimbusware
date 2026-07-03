from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from env import find_repo_root
from maker.user_agent_overlay import prompt_addon_for_run_claims, save_user_agent_overlay
from orchestrator.collab_mesh_context import (
    clear_mesh_binding_context,
    set_mesh_binding_context,
)
from orchestrator.critique_routing import load_critique_router
from orchestrator.llm_slice import _custom_agent_prompt_from_rows
from orchestrator.registry import RoleRegistry

ROOT = find_repo_root()


def _disciplines_yaml(repo: Path) -> None:
    (repo / "configs" / "collab").mkdir(parents=True)
    (repo / "configs" / "collab" / "disciplines.yaml").write_text(
        """
disciplines:
  - id: backend
    display_name: Backend
    taxonomy_key: backend_writer
  - id: pm
    display_name: PM
    taxonomy_key: planner
""",
        encoding="utf-8",
    )


def test_overlay_composes_with_bound_role_custom_agent(tmp_path: Path) -> None:
    _disciplines_yaml(tmp_path)
    save_user_agent_overlay(
        "claimer-1",
        "pm",
        prompt_extension="Always cite acceptance criteria.",
        repo_root=tmp_path,
    )
    run_id = uuid4()
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "custom_agent": {
                    "id": "agent-planner",
                    "system_prompt_preview": "You are the team planner.",
                    "bound_role_id": "planner",
                },
            },
        },
        {
            "event_type": "workload.role_claimed",
            "event_id": str(uuid4()),
            "run_id": str(run_id),
            "occurred_at": "2026-06-26T12:00:00+00:00",
            "payload": {
                "agent_role": "planner",
                "claimer_user_id": "claimer-1",
                "provider_id": "ollama",
                "model_id": "llama",
            },
        },
    ]
    addon = prompt_addon_for_run_claims({"planner": "claimer-1"}, repo_root=tmp_path)
    assert "acceptance criteria" in addon
    with patch("env.find_repo_root", return_value=tmp_path):
        prompt = _custom_agent_prompt_from_rows(rows)
    assert "team planner" in prompt
    assert "acceptance criteria" in prompt


def test_mesh_overlay_appended_without_dropping_custom_agent() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "custom_agent": {
                    "system_prompt_preview": "Custom backend writer.",
                    "bound_role_id": "backend_writer",
                },
            },
        },
    ]
    set_mesh_binding_context(
        participant_overrides=None, agent_overlay_prompt="Prefer thin handlers."
    )
    try:
        prompt = _custom_agent_prompt_from_rows(rows)
    finally:
        clear_mesh_binding_context()
    assert "Custom backend writer" in prompt
    assert "thin handlers" in prompt


def test_overlay_merge_does_not_alter_critique_pairings() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    router = load_critique_router(ROOT)
    before = {k: router.pairing_for(k) for k in ("planner", "backend_writer")}
    set_mesh_binding_context(
        participant_overrides=None,
        actor_user_id="u1",
        agent_overlay_prompt="Wear a security hat when reviewing.",
    )
    try:
        rows = [
            {
                "event_type": "run.created",
                "metadata": {
                    "custom_agent": {
                        "system_prompt_preview": "Planner persona.",
                        "bound_role_id": "planner",
                    },
                },
            },
        ]
        _ = _custom_agent_prompt_from_rows(rows)
        after = {k: router.pairing_for(k) for k in ("planner", "backend_writer")}
    finally:
        clear_mesh_binding_context()
    assert before == after
    assert "product_reference_critic" in after["planner"]
    assert "domain_critic" in reg.known_taxonomy_keys()
