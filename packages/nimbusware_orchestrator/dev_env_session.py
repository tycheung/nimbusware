from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from nimbusware_orchestrator.put_runtime import PutPreviewHandle, PutStack

_PUT_STACKS = frozenset({"fastapi", "static", "spa", "fullstack", "unknown"})


def _coerce_put_stack(value: object) -> PutStack:
    stack = str(value or "unknown")
    if stack in _PUT_STACKS:
        return cast(PutStack, stack)
    return "unknown"


@dataclass
class DevEnvironmentSession:
    session_id: str
    run_id: str
    workspace: Path
    base_url: str
    stack: PutStack
    port: int
    attach_mode: bool = False
    health: str = "starting"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_probe_at: str | None = None
    probe: dict[str, Any] = field(default_factory=dict)
    adapter: str = "default"
    command: tuple[str, ...] = ()
    api_base_url: str | None = None
    frontend_base_url: str | None = None
    frontend_port: int = 0

    @classmethod
    def from_handle(
        cls,
        *,
        run_id: str,
        handle: PutPreviewHandle,
        attach_mode: bool = False,
        adapter: str = "default",
    ) -> DevEnvironmentSession:
        return cls(
            session_id=str(uuid4()),
            run_id=str(run_id),
            workspace=handle.workspace,
            base_url=handle.base_url,
            stack=handle.stack,
            port=handle.port,
            attach_mode=attach_mode,
            health="healthy",
            command=handle.command,
            adapter=adapter,
        )

    @classmethod
    def from_attach(
        cls,
        *,
        run_id: str,
        workspace: Path,
        base_url: str,
        stack: PutStack = "unknown",
    ) -> DevEnvironmentSession:
        return cls(
            session_id=str(uuid4()),
            run_id=str(run_id),
            workspace=workspace.resolve(),
            base_url=base_url.rstrip("/"),
            stack=stack,
            port=0,
            attach_mode=True,
            health="healthy",
            adapter="attach",
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["workspace"] = str(self.workspace)
        data["command"] = list(self.command)
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DevEnvironmentSession:
        api_url = raw.get("api_base_url")
        fe_url = raw.get("frontend_base_url")
        base = str(raw.get("base_url") or "")
        return cls(
            session_id=str(raw.get("session_id") or uuid4()),
            run_id=str(raw.get("run_id") or ""),
            workspace=Path(str(raw.get("workspace") or ".")),
            base_url=base,
            stack=_coerce_put_stack(raw.get("stack")),
            port=int(raw.get("port") or 0),
            attach_mode=bool(raw.get("attach_mode")),
            health=str(raw.get("health") or "unknown"),
            started_at=str(raw.get("started_at") or datetime.now(timezone.utc).isoformat()),
            last_probe_at=raw.get("last_probe_at"),
            probe=dict(raw.get("probe") or {}),
            adapter=str(raw.get("adapter") or "default"),
            command=tuple(str(x) for x in (raw.get("command") or [])),
            api_base_url=str(api_url) if api_url else None,
            frontend_base_url=str(fe_url) if fe_url else None,
            frontend_port=int(raw.get("frontend_port") or 0),
        )


def session_dir(workspace: Path) -> Path:
    path = workspace.resolve() / ".nimbusware" / "dev_env"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_file_path(workspace: Path) -> Path:
    return session_dir(workspace) / "session.json"


def persist_session(session: DevEnvironmentSession) -> Path:
    path = session_file_path(session.workspace)
    path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
    return path


def load_session(workspace: Path) -> DevEnvironmentSession | None:
    path = session_file_path(workspace)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return DevEnvironmentSession.from_dict(raw)


def clear_session(workspace: Path) -> None:
    path = session_file_path(workspace)
    if path.is_file():
        path.unlink()
