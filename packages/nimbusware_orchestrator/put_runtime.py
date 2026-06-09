"""Local PUT preview subprocess and stack detection."""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

PutStack = Literal["fastapi", "static", "spa", "fullstack", "unknown"]

_SPA_MARKERS = frozenset({"vite", "react", "vue", "angular", "svelte"})
_FASTAPI_MARKERS = frozenset({"fastapi", "from fastapi import"})


@dataclass
class PutPreviewHandle:
    process: subprocess.Popen[str]
    workspace: Path
    port: int
    stack: PutStack
    base_url: str
    command: tuple[str, ...]
    artifacts_dir: Path | None = None


@dataclass(frozen=True)
class PutPreviewStartResult:
    ok: bool
    handle: PutPreviewHandle | None = None
    error: str | None = None
    probe: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)


def _has_spa_marker(ws: Path) -> bool:
    pkg = ws / "package.json"
    if pkg.is_file():
        text = pkg.read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in text for marker in _SPA_MARKERS):
            return True
    frontend = ws / "frontend"
    if frontend.is_dir() and (frontend / "package.json").is_file():
        text = (frontend / "package.json").read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in text for marker in _SPA_MARKERS):
            return True
    for html_path in (
        ws / "index.html",
        ws / "dist" / "index.html",
        ws / "public" / "index.html",
        ws / "frontend" / "index.html",
        ws / "frontend" / "dist" / "index.html",
    ):
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in html for marker in _SPA_MARKERS):
            return True
        if 'id="root"' in html or 'id="app"' in html:
            return True
    return False


def detect_put_stack(workspace: Path) -> PutStack:
    ws = workspace.resolve()
    if not ws.is_dir():
        return "unknown"

    has_api = _has_fastapi_marker(ws)
    has_spa = _has_spa_marker(ws)
    if has_api and has_spa:
        return "fullstack"

    if has_api:
        return "fastapi"

    pkg = ws / "package.json"
    if pkg.is_file():
        text = pkg.read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in text for marker in _SPA_MARKERS):
            return "spa"

    for html_path in (
        ws / "index.html",
        ws / "dist" / "index.html",
        ws / "public" / "index.html",
    ):
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in html for marker in _SPA_MARKERS):
            return "spa"
        if 'id="root"' in html or 'id="app"' in html:
            return "spa"
        return "static"

    return "unknown"


def _has_fastapi_marker(ws: Path) -> bool:
    for path in (ws / "pyproject.toml", ws / "requirements.txt"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "fastapi" in text:
                return True
    for py_path in sorted(ws.glob("*.py"))[:30]:
        text = py_path.read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in text for marker in _FASTAPI_MARKERS):
            return True
    for py_path in sorted(ws.glob("**/main.py"))[:10]:
        if py_path.is_relative_to(ws / ".venv"):
            continue
        text = py_path.read_text(encoding="utf-8", errors="replace").lower()
        if any(marker in text for marker in _FASTAPI_MARKERS):
            return True
    return False


def _serve_directory(workspace: Path, stack: PutStack) -> Path:
    if stack == "spa" and (workspace / "dist" / "index.html").is_file():
        return workspace / "dist"
    if (workspace / "public" / "index.html").is_file():
        return workspace / "public"
    return workspace


def _preview_command(workspace: Path, stack: PutStack, port: int) -> list[str]:
    host = "127.0.0.1"
    if stack == "fastapi":
        if (workspace / "app" / "main.py").is_file():
            module = "app.main:app"
        else:
            module = "main:app"
        return [
            sys.executable,
            "-m",
            "uvicorn",
            module,
            "--host",
            host,
            "--port",
            str(port),
        ]

    serve_dir = _serve_directory(workspace, stack)
    return [
        sys.executable,
        "-m",
        "http.server",
        str(port),
        "--bind",
        host,
        "--directory",
        str(serve_dir),
    ]


def _health_paths_for_stack(stack: PutStack) -> tuple[str, ...]:
    if stack in {"fastapi", "fullstack"}:
        return ("/docs", "/openapi.json", "/health", "/")
    return ("/", "/index.html")


def _probe_preview_health(base_url: str, stack: PutStack) -> dict[str, Any]:
    from nimbusware_orchestrator.integration_adapter_scaffold import probe_http_endpoint

    last: dict[str, Any] = {"reachable": False, "error": "no_probe"}
    for path in _health_paths_for_stack(stack):
        probe = probe_http_endpoint(f"{base_url.rstrip('/')}{path}", timeout=1.5, max_attempts=5)
        last = {**probe, "path": path}
        if probe.get("reachable") and probe.get("ok"):
            return last
    return last


