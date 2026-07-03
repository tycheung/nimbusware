from __future__ import annotations

from pathlib import Path

from config.materializer import ConfigMaterializer
from config.persist import load_custom_agent_registry, persist_custom_agent_registry
from config.seed import seed_config_from_repo
from config.store import InMemoryConfigStore
from env import find_repo_root
from extensions.custom_agents import CustomAgent


def test_custom_agents_roundtrip_via_materializer() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(repo, store)
    mat = ConfigMaterializer(repo, store=store, use_db=True)
    reg = mat.get_custom_agent_registry()
    assert reg.get("default_planner") is not None

    reg.upsert(
        CustomAgent(
            id="db_test_agent",
            display_name="DB Test",
            system_prompt="test prompt",
        ),
    )
    persist_custom_agent_registry(repo, reg, materializer=mat)
    mat.refresh("custom_agents")
    reloaded = load_custom_agent_registry(repo, materializer=mat)
    assert reloaded.get("db_test_agent") is not None
    assert reloaded.get("db_test_agent").display_name == "DB Test"
