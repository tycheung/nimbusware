from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.dev_env_adapters import (
    adapter_spawn_env,
    build_adapter_command,
    resolve_adapter_name,
)
from nimbusware_orchestrator.dev_env_events import (
    emit_dev_env_health,
    emit_dev_env_started,
    emit_dev_env_stopped,
)
from nimbusware_orchestrator.dev_env_session import (
    DevEnvironmentSession,
    clear_session,
    load_session,
    persist_session,
)
from nimbusware_orchestrator.put_runtime import (
    PutPreviewHandle,
    PutPreviewStartResult,
    _probe_preview_health,
    detect_put_stack,
    stop_put_preview,
)
from nimbusware_orchestrator.put_sandbox import wrap_put_preview_command

_ACTIVE: dict[str, PutPreviewHandle] = {}


@dataclass(frozen=True)
class DevEnvStartResult:
    ok: bool
    session: DevEnvironmentSession | None = None
    error: str | None = None
    probe: dict[str, Any] = field(default_factory=dict)
    reused: bool = False


def _attach_base_url() -> str | None:
    for key in ("NIMBUSWARE_DEV_ENV_BASE_URL", "NIMBUSWARE_PUT_BASE_URL"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return raw.rstrip("/")
    return None


def _default_port(workspace: Path) -> int:
    base = int(os.environ.get("NIMBUSWARE_DEV_ENV_PORT_BASE", "19800") or 19800)
    return base + (hash(str(workspace.resolve())) % 500)


def _spawn_preview(
    workspace: Path,
    port: int,
    *,
    adapter_name: str | None = None,
    prefer_reload: bool = True,
    startup_timeout_seconds: float = 20.0,
) -> PutPreviewStartResult:
    ws = workspace.resolve()
    stack = detect_put_stack(ws)
    name, command = build_adapter_command(
        ws,
        port,
        adapter_name=adapter_name,
        prefer_reload=prefer_reload,
    )
    command = wrap_put_preview_command(command, port=port, workspace=str(ws))
    base_url = f"http://127.0.0.1:{port}"
    try:
        proc = subprocess.Popen(
            command,
            cwd=ws,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=adapter_spawn_env(port),
        )
    except OSError as exc:
        return PutPreviewStartResult(ok=False, error=str(exc))

    handle = PutPreviewHandle(
        process=proc,
        workspace=ws,
        port=port,
        stack=stack,
        base_url=base_url,
        command=tuple(command),
    )
    deadline = time.monotonic() + startup_timeout_seconds
    probe: dict[str, Any] = {"reachable": False, "error": "startup_timeout"}
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        probe = _probe_preview_health(base_url, stack)
        if probe.get("reachable") and probe.get("ok"):
            _ACTIVE[str(ws)] = handle
            return PutPreviewStartResult(ok=True, handle=handle, probe=probe)
        time.sleep(0.25)

    if proc.poll() is None:
        probe = _probe_preview_health(base_url, stack)
        if probe.get("reachable") and probe.get("ok"):
            _ACTIVE[str(ws)] = handle
            return PutPreviewStartResult(ok=True, handle=handle, probe=probe)

    error = probe.get("error") or f"preview exited with code {proc.poll()}"
    stop_put_preview(handle)
    return PutPreviewStartResult(ok=False, error=str(error), probe=probe)


def start_dev_environment(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    port: int | None = None,
    adapter_name: str | None = None,
    prefer_reload: bool = True,
    emit_events: bool = True,
) -> DevEnvStartResult:
    ws = workspace.resolve()
    existing = load_session(ws)
    if existing is not None and existing.health in {"healthy", "starting"}:
        probe = _probe_preview_health(existing.base_url, existing.stack)
        if probe.get("reachable") and probe.get("ok"):
            return DevEnvStartResult(ok=True, session=existing, probe=probe, reused=True)

    attach = _attach_base_url()
    if attach:
        session = DevEnvironmentSession.from_attach(
            run_id=str(run_id),
            workspace=ws,
            base_url=attach,
            stack=detect_put_stack(ws),
        )
        persist_session(session)
        if emit_events:
            emit_dev_env_started(store, run_id, session)
        return DevEnvStartResult(ok=True, session=session, probe={"reachable": True, "ok": True})

    chosen_port = port if port is not None else _default_port(ws)
    preview = _spawn_preview(
        ws,
        chosen_port,
        adapter_name=adapter_name,
        prefer_reload=prefer_reload,
    )
    if not preview.ok or preview.handle is None:
        return DevEnvStartResult(ok=False, error=preview.error, probe=preview.probe)

    adapter = adapter_name or resolve_adapter_name(ws, prefer_reload=prefer_reload)
    session = DevEnvironmentSession.from_handle(
        run_id=str(run_id),
        handle=preview.handle,
        adapter=adapter,
    )
    session.probe = dict(preview.probe)
    session.last_probe_at = datetime.now(timezone.utc).isoformat()
    persist_session(session)
    if emit_events:
        emit_dev_env_started(store, run_id, session)
    return DevEnvStartResult(ok=True, session=session, probe=preview.probe)


def stop_dev_environment(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    emit_events: bool = True,
) -> bool:
    ws = workspace.resolve()
    session = load_session(ws)
    handle = _ACTIVE.pop(str(ws), None)
    if handle is not None:
        stop_put_preview(handle)
    elif session is not None and not session.attach_mode:
        pass
    if session is not None:
        session.health = "stopped"
        if emit_events:
            emit_dev_env_stopped(store, run_id, session)
    clear_session(ws)
    return True


def probe_dev_environment_health(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    emit_events: bool = False,
) -> dict[str, Any]:
    ws = workspace.resolve()
    session = load_session(ws)
    if session is None:
        return {"healthy": False, "error": "no_session"}
    probe = _probe_preview_health(session.base_url, session.stack)
    healthy = bool(probe.get("reachable") and probe.get("ok"))
    session.health = "healthy" if healthy else "degraded"
    session.probe = dict(probe)
    session.last_probe_at = datetime.now(timezone.utc).isoformat()
    persist_session(session)
    if emit_events:
        emit_dev_env_health(store, run_id, session, degraded=not healthy)
    return {"healthy": healthy, "session": session.to_dict(), "probe": probe}


def dev_env_status(workspace: Path) -> dict[str, Any]:
    session = load_session(workspace.resolve())
    if session is None:
        return {"active": False}
    probe = _probe_preview_health(session.base_url, session.stack)
    return {
        "active": bool(probe.get("reachable") and probe.get("ok")),
        "session": session.to_dict(),
        "probe": probe,
    }


def active_base_url(workspace: Path) -> str | None:
    session = load_session(workspace.resolve())
    if session is None:
        return None
    probe = _probe_preview_health(session.base_url, session.stack)
    if probe.get("reachable") and probe.get("ok"):
        return session.base_url
    return None
