"""Framework adapters for persistent dev environment processes."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from nimbusware_orchestrator.put_runtime import PutStack, detect_put_stack

AdapterFn = Callable[[Path, int], list[str]]


@dataclass(frozen=True)
class DevEnvAdapterSpec:
    name: str
    stacks: frozenset[PutStack]
    build_command: AdapterFn
    supports_reload: bool = False


def _fastapi_reload_command(workspace: Path, port: int) -> list[str]:
    host = "127.0.0.1"
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
        "--reload",
    ]


def _fastapi_plain_command(workspace: Path, port: int) -> list[str]:
    host = "127.0.0.1"
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


def _static_http_command(workspace: Path, port: int) -> list[str]:
    serve = workspace
    if (workspace / "dist" / "index.html").is_file():
        serve = workspace / "dist"
    elif (workspace / "public" / "index.html").is_file():
        serve = workspace / "public"
    return [
        sys.executable,
        "-m",
        "http.server",
        str(port),
        "--bind",
        "127.0.0.1",
        "--directory",
        str(serve),
    ]


def _npm_dev_command(workspace: Path, port: int) -> list[str]:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    env_prefix: list[str] = []
    if port:
        env_prefix = []  # caller sets PORT in env when spawning
    return env_prefix + [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)]


def _custom_yaml_command(workspace: Path, port: int) -> list[str]:
    cfg_path = workspace / ".nimbusware" / "dev_env" / "adapter.yaml"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"missing custom adapter config: {cfg_path}")
    import yaml

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("adapter.yaml must be a mapping")
    command = raw.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError("adapter.yaml command must be a non-empty list")
    rendered = [str(part).replace("{port}", str(port)) for part in command]
    return rendered


_BUILTIN: tuple[DevEnvAdapterSpec, ...] = (
    DevEnvAdapterSpec("fastapi_reload", frozenset({"fastapi"}), _fastapi_reload_command, True),
    DevEnvAdapterSpec("fastapi", frozenset({"fastapi"}), _fastapi_plain_command),
    DevEnvAdapterSpec("static", frozenset({"static", "spa", "unknown"}), _static_http_command),
    DevEnvAdapterSpec("npm_dev", frozenset({"spa"}), _npm_dev_command, True),
    DevEnvAdapterSpec("custom_yaml", frozenset({"unknown"}), _custom_yaml_command),
)

_REGISTRY: dict[str, DevEnvAdapterSpec] = {spec.name: spec for spec in _BUILTIN}


def register_dev_env_adapter(spec: DevEnvAdapterSpec) -> None:
    _REGISTRY[spec.name] = spec


def list_dev_env_adapters() -> list[str]:
    return sorted(_REGISTRY)


def resolve_adapter_name(workspace: Path, *, prefer_reload: bool = True) -> str:
    custom = workspace / ".nimbusware" / "dev_env" / "adapter.yaml"
    if custom.is_file():
        return "custom_yaml"
    stack = detect_put_stack(workspace)
    if stack == "fastapi" and prefer_reload:
        return "fastapi_reload"
    if stack == "spa" and (workspace / "package.json").is_file():
        pkg = json.loads((workspace / "package.json").read_text(encoding="utf-8"))
        scripts = pkg.get("scripts") if isinstance(pkg, dict) else None
        if isinstance(scripts, dict) and "dev" in scripts:
            return "npm_dev"
    if stack == "fastapi":
        return "fastapi"
    return "static"


def build_adapter_command(
    workspace: Path,
    port: int,
    *,
    adapter_name: str | None = None,
    prefer_reload: bool = True,
) -> tuple[str, list[str]]:
    name = adapter_name or resolve_adapter_name(workspace, prefer_reload=prefer_reload)
    spec = _REGISTRY.get(name)
    if spec is None:
        raise KeyError(f"unknown dev env adapter: {name}")
    command = spec.build_command(workspace.resolve(), port)
    return name, command


def adapter_spawn_env(port: int) -> dict[str, str]:
    env = dict(os.environ)
    env["PORT"] = str(port)
    return env
