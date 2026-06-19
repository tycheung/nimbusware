from __future__ import annotations

import os
import re
from pathlib import Path

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def find_repo_root(*, start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return cur


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def load_dotenv(
    path: Path | None = None,
    *,
    repo_root: Path | None = None,
    override: bool = False,
) -> Path | None:
    """Load ``KEY=VALUE`` pairs from ``.env`` at repo root into ``os.environ``.

    Existing environment variables are kept unless ``override=True``.
    Returns the path loaded, or ``None`` if no file exists.
    """
    root = repo_root or find_repo_root()
    env_path = path or (root / ".env")
    if env_path.is_file():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = _LINE.match(line)
            if not match:
                continue
            key, value = match.group(1), _strip_quotes(match.group(2))
            if not override and key in os.environ:
                continue
            os.environ[key] = value
    from nimbusware_env.admin_token import apply_default_admin_token_env

    apply_default_admin_token_env()
    return env_path.resolve() if env_path.is_file() else None


def _format_env_value(value: str) -> str:
    if re.search(r'[#\s="\']', value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def set_env_var(
    key: str,
    value: str,
    *,
    repo_root: Path | None = None,
    env_path: Path | None = None,
) -> Path:
    root = repo_root or find_repo_root()
    path = env_path or (root / ".env")
    formatted = f"{key}={_format_env_value(value)}"
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    replaced = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            out.append(line)
            continue
        match = _LINE.match(line)
        if match and match.group(1) == key:
            out.append(formatted)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append(formatted)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    os.environ[key] = value
    return path.resolve()
