from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.runtime_bootstrap import (
    build_runtime_orchestrator,
    resolve_role_registry,
    roles_from_db_enabled,
)
from hermes_store.memory import InMemoryEventStore


def test_roles_from_db_enabled_parses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_ROLES_FROM_DB", "true")
    assert roles_from_db_enabled() is True
    monkeypatch.setenv("NIMBUSWARE_ROLES_FROM_DB", "0")
    assert roles_from_db_enabled() is False


def test_resolve_role_registry_yaml_default(tmp_path: Path) -> None:
    roles = tmp_path / "configs" / "roles.yaml"
    roles.parent.mkdir(parents=True)
    roles.write_text(
        "version: 1\nroles:\n"
        "  - taxonomy_key: planner\n"
        '    role_id: "11111111-1111-4111-8111-111111111101"\n',
        encoding="utf-8",
    )
    reg = resolve_role_registry(tmp_path, None, None)
    assert isinstance(reg, RoleRegistry)


def test_api_and_worker_share_in_memory_store_without_db(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roles = tmp_path / "configs" / "roles.yaml"
    roles.parent.mkdir(parents=True)
    roles.write_text(
        "version: 1\nroles:\n"
        "  - taxonomy_key: planner\n"
        '    role_id: "11111111-1111-4111-8111-111111111101"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)

    with patch("hermes_orchestrator.runtime_bootstrap.RunOrchestrator") as orch_cls:
        api_rt = build_runtime_orchestrator(
            roles_from_db=False,
            use_materializer_registry=False,
        )
        worker_rt = build_runtime_orchestrator(
            roles_from_db=False,
            use_materializer_registry=True,
        )
    assert orch_cls.call_count == 2
    assert isinstance(api_rt.store, InMemoryEventStore)
    assert isinstance(worker_rt.store, InMemoryEventStore)
    assert api_rt.registry.yaml_version == worker_rt.registry.yaml_version


@patch("hermes_orchestrator.runtime_bootstrap.load_registry_from_postgres")
def test_resolve_role_registry_postgres_when_flag(
    mock_load: MagicMock,
    tmp_path: Path,
) -> None:
    mock_load.return_value = MagicMock(spec=RoleRegistry)
    mat = MagicMock()
    reg = resolve_role_registry(
        tmp_path,
        "postgres://x",
        mat,
        roles_from_db=True,
        use_materializer_registry=True,
    )
    mock_load.assert_called_once_with("postgres://x")
    assert reg is mock_load.return_value


@patch("hermes_orchestrator.runtime_bootstrap.config_from_db_enabled", return_value=True)
@patch("hermes_orchestrator.runtime_bootstrap.PostgresEventStore")
def test_worker_uses_materializer_registry_when_db_config(
    _pg: MagicMock,
    _cfg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roles = tmp_path / "configs" / "roles.yaml"
    roles.parent.mkdir(parents=True)
    roles.write_text(
        "version: 1\nroles:\n"
        "  - taxonomy_key: planner\n"
        '    role_id: "11111111-1111-4111-8111-111111111101"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgres://local/test")
    yaml_reg = RoleRegistry.from_yaml(roles)

    mat_reg = MagicMock(spec=RoleRegistry)
    with patch(
        "hermes_orchestrator.runtime_bootstrap.ConfigMaterializer",
    ) as mat_cls:
        mat_cls.return_value.get_role_registry.return_value = mat_reg
        worker_rt = build_runtime_orchestrator(
            roles_from_db=False,
            use_materializer_registry=True,
        )
    assert worker_rt.registry is mat_reg

    with patch(
        "hermes_orchestrator.runtime_bootstrap.ConfigMaterializer",
    ) as mat_cls:
        mat_cls.return_value.get_role_registry.return_value = mat_reg
        api_rt = build_runtime_orchestrator(
            roles_from_db=False,
            use_materializer_registry=False,
        )
    assert api_rt.registry.yaml_version == yaml_reg.yaml_version
    assert api_rt.registry is not mat_reg
