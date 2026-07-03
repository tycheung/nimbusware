from __future__ import annotations

import yaml

from env import find_repo_root
from maker.quick_mode import (
    DEFAULT_QUICK_WORKFLOW,
    QUICK_MODE_ENV,
    apply_quick_mode_env,
    quick_mode_enabled,
)
from orchestrator.runtime_bootstrap import build_runtime_orchestrator
from store.memory import InMemoryEventStore


def test_apply_quick_mode_env_clears_database_url(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://localhost/nimbusware")
    env: dict[str, str] = {}
    apply_quick_mode_env(env)
    assert env.get(QUICK_MODE_ENV) == "1"
    assert "NIMBUSWARE_DATABASE_URL" not in env
    assert env.get("NIMBUSWARE_SKIP_PREFLIGHT") == "1"
    assert env.get("NIMBUSWARE_CONFIG_FROM_FILES") == "1"
    assert env.get("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE") == DEFAULT_QUICK_WORKFLOW


def test_quick_mode_enabled_after_apply(monkeypatch) -> None:
    monkeypatch.delenv(QUICK_MODE_ENV, raising=False)
    apply_quick_mode_env()
    assert quick_mode_enabled()


def test_quick_runtime_uses_in_memory_store(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    apply_quick_mode_env()
    result = build_runtime_orchestrator(config_from_db=False)
    assert isinstance(result.store, InMemoryEventStore)


def test_quick_local_workflow_profile() -> None:
    path = find_repo_root() / "configs" / "workflows" / "quick_local.yaml"
    assert path.is_file()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["slice"]["max_files"] == 1
    assert doc["universal_critique"]["implementation"]["stub"] is True
    assert doc["research"]["enabled"] is False
