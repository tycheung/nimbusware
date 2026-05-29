#!/usr/bin/env python3
"""Bootstrap a Hermes developer environment (Poetry, Postgres, schema, optional seed).

Run from an existing clone::

    python scripts/install_hermes.py

Or clone first (requires git)::

    python scripts/install_hermes.py --clone <repo-url> --target-dir D:\\Hermes

If PostgreSQL is not running, the script shows an interactive menu (Docker,
Windows ``.exe``, winget, manual, custom URL, or skip). Ollama can be installed
via winget/brew/curl (see ``--ollama-choice``). Use ``--non-interactive`` for CI.
Use ``--install-postgres-native`` or ``--postgres-choice native`` to skip the Postgres menu.

Windows wrapper: ``.\\scripts\\install-hermes.ps1``
Unix wrapper: ``bash scripts/install-hermes.sh``
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql://hermes:hermes@127.0.0.1:5432/hermes"
MIN_PYTHON = (3, 10)
REC_PYTHON = (3, 11)
SCHEMA_REL = Path("packages/hermes_store/schema/postgres.sql")
COMPOSE_FILE = "docker-compose.yml"


class SetupError(RuntimeError):
    pass


def _log(msg: str) -> None:
    print(msg, flush=True)


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", flush=True)


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    _log(f"  $ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        text=True,
        capture_output=False,
    )


def _which(name: str) -> str | None:
    return shutil.which(name)


def _python_version() -> tuple[int, int, int]:
    return sys.version_info[:3]


def _version_at_least(ver: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    return ver >= minimum


def _find_poetry() -> str | None:
    for candidate in ("poetry", "poetry.exe"):
        path = _which(candidate)
        if path:
            return path
    return None


def _ensure_poetry(*, install: bool) -> str:
    existing = _find_poetry()
    if existing:
        return existing
    if not install:
        raise SetupError(
            "Poetry is not on PATH. Install from https://python-poetry.org/docs/#installation "
            "or re-run with default options to install via pip.",
        )
    _log("Installing Poetry via pip...")
    _run([sys.executable, "-m", "pip", "install", "--upgrade", "poetry"])
    path = _find_poetry()
    if not path:
        raise SetupError("Poetry install finished but `poetry` is still not on PATH.")
    return path


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def _is_hermes_repo(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / SCHEMA_REL).is_file()


def _clone_repo(url: str, target: Path) -> Path:
    if target.exists() and any(target.iterdir()):
        if not _is_hermes_repo(target):
            raise SetupError(f"Target exists but is not a Hermes repo: {target}")
        _log(f"Using existing clone at {target}")
        return target.resolve()
    git = _which("git")
    if not git:
        raise SetupError("git is required for --clone but was not found on PATH.")
    target.parent.mkdir(parents=True, exist_ok=True)
    _run([git, "clone", url, str(target)])
    if not _is_hermes_repo(target):
        raise SetupError(f"Cloned repo does not look like Hermes: {target}")
    return target.resolve()


def _ensure_poetry_lock(poetry: str, repo: Path) -> None:
    pyproject = repo / "pyproject.toml"
    lock = repo / "poetry.lock"
    if lock.is_file() and pyproject.stat().st_mtime <= lock.stat().st_mtime:
        return
    _log("poetry.lock is missing or older than pyproject.toml; running poetry lock...")
    _run([poetry, "lock", "--no-interaction"], cwd=repo)


def _poetry_install(
    poetry: str,
    repo: Path,
    *,
    with_faiss: bool,
    with_redis: bool,
) -> None:
    _ensure_poetry_lock(poetry, repo)
    cmd = [poetry, "install", "--no-interaction"]
    if with_faiss:
        cmd.extend(["--with", "faiss"])
    if with_redis:
        cmd.extend(["--with", "redis"])
    try:
        _run(cmd, cwd=repo)
    except subprocess.CalledProcessError as exc:
        if exc.returncode != 1:
            raise
        lock_file = repo / "poetry.lock"
        if not lock_file.is_file():
            raise
        _log("Poetry install failed; refreshing poetry.lock and retrying...")
        _run([poetry, "lock", "--no-interaction"], cwd=repo)
        _run(cmd, cwd=repo)


def _postgres_reachable(
    url: str,
    *,
    timeout_s: float = 2.0,
    postgres_major: int | None = None,
) -> bool:
    if sys.platform == "win32":
        scripts_dir = _scripts_dir()
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from postgres_windows import postgres_reachable  # noqa: PLC0415

        return postgres_reachable(url, timeout_s=timeout_s, major=postgres_major)
    try:
        import psycopg  # noqa: PLC0415

        with psycopg.connect(url, connect_timeout=int(timeout_s)):
            return True
    except Exception:
        return False


def _wait_for_postgres(url: str, *, attempts: int = 60, sleep_s: float = 2.0) -> None:
    _log(f"Waiting for PostgreSQL at {url} ...")
    for i in range(attempts):
        if _postgres_reachable(url):
            _log("PostgreSQL is accepting connections.")
            return
        if i < attempts - 1:
            time.sleep(sleep_s)
    raise SetupError(
        f"PostgreSQL did not become reachable within {attempts * sleep_s:.0f}s. "
        "Start Postgres manually or use Docker (see --help).",
    )


def _docker_compose_cmd() -> list[str] | None:
    if _which("docker"):
        try:
            _run(["docker", "compose", "version"], check=True)
            return ["docker", "compose"]
        except subprocess.CalledProcessError:
            pass
        if _which("docker-compose"):
            return ["docker-compose"]
    return None


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def _import_postgres_windows():
    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from postgres_windows import (  # noqa: PLC0415
        PostgresWindowsError,
        install_postgresql_windows,
    )

    return PostgresWindowsError, install_postgresql_windows


def _import_postgres_menu():
    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from postgres_setup_menu import (  # noqa: PLC0415
        build_postgres_setup_options,
        print_os_package_hints,
        prompt_database_url,
        prompt_postgres_setup_choice,
        prompt_press_enter_when_ready,
        run_winget_postgresql_install,
    )

    return (
        build_postgres_setup_options,
        print_os_package_hints,
        prompt_database_url,
        prompt_postgres_setup_choice,
        prompt_press_enter_when_ready,
        run_winget_postgresql_install,
    )


def _run_postgres_native_install(
    *,
    database_url: str,
    postgres_major: int,
    postgres_build: str | None,
    postgres_superpassword: str | None,
    postgres_installer_silent: bool,
) -> None:
    PostgresWindowsError, install_postgresql_windows = _import_postgres_windows()
    mode = "silent" if postgres_installer_silent else "interactive GUI"
    _log(f"Installing PostgreSQL via official Windows .exe (EDB, {mode})...")
    try:
        install_postgresql_windows(
            major=postgres_major,
            build=postgres_build,
            superpassword=postgres_superpassword,
            interactive=not postgres_installer_silent,
            repo_root=_repo_root_from_script(),
            database_url=database_url,
            log=_log,
        )
    except PostgresWindowsError as exc:
        raise SetupError(str(exc)) from exc


def _resolve_postgres_choice(
    args: argparse.Namespace,
    *,
    docker_available: bool,
) -> str | None:
    """Return setup method key, or None if postgres was already reachable (caller handles)."""
    if args.install_postgres_native:
        return "native"
    if args.postgres_choice:
        return args.postgres_choice.strip().lower()
    if args.non_interactive:
        if docker_available and not args.skip_docker:
            return "docker"
        return "skip"
    (
        build_postgres_setup_options,
        _print_hints,
        _prompt_url,
        prompt_postgres_setup_choice,
        _press_enter,
        _winget,
    ) = _import_postgres_menu()
    options = build_postgres_setup_options(
        docker_available=docker_available,
        skip_docker=args.skip_docker,
    )
    return prompt_postgres_setup_choice(options, args.database_url.strip())


def _try_boot_existing_postgres_windows(
    args: argparse.Namespace,
    repo: Path,
    url: str,
) -> bool:
    if sys.platform != "win32":
        return False
    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from postgres_windows import (  # noqa: PLC0415
        PostgresWindowsError,
        try_boot_installed_postgres,
    )

    try:
        if try_boot_installed_postgres(
            preferred_major=args.postgres_major,
            database_url=url,
            repo_root=repo,
            cli_password=args.postgres_superpassword,
            log=_log,
        ):
            return True
    except PostgresWindowsError as exc:
        raise SetupError(str(exc)) from exc
    return False


def _bootstrap_postgres(
    args: argparse.Namespace,
    repo: Path,
    url: str,
) -> tuple[bool, str]:
    """Install/connect Postgres per user choice. Returns (ready, database_url)."""
    if _postgres_reachable(url, postgres_major=args.postgres_major):
        _log("PostgreSQL already reachable.")
        return True, url

    if _try_boot_existing_postgres_windows(args, repo, url):
        _log("PostgreSQL is running (existing installation).")
        return True, url

    docker_available = _docker_compose_cmd() is not None
    choice = _resolve_postgres_choice(args, docker_available=docker_available)
    (
        build_postgres_setup_options,
        print_os_package_hints,
        prompt_database_url,
        _prompt_choice,
        prompt_press_enter_when_ready,
        run_winget_postgresql_install,
    ) = _import_postgres_menu()
    if choice != "skip":
        options = build_postgres_setup_options(
            docker_available=docker_available,
            skip_docker=args.skip_docker,
        )
        opt = next((o for o in options if o.key == choice), None)
        if opt is None:
            raise SetupError(f"Unknown PostgreSQL setup choice: {choice!r}")
        if not opt.available:
            raise SetupError(
                f"PostgreSQL setup {choice!r} is not available: {opt.unavailable_reason}",
            )
    _log(f"\nPostgreSQL setup: {choice}")

    if choice == "skip":
        _log("Skipping PostgreSQL setup.")
        return False, url

    if choice == "docker":
        _log("Starting Postgres via Docker Compose...")
        _start_postgres_compose(repo)
        _wait_for_postgres(url)
        return True, url

    if choice == "native":
        if sys.platform != "win32":
            raise SetupError("Native .exe install is only supported on Windows.")
        _run_postgres_native_install(
            database_url=url,
            postgres_major=args.postgres_major,
            postgres_build=args.postgres_build,
            postgres_superpassword=args.postgres_superpassword,
            postgres_installer_silent=args.postgres_installer_silent,
        )
        _wait_for_postgres(url)
        return True, url

    if choice == "winget":
        if sys.platform != "win32":
            raise SetupError("winget install is only supported on Windows.")
        run_winget_postgresql_install(major=args.postgres_major, log=_log)
        prompt_press_enter_when_ready(
            "Complete the winget installer if prompted, create hermes/hermes if needed.",
        )
        _wait_for_postgres(url)
        return True, url

    if choice == "packages":
        print_os_package_hints()
        prompt_press_enter_when_ready(
            "After PostgreSQL is installed and hermes/hermes exists, continue.",
        )
        _wait_for_postgres(url)
        return True, url

    if choice == "custom_url":
        url = prompt_database_url(url)
        _wait_for_postgres(url)
        return True, url

    if choice == "manual":
        prompt_press_enter_when_ready(
            "Start your PostgreSQL server (or point HERMES_DATABASE_URL at it), "
            f"then continue. Expected URL: {url}",
        )
        _wait_for_postgres(url)
        return True, url

    raise SetupError(f"Unknown postgres setup choice: {choice!r}")


def _start_postgres_compose(repo: Path) -> None:
    compose = repo / COMPOSE_FILE
    if not compose.is_file():
        raise SetupError(f"Missing {compose}; cannot start Postgres via Docker.")
    cmd = _docker_compose_cmd()
    if not cmd:
        raise SetupError(
            "Docker is not available. Install Docker Desktop (Windows/macOS) or docker.io (Linux), "
            "or run PostgreSQL yourself and set HERMES_DATABASE_URL.",
        )
    _run([*cmd, "-f", str(compose), "up", "-d", "postgres"], cwd=repo)


def apply_event_store_schema(
    poetry: str,
    repo: Path,
    url: str,
    *,
    prefer_psql: bool,
) -> None:
    del poetry, prefer_psql  # apply via scripts/postgres_schema (psql under Program Files on Windows)
    sql_path = repo / SCHEMA_REL
    if not sql_path.is_file():
        raise SetupError(f"Schema file not found: {sql_path}")
    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from postgres_schema import apply_sql_file  # noqa: PLC0415

    if not apply_sql_file(url, sql_path, log=_log):
        raise SetupError(f"Failed to apply schema: {sql_path}")


def _seed_config(poetry: str, repo: Path, url: str) -> None:
    env = os.environ.copy()
    env["HERMES_DATABASE_URL"] = url
    env.setdefault("HERMES_REPO_ROOT", str(repo))
    _run(
        [poetry, "run", "hermes-config", "seed-from-repo", "--repo-root", str(repo)],
        cwd=repo,
        env=env,
    )


def _check_ollama(host: str = "http://127.0.0.1:11434") -> bool:
    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from ollama_setup import ollama_reachable  # noqa: PLC0415

    return ollama_reachable(host)


def _import_ollama_setup():
    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from ollama_setup import (  # noqa: PLC0415
        OllamaSetupError,
        bootstrap_ollama,
        models_from_repo,
        ollama_api_host,
    )

    return OllamaSetupError, bootstrap_ollama, models_from_repo, ollama_api_host


def _bootstrap_ollama(args: argparse.Namespace, repo: Path) -> bool:
    if args.skip_ollama:
        return _check_ollama(args.ollama_host)

    OllamaSetupError, bootstrap_ollama, models_from_repo, ollama_api_host = _import_ollama_setup()
    models: list[str] | None = None
    if args.ollama_models:
        models = [m.strip() for m in args.ollama_models.split(",") if m.strip()]
    elif args.ollama_pull_only:
        models = models_from_repo(repo)

    choice = args.ollama_choice
    if choice is None and args.install_ollama:
        choice = None  # bootstrap picks platform default

    try:
        return bootstrap_ollama(
            repo=repo,
            host=ollama_api_host(args.ollama_host),
            choice=choice,
            non_interactive=args.non_interactive or bool(args.install_ollama),
            skip_pull=args.skip_ollama_pull,
            models=models,
            enable_llm=not args.no_enable_llm,
            log=_log,
        )
    except OllamaSetupError as exc:
        raise SetupError(str(exc)) from exc


def _print_next_steps(
    repo: Path,
    url: str,
    *,
    ollama_ok: bool,
    with_faiss: bool,
) -> None:
    _log("")
    _log("=== Hermes setup complete ===")
    _log(f"  Repo:     {repo}")
    _log(f"  Database: {url}")
    _log("")
    _log("Environment file:")
    _log(f"  {repo / '.env'}  (see .env.example; loaded automatically by Hermes apps)")
    _log("")
    _log("PowerShell environment (current session; optional if using .env):")
    _log(f'  $env:HERMES_REPO_ROOT = "{repo}"')
    _log(f'  $env:HERMES_DATABASE_URL = "{url}"')
    _log('  $env:HERMES_SKIP_PREFLIGHT = "1"   # optional for tests')
    _log("")
    _log("Unix:")
    _log(f'  export HERMES_REPO_ROOT="{repo}"')
    _log(f'  export HERMES_DATABASE_URL="{url}"')
    _log('  export HERMES_SKIP_PREFLIGHT=1')
    _log("")
    _log("Verify:")
    _log("  poetry run pytest tests -q -m \"not integration\"")
    _log("  .\\scripts\\run_integration_like_ci.ps1   # or bash scripts/run_integration_like_ci.sh")
    _log("")
    _log("Run API:")
    _log("  poetry run hermes-api")
    _log("Run console:")
    _log("  poetry run streamlit run packages/hermes_console/app.py")
    if ollama_ok:
        _log("")
        _log("Ollama: ready (HERMES_USE_LLM=1 if enabled in .env)")
        _log("  poetry run hermes-preflight   # verify model routing")
    else:
        _log("")
        _warn(
            "Ollama was not configured. Re-run install with an Ollama menu choice, "
            "or install from https://ollama.com and set HERMES_USE_LLM=1 in .env.",
        )
    if with_faiss:
        _log("")
        _log("FAISS index (optional):")
        _log("  poetry run python scripts/build_bundle_faiss_index.py")


def _check_prerequisites(*, install_poetry: bool) -> list[str]:
    issues: list[str] = []
    if not _version_at_least(_python_version(), MIN_PYTHON):
        issues.append(
            f"Python {_python_version()[0]}.{_python_version()[1]} found; "
            f"need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        )
    elif not _version_at_least(_python_version(), REC_PYTHON):
        _warn(
            f"Python {_python_version()[0]}.{_python_version()[1]} works; "
            f"{REC_PYTHON[0]}.{REC_PYTHON[1]}+ is recommended (matches CI).",
        )
    if install_poetry and not _find_poetry():
        _log("Poetry: will install via pip")
    elif not _find_poetry():
        issues.append("Poetry not on PATH")
    else:
        _log(f"Poetry: {_find_poetry()}")
    if _which("git"):
        _log(f"git: {_which('git')}")
    else:
        _warn("git not on PATH (only needed for --clone)")
    compose = _docker_compose_cmd()
    if compose:
        _log(f"Docker Compose: {' '.join(compose)}")
    else:
        _warn("Docker Compose not available; you must provide PostgreSQL yourself")
    if _which("psql"):
        _log(f"psql: {_which('psql')}")
    else:
        _log("psql: not on PATH (schema apply will use psycopg via Poetry)")
    if _check_ollama():
        _log("Ollama: reachable at http://127.0.0.1:11434")
    else:
        _log("Ollama: not reachable (optional; install script can set up)")
    return issues


def _load_repo_dotenv() -> None:
    repo = _repo_root_from_script()
    packages = repo / "packages"
    if str(packages) not in sys.path:
        sys.path.insert(0, str(packages))
    from hermes_env import load_dotenv  # noqa: PLC0415

    load_dotenv(repo_root=repo)


def main(argv: list[str] | None = None) -> int:
    _load_repo_dotenv()
    parser = argparse.ArgumentParser(
        description="Install and bootstrap a Hermes local development environment.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Hermes repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--clone",
        metavar="URL",
        default=None,
        help="Clone Hermes from this git URL before setup",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="Directory for --clone (default: ./Hermes next to cwd)",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("HERMES_DATABASE_URL", DEFAULT_DATABASE_URL),
        help=f"PostgreSQL URL (default: {DEFAULT_DATABASE_URL})",
    )
    parser.add_argument(
        "--skip-postgres",
        action="store_true",
        help="Do not start Docker Postgres or apply schema",
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Do not run docker compose; only connect if Postgres is already up",
    )
    parser.add_argument(
        "--no-poetry-install",
        action="store_true",
        help="Do not run `poetry install`",
    )
    parser.add_argument(
        "--no-install-poetry",
        action="store_true",
        help="Fail if Poetry is missing instead of installing via pip",
    )
    parser.add_argument(
        "--with-faiss",
        action="store_true",
        help="poetry install --with faiss",
    )
    parser.add_argument(
        "--with-redis",
        action="store_true",
        help="poetry install --with redis (dispatch worker profile)",
    )
    parser.add_argument(
        "--seed-config",
        action="store_true",
        help="Run hermes-config seed-from-repo after schema apply",
    )
    parser.add_argument(
        "--run-unit-tests",
        action="store_true",
        help="Run poetry run pytest -m 'not integration' after setup",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Print prerequisite checks and exit",
    )
    parser.add_argument(
        "--prefer-psql",
        action="store_true",
        help="Use psql for schema apply when available (default: psycopg)",
    )
    parser.add_argument(
        "--install-postgres-native",
        action="store_true",
        help=(
            "Windows only: download the official PostgreSQL EDB installer (.exe), "
            "run it silently, and create the hermes/hermes database (requires admin/UAC)"
        ),
    )
    parser.add_argument(
        "--postgres-major",
        type=int,
        default=16,
        help="PostgreSQL major version for --install-postgres-native (default: 16)",
    )
    parser.add_argument(
        "--postgres-build",
        default=None,
        help="Exact EDB build id, e.g. 16.9-1 (default: auto-detect newest 16.x)",
    )
    parser.add_argument(
        "--postgres-superpassword",
        default=None,
        help=(
            "postgres superuser password for native install "
            "(default: HERMES_POSTGRES_SUPERPASSWORD or hermes_setup)"
        ),
    )
    parser.add_argument(
        "--postgres-installer-silent",
        action="store_true",
        help="Use unattended silent .exe install (default: interactive GUI wizard)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help=(
            "Do not prompt when PostgreSQL is missing; use Docker if available, "
            "otherwise skip Postgres setup"
        ),
    )
    parser.add_argument(
        "--postgres-choice",
        choices=("docker", "native", "winget", "manual", "custom_url", "skip", "packages"),
        default=None,
        help="Non-interactive Postgres setup method (skips the menu)",
    )
    parser.add_argument(
        "--skip-ollama",
        action="store_true",
        help="Do not install or configure Ollama",
    )
    parser.add_argument(
        "--install-ollama",
        action="store_true",
        help=(
            "Install/start Ollama when missing (winget on Windows, brew on macOS, "
            "install.sh on Linux) and pull default models"
        ),
    )
    parser.add_argument(
        "--ollama-choice",
        choices=("winget", "download", "brew", "script", "pull", "manual", "skip"),
        default=None,
        help="Ollama setup method (skips the Ollama menu)",
    )
    parser.add_argument(
        "--ollama-host",
        default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        help="Ollama API base URL (default: http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--ollama-models",
        default=None,
        help="Comma-separated models to ollama pull (default: from configs/model-routing.yaml)",
    )
    parser.add_argument(
        "--skip-ollama-pull",
        action="store_true",
        help="Install Ollama but do not download models (ollama pull)",
    )
    parser.add_argument(
        "--ollama-pull-only",
        action="store_true",
        help="Only pull models (implies reachable Ollama; sets --ollama-choice pull)",
    )
    parser.add_argument(
        "--no-enable-llm",
        action="store_true",
        help="Do not set HERMES_USE_LLM=1 in .env after Ollama is ready",
    )
    parser.add_argument(
        "--skip-linux-desktop-deps",
        action="store_true",
        help="Do not install GTK/WebKit system packages on Linux (pywebview)",
    )
    parser.add_argument(
        "--verify-ollama",
        action="store_true",
        help="Run poetry run hermes-preflight after Ollama setup (slow; needs models)",
    )
    args = parser.parse_args(argv)

    if args.ollama_pull_only and args.ollama_choice is None:
        args.ollama_choice = "pull"

    _log("Hermes install - prerequisite check")
    issues = _check_prerequisites(install_poetry=not args.no_install_poetry)
    if issues:
        for item in issues:
            _warn(item)
        if args.check_only:
            return 1
        raise SetupError("Fix prerequisites above and re-run.")
    if args.check_only:
        _log("Prerequisite check passed.")
        return 0

    if args.install_postgres_native and sys.platform != "win32":
        raise SetupError("--install-postgres-native is only supported on Windows.")
    if args.postgres_choice == "native" and sys.platform != "win32":
        raise SetupError("--postgres-choice native is only supported on Windows.")

    repo = args.repo_root.resolve() if args.repo_root else _repo_root_from_script()
    if args.clone:
        target = args.target_dir or (Path.cwd() / "Hermes")
        repo = _clone_repo(args.clone, target)
    elif not _is_hermes_repo(repo):
        raise SetupError(
            f"Not a Hermes repo (missing pyproject.toml or schema): {repo}. "
            "Use --clone URL or run from a checkout.",
        )

    _log(f"\nRepository: {repo}")
    poetry = _ensure_poetry(install=not args.no_install_poetry)

    if not args.no_poetry_install:
        _log("\nInstalling Python dependencies (Poetry)...")
        _poetry_install(
            poetry,
            repo,
            with_faiss=args.with_faiss,
            with_redis=args.with_redis,
        )

    if sys.platform.startswith("linux") and not args.skip_linux_desktop_deps:
        _log("\nLinux desktop (GTK / pywebview)...")
        packages = repo / "packages"
        if str(packages) not in sys.path:
            sys.path.insert(0, str(packages))
        from hermes_env.desktop_common import resolve_python_command
        from hermes_env.linux_desktop_deps import ensure_linux_desktop_deps

        py_cmd = resolve_python_command(repo)
        ok, detail = ensure_linux_desktop_deps(repo, py_cmd, log=_log)
        if not ok:
            _warn(f"Linux desktop deps: {detail}")
        elif "already" not in detail.lower():
            _log(detail)

    url = args.database_url.strip()
    postgres_ready = False
    if not args.skip_postgres:
        _log("\nPostgreSQL bootstrap...")
        try:
            postgres_ready, url = _bootstrap_postgres(args, repo, url)
        except SetupError:
            raise
        if not postgres_ready and args.non_interactive:
            _warn(
                "PostgreSQL was not configured. Re-run without --non-interactive for an "
                "interactive menu, or pass --postgres-choice docker|native|manual|skip.",
            )

    if postgres_ready:
        _log("Applying event store schema...")
        apply_event_store_schema(poetry, repo, url, prefer_psql=args.prefer_psql)
        if args.seed_config:
            _log("Seeding config from repo YAML into Postgres...")
            _seed_config(poetry, repo, url)

    os.environ.setdefault("HERMES_REPO_ROOT", str(repo))
    if postgres_ready:
        os.environ["HERMES_DATABASE_URL"] = url

    ollama_ok = False
    if not args.skip_ollama:
        _log("\nOllama bootstrap...")
        ollama_ok = _bootstrap_ollama(args, repo)
        if args.verify_ollama and ollama_ok:
            _log("\nVerifying Ollama preflight...")
            env = os.environ.copy()
            env.setdefault("HERMES_REPO_ROOT", str(repo))
            _run([poetry, "run", "hermes-preflight"], cwd=repo, env=env)
    else:
        ollama_ok = _check_ollama(args.ollama_host)

    if args.run_unit_tests:
        _log("\nRunning unit tests (not integration)...")
        env = os.environ.copy()
        env.setdefault("HERMES_SKIP_PREFLIGHT", "1")
        _run(
            [poetry, "run", "pytest", "tests", "-q", "-m", "not integration"],
            cwd=repo,
            env=env,
        )

    _print_next_steps(
        repo,
        url if postgres_ready else "(Postgres not configured - set HERMES_DATABASE_URL)",
        ollama_ok=ollama_ok,
        with_faiss=args.with_faiss,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SetupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
