from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from nimbusware_orchestrator.dev_env_adapters import (
    build_adapter_command,
    resolve_adapter_name,
)
from nimbusware_orchestrator.dev_env_session import (
    DevEnvironmentSession,
    load_session,
    persist_session,
)
from nimbusware_orchestrator.dev_env_supervisor import (
    dev_env_status,
    start_dev_environment,
    stop_dev_environment,
)
from nimbusware_store.memory import InMemoryEventStore


def test_resolve_adapter_fastapi_reload(tmp_path: Path) -> None:
    ws = tmp_path / "api"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]\n', encoding="utf-8")
    assert resolve_adapter_name(ws, prefer_reload=True) == "fastapi_reload"
    _, cmd = build_adapter_command(ws, 19999, prefer_reload=True)
    assert "--reload" in cmd


def test_session_persist_roundtrip(tmp_path: Path) -> None:
    session = DevEnvironmentSession.from_attach(
        run_id=str(uuid4()),
        workspace=tmp_path,
        base_url="http://127.0.0.1:8080",
        stack="fastapi",
    )
    persist_session(session)
    loaded = load_session(tmp_path)
    assert loaded is not None
    assert loaded.base_url == session.base_url


def test_start_stop_dev_environment_static(tmp_path: Path) -> None:
    ws = tmp_path / "site"
    ws.mkdir()
    (ws / "index.html").write_text("<html><body>dev env ok</body></html>", encoding="utf-8")
    store = InMemoryEventStore()
    run_id = uuid4()
    started = start_dev_environment(store, run_id, ws, port=18766)
    assert started.ok is True
    assert started.session is not None
    status = dev_env_status(ws)
    assert status.get("active") is True
    stop_dev_environment(store, run_id, ws)
    assert load_session(ws) is None
