from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from orchestrator._pipeline.base import RunOrchestratorBase
from orchestrator.registry import RoleRegistry
from store.memory import InMemoryEventStore


def test_base_cfg_prefers_materializer_when_db(tmp_path: Path) -> None:
    base_path = tmp_path / "configs" / "model-routing.yaml"
    base_path.parent.mkdir(parents=True)
    base_path.write_text("finding_fix_strictness: {}\n", encoding="utf-8")
    mat = MagicMock()
    mat.use_db = True
    mat.get_model_routing_base.return_value = {"from": "db"}
    orch = RunOrchestratorBase(
        InMemoryEventStore(),
        RoleRegistry([]),
        repo_root=tmp_path,
        base_config_path=base_path,
        config_materializer=mat,
    )
    assert orch._base_cfg() == {"from": "db"}
    mat.get_model_routing_base.assert_called_once()