def start_put_preview(
    workspace: Path,
    port: int,
    *,
    startup_timeout_seconds: float = 15.0,
) -> PutPreviewStartResult:
    ws = workspace.resolve()
    stack = detect_put_stack(ws)
    command = _preview_command(ws, stack, port)
    from nimbusware_orchestrator.put_sandbox import wrap_put_preview_command

    command = wrap_put_preview_command(command, port=port, workspace=str(ws))
    base_url = f"http://127.0.0.1:{port}"

    try:
        proc = subprocess.Popen(
            command,
            cwd=ws,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        artifacts = collect_put_artifacts(ws, None, reason=str(exc), stack=stack, command=command)
        return PutPreviewStartResult(
            ok=False,
            error=str(exc),
            artifacts=artifacts,
        )

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
            return PutPreviewStartResult(ok=True, handle=handle, probe=probe)
        time.sleep(0.25)

    if proc.poll() is None:
        probe = _probe_preview_health(base_url, stack)
        if probe.get("reachable") and probe.get("ok"):
            return PutPreviewStartResult(ok=True, handle=handle, probe=probe)

    error = probe.get("error") or f"preview exited with code {proc.poll()}"
    artifacts = collect_put_artifacts(ws, handle, reason=error, stack=stack, command=command)
    stop_put_preview(handle)
    return PutPreviewStartResult(ok=False, error=str(error), probe=probe, artifacts=artifacts)


def stop_put_preview(handle: PutPreviewHandle | None) -> None:
    if handle is None:
        return
    proc = handle.process
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5.0)
    except (OSError, subprocess.TimeoutExpired):
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=2.0)
        except (OSError, subprocess.TimeoutExpired):
            pass


def collect_put_artifacts(
    workspace: Path,
    handle: PutPreviewHandle | None,
    *,
    reason: str,
    stack: PutStack | None = None,
    command: list[str] | None = None,
) -> dict[str, Any]:
    ws = workspace.resolve()
    artifacts_dir = ws / ".nimbusware" / "put_artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    stdout_tail = ""
    stderr_tail = ""
    exit_code: int | None = None
    if handle is not None:
        proc = handle.process
        exit_code = proc.poll()
        if exit_code is None:
            stop_put_preview(handle)
            exit_code = proc.poll()
        try:
            if proc.stdout is not None:
                stdout_tail = proc.stdout.read()[-4000:]
            if proc.stderr is not None:
                stderr_tail = proc.stderr.read()[-4000:]
        except OSError:
            pass
        stack = stack or handle.stack
        command = command or list(handle.command)

    manifest = {
        "reason": reason[:500],
        "stack": stack or detect_put_stack(ws),
        "command": command or [],
        "exit_code": exit_code,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }
    manifest_path = artifacts_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    for name, content in (("stdout.log", stdout_tail), ("stderr.log", stderr_tail)):
        if content:
            (artifacts_dir / name).write_text(content, encoding="utf-8")

    return {
        "artifacts_dir": str(artifacts_dir),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
    }


def emit_put_preview_started(store: Any, run_id: Any, handle: PutPreviewHandle) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "put": {
                    "base_url": handle.base_url,
                    "stack": handle.stack,
                    "port": handle.port,
                },
            },
            payload=StageStartedPayload(stage_name="put.preview.started", attempt=1),
        ),
    )


def emit_put_preview_stopped(store: Any, run_id: Any, handle: PutPreviewHandle) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "put": {
                    "base_url": handle.base_url,
                    "stack": handle.stack,
                    "port": handle.port,
                },
            },
            payload=StageStartedPayload(stage_name="put.preview.stopped", attempt=1),
        ),
    )


def put_stack_note(workspace: Path | None) -> str:
    if workspace is None or not workspace.is_dir():
        return ""
    return f" put_stack={detect_put_stack(workspace.resolve())}"


def put_runtime_summary(workspace: Path) -> dict[str, Any]:
    ws = workspace.resolve()
    stack = detect_put_stack(ws)
    return {
        "stack": stack,
        "serve_directory": str(_serve_directory(ws, stack)),
        "preview_command": _preview_command(ws, stack, 0),
    }
