from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nimbusware_config import ConfigMaterializer, config_from_db_enabled
from nimbusware_env.env_flags import nimbusware_database_url, nimbusware_repo_root_path
from nimbusware_extensions.bundle_memory_factory import build_bundle_outcome_store
from nimbusware_memory.factory import build_memory_chunk_store
from nimbusware_orchestrator.pipeline import RunOrchestrator, default_paths
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.registry_db import load_registry_from_postgres
from nimbusware_store.memory import InMemoryEventStore
from nimbusware_store.postgres import PostgresEventStore
from nimbusware_store.protocol import EventStore

if TYPE_CHECKING:
    from nimbusware_config.notify import ConfigNotifyHub


@dataclass(frozen=True)
class RuntimeBootstrapResult:
    orchestrator: RunOrchestrator
    store: EventStore
    registry: RoleRegistry
    materializer: ConfigMaterializer | None
    notify_stop: threading.Event | None
    notify_thread: threading.Thread | None
    config_notify_hub: ConfigNotifyHub | None


def resolve_repo_root(repo_root: Path | None = None) -> Path:
    if repo_root is not None:
        return repo_root.resolve()
    return nimbusware_repo_root_path()


def resolve_database_url() -> str | None:
    return nimbusware_database_url()


def roles_from_db_enabled() -> bool:
    from nimbusware_env.env_flags import nimbusware_roles_from_db_enabled

    return nimbusware_roles_from_db_enabled()


def api_config_from_db_enabled() -> bool:
    """API lifespan: materializer only when ``NIMBUSWARE_CONFIG_FROM_DB`` is explicitly on."""
    from nimbusware_env.env_flags import env_truthy, nimbusware_config_from_files_enabled

    if nimbusware_config_from_files_enabled():
        return False
    return env_truthy("NIMBUSWARE_CONFIG_FROM_DB")


def _config_from_db_active(config_from_db: bool | None) -> bool:
    if config_from_db is not None:
        return config_from_db
    return config_from_db_enabled()


def resolve_role_registry(
    repo: Path,
    url: str | None,
    materializer: ConfigMaterializer | None,
    *,
    roles_from_db: bool = False,
    use_materializer_registry: bool = False,
) -> RoleRegistry:
    if url and roles_from_db:
        return load_registry_from_postgres(url)
    if materializer is not None and use_materializer_registry:
        return materializer.get_role_registry()
    return RoleRegistry.from_yaml(repo / "configs" / "roles.yaml")


def _load_operator_settings_from_db(url: str | None) -> None:
    if not url:
        return
    try:
        from nimbusware_env.settings_resolve import refresh_scope_caches
        from nimbusware_env.settings_store import apply_all_managed_to_environ

        apply_all_managed_to_environ()
        refresh_scope_caches()
    except Exception:
        return


def build_event_store(url: str | None) -> EventStore:
    if url:
        return PostgresEventStore(url)
    return InMemoryEventStore()


def start_config_notify(
    url: str,
    materializer: ConfigMaterializer,
) -> tuple[threading.Event, threading.Thread, ConfigNotifyHub]:
    from nimbusware_config import get_config_notify_hub, start_config_notify_listener

    hub = get_config_notify_hub()
    hub.register(materializer)
    notify_stop = threading.Event()
    notify_thread = start_config_notify_listener(url, hub, notify_stop)
    return notify_stop, notify_thread, hub


def build_runtime_orchestrator(
    *,
    repo_root: Path | None = None,
    roles_from_db: bool | None = None,
    use_materializer_registry: bool = False,
    config_from_db: bool | None = None,
) -> RuntimeBootstrapResult:
    repo = resolve_repo_root(repo_root)
    base, _ = default_paths(repo)
    url = resolve_database_url()
    _load_operator_settings_from_db(url)
    roles_db = roles_from_db_enabled() if roles_from_db is None else roles_from_db

    materializer: ConfigMaterializer | None = None
    if _config_from_db_active(config_from_db) and url:
        materializer = ConfigMaterializer(repo, use_db=True)

    registry = resolve_role_registry(
        repo,
        url,
        materializer,
        roles_from_db=roles_db,
        use_materializer_registry=use_materializer_registry,
    )
    store = build_event_store(url)

    notify_stop: threading.Event | None = None
    notify_thread: threading.Thread | None = None
    hub: ConfigNotifyHub | None = None
    if materializer is not None and url:
        from nimbusware_config import config_notify_listener_enabled

        if config_notify_listener_enabled():
            notify_stop, notify_thread, hub = start_config_notify(url, materializer)

    orchestrator = RunOrchestrator(
        store,
        registry,
        repo_root=repo,
        base_config_path=base,
        config_materializer=materializer,
        memory_chunk_store=build_memory_chunk_store(url),
        bundle_outcome_store=build_bundle_outcome_store(url),
    )
    return RuntimeBootstrapResult(
        orchestrator=orchestrator,
        store=store,
        registry=registry,
        materializer=materializer,
        notify_stop=notify_stop,
        notify_thread=notify_thread,
        config_notify_hub=hub,
    )
