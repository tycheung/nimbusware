from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from env.launcher_fetch import (
    INSTALL_PROFILE_BAREBONES,
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
    install_script_args,
    resolve_bootstrap_python,
    resolve_install_script,
)

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


@dataclass(frozen=True)
class InstallState:
    install_profile: str
    setup_bundle: str
    edition: str
    database_url: str | None


def _strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def read_env_file(repo: Path) -> dict[str, str]:
    env_path = repo / ".env"
    if not env_path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        values[match.group(1)] = _strip_env_value(match.group(2))
    return values


def read_install_state(repo: Path) -> InstallState:
    env = read_env_file(repo)
    return InstallState(
        install_profile=env.get("NIMBUSWARE_INSTALL_PROFILE", INSTALL_PROFILE_BAREBONES),
        setup_bundle=env.get("NIMBUSWARE_SETUP_BUNDLE", SETUP_BUNDLE_DEFAULT),
        edition=env.get("NIMBUSWARE_EDITION", "individual"),
        database_url=env.get("NIMBUSWARE_DATABASE_URL"),
    )


def postgres_extra_args(
    repo: Path,
    *,
    database_url: str | None = None,
    admin_url: str | None = None,
) -> list[str]:
    env = read_env_file(repo)
    extras: list[str] = []
    db_url = (database_url or env.get("NIMBUSWARE_DATABASE_URL") or "").strip()
    admin = (admin_url or env.get("NIMBUSWARE_POSTGRES_ADMIN_URL") or "").strip()
    if db_url:
        extras.extend(["--database-url", db_url])
    if admin:
        extras.extend(["--postgres-admin-url", admin])
    return extras


def run_convert_install(
    repo: Path,
    *,
    profile: str,
    setup_bundle: str,
    extra_args: list[str] | None = None,
    log: Callable[[str], None] | None = None,
) -> int:
    import os

    script = resolve_install_script(repo)
    cmd = [
        *resolve_bootstrap_python(repo),
        str(script),
        *install_script_args(profile, setup_bundle=setup_bundle),
        *(extra_args or []),
    ]
    if log:
        log(f"$ {' '.join(cmd)}")
    env = os.environ.copy()
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(repo))
    return subprocess.run(cmd, cwd=str(repo), env=env, text=True).returncode


def uninstall_nimbusware(repo: Path, *, log: Callable[[str], None] | None = None) -> None:
    """Remove the Poetry virtualenv only; preserve .env, Postgres data, and Ollama models."""
    venv = repo / ".venv"
    if venv.is_dir():
        if log:
            log(f"Removing virtualenv: {venv}")
        shutil.rmtree(venv, ignore_errors=True)
    poetry = shutil.which("poetry")
    if poetry and (repo / "pyproject.toml").is_file():
        if log:
            log("Removing Poetry-managed environment (if any)...")
        subprocess.run(
            [poetry, "env", "remove", "--all"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
    if log:
        log("Uninstall complete. User data preserved (.env, database, models).")


def convert_label(state: InstallState) -> str:
    profile = "Quick" if state.install_profile == INSTALL_PROFILE_BAREBONES else "Full"
    bundle = "Enterprise" if state.setup_bundle == SETUP_BUNDLE_ENTERPRISE else "Individual"
    return f"{profile} / {bundle}"
