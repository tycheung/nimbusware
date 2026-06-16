from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class OllamaManageError(RuntimeError):
    pass


@dataclass(frozen=True)
class OllamaModelRow:
    name: str
    size_bytes: int | None = None
    modified_at: str | None = None
    digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name}
        if self.size_bytes is not None:
            out["size_bytes"] = self.size_bytes
        if self.modified_at is not None:
            out["modified_at"] = self.modified_at
        if self.digest is not None:
            out["digest"] = self.digest
        return out


def ollama_base_url(host: str | None = None) -> str:
    from nimbusware_env.env_flags import nimbusware_ollama_base_url

    return nimbusware_ollama_base_url(host)


def ollama_reachable(host: str | None = None, *, timeout_s: float = 2.0) -> bool:
    base = ollama_base_url(host)
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(resp.status)
            return 200 <= status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def list_installed_models(host: str | None = None) -> list[OllamaModelRow]:
    base = ollama_base_url(host)
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    rows: list[OllamaModelRow] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        size_raw = item.get("size")
        size = int(size_raw) if isinstance(size_raw, int) else None
        modified = item.get("modified_at")
        modified_at = str(modified) if modified is not None else None
        digest_raw = item.get("digest")
        digest = str(digest_raw) if isinstance(digest_raw, str) and digest_raw else None
        rows.append(
            OllamaModelRow(
                name=name.strip(),
                size_bytes=size,
                modified_at=modified_at,
                digest=digest,
            ),
        )
    rows.sort(key=lambda r: r.name.lower())
    return rows


def filter_models(models: list[OllamaModelRow], query: str) -> list[OllamaModelRow]:
    q = query.strip().lower()
    if not q:
        return list(models)
    return [m for m in models if q in m.name.lower()]


def pull_model(model: str, *, host: str | None = None) -> None:
    name = model.strip()
    if not name:
        raise OllamaManageError("model name is required")
    if not ollama_reachable(host):
        raise OllamaManageError(f"Ollama API is not reachable at {ollama_base_url(host)}")
    binary = _find_ollama_binary()
    if binary is None:
        raise OllamaManageError("ollama CLI not found on PATH")
    subprocess.run([binary, "pull", name], check=True)


def delete_model(model: str, *, host: str | None = None) -> None:
    name = model.strip()
    if not name:
        raise OllamaManageError("model name is required")
    base = ollama_base_url(host)
    body = json.dumps({"name": name}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/delete",
        data=body,
        method="DELETE",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            if resp.status >= 400:
                raise OllamaManageError(f"Ollama delete failed with status {resp.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OllamaManageError(f"Ollama delete failed: {detail or exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OllamaManageError(f"Ollama delete failed: {exc}") from exc


def _find_ollama_binary() -> str | None:
    import shutil
    import sys
    from pathlib import Path

    on_path = shutil.which("ollama")
    if on_path:
        return on_path
    if sys.platform == "win32":
        from nimbusware_env.env_flags import env_str

        local = Path(env_str("LOCALAPPDATA")) / "Programs" / "Ollama" / "ollama.exe"
        if local.is_file():
            return str(local)
    return None


def runtime_base_url_from_routing(routing: dict[str, Any]) -> str:
    runtime = routing.get("runtime")
    if isinstance(runtime, dict):
        raw = runtime.get("base_url")
        if isinstance(raw, str) and raw.strip():
            return raw.strip().rstrip("/")
    return ollama_base_url(None)
