"""Interactive PostgreSQL setup menu when no server is reachable."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PostgresSetupOption:
    key: str
    title: str
    explanation: str
    available: bool
    unavailable_reason: str = ""


def _which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


def winget_available() -> bool:
    return _which("winget") is not None


def build_postgres_setup_options(
    *,
    docker_available: bool,
    skip_docker: bool,
    platform: str | None = None,
) -> list[PostgresSetupOption]:
    plat = platform or sys.platform
    docker_ok = docker_available and not skip_docker
    docker_reason = ""
    if skip_docker:
        docker_reason = "Disabled by --skip-docker."
    elif not docker_available:
        docker_reason = "Docker or Docker Compose was not found on PATH."

    options: list[PostgresSetupOption] = [
        PostgresSetupOption(
            key="docker",
            title="Docker Compose",
            explanation=(
                "Starts the postgres:16-alpine service from this repository's "
                "docker-compose.yml on port 5432 with database user/password "
                "hermes/hermes (same as CI). Nothing is installed on the host except "
                "the container. Best if you already use Docker Desktop."
            ),
            available=docker_ok,
            unavailable_reason=docker_reason,
        ),
    ]

    if plat == "win32":
        options.append(
            PostgresSetupOption(
                key="native",
                title="Windows installer (.exe download)",
                explanation=(
                    "If PostgreSQL is already installed under Program Files, starts "
                    "that server and skips the installer. Otherwise downloads the EDB "
                    "installer (~300 MB) and opens the setup wizard. Creates hermes/hermes. "
                    "Run as Administrator to start the Windows service. No Docker needed."
                ),
                available=True,
            ),
        )
        winget_ok = winget_available()
        options.append(
            PostgresSetupOption(
                key="winget",
                title="winget (PostgreSQL 16 package)",
                explanation=(
                    "Installs PostgreSQL.PostgreSQL.16 via Windows Package Manager. "
                    "May open an elevated installer UI. After install you may need to "
                    "create the hermes user/database manually (or press Enter here and "
                    "let setup retry once Postgres is listening)."
                ),
                available=winget_ok,
                unavailable_reason="winget was not found on PATH.",
            ),
        )
    else:
        options.append(
            PostgresSetupOption(
                key="packages",
                title="Show OS package install commands",
                explanation=(
                    "Prints suggested apt/brew commands for PostgreSQL 16 on "
                    "Linux/macOS. Does not run them automatically; you install, "
                    "create hermes/hermes, then continue."
                ),
                available=True,
            ),
        )

    options.extend(
        [
            PostgresSetupOption(
                key="manual",
                title="I already have PostgreSQL (or will start it myself)",
                explanation=(
                    "Use an existing local install, cloud instance, or a container you "
                    "start yourself. Ensure the server listens on the URL below and that "
                    "the hermes role/database exist (or use a URL you configure next)."
                ),
                available=True,
            ),
            PostgresSetupOption(
                key="custom_url",
                title="Use a different connection URL",
                explanation=(
                    "Type a custom postgresql:// URL (remote host, different port, or "
                    "superuser). Schema apply runs against that URL; you are responsible "
                    "for credentials and database creation."
                ),
                available=True,
            ),
            PostgresSetupOption(
                key="skip",
                title="Skip PostgreSQL for now",
                explanation=(
                    "Only finishes Poetry/Python setup. Apply the schema later with "
                    "scripts/apply_event_store.ps1 (or .sh) once Postgres is ready."
                ),
                available=True,
            ),
        ],
    )
    return options


def _print_menu(options: list[PostgresSetupOption], database_url: str) -> None:
    print("", flush=True)
    print("=" * 72, flush=True)
    print("PostgreSQL is not reachable", flush=True)
    print(f"  Connection URL: {database_url}", flush=True)
    print("=" * 72, flush=True)
    print("", flush=True)
    print("Choose how to set up or connect PostgreSQL:", flush=True)
    print("", flush=True)
    for index, opt in enumerate(options, start=1):
        status = "available" if opt.available else f"NOT available - {opt.unavailable_reason}"
        print(f"  [{index}] {opt.title}", flush=True)
        for line in _wrap(opt.explanation, indent=6, width=70):
            print(line, flush=True)
        print(f"      ({status})", flush=True)
        print("", flush=True)
    keys = ", ".join(opt.key for opt in options)
    print(f"Enter a number [1-{len(options)}] or option key ({keys}): ", end="", flush=True)


def _wrap(text: str, *, indent: int, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = " " * indent
    for word in words:
        chunk = word if not current.strip() else f" {word}"
        if len(current) + len(chunk) > width and current.strip():
            lines.append(current.rstrip())
            current = " " * indent + word
        else:
            current += chunk if current.strip() else (" " * indent + word)
    if current.strip():
        lines.append(current.rstrip())
    return lines


def prompt_postgres_setup_choice(
    options: list[PostgresSetupOption],
    database_url: str,
) -> str:
    key_by_index = {str(i): opt.key for i, opt in enumerate(options, start=1)}
    key_by_name = {opt.key: opt.key for opt in options}

    while True:
        _print_menu(options, database_url)
        raw = input().strip().lower()
        if not raw:
            print("Please enter a choice.", flush=True)
            continue
        chosen_key = key_by_index.get(raw) or key_by_name.get(raw)
        if chosen_key is None:
            print(f"Invalid choice: {raw!r}. Try again.", flush=True)
            continue
        opt = next(o for o in options if o.key == chosen_key)
        if not opt.available:
            print(f"Option [{opt.title}] is not available: {opt.unavailable_reason}", flush=True)
            continue
        return chosen_key


def print_os_package_hints() -> None:
    print("", flush=True)
    print("Install PostgreSQL 16 using your OS package manager, then create the app DB:", flush=True)
    print("", flush=True)
    print("  Debian/Ubuntu:", flush=True)
    print("    sudo apt update && sudo apt install -y postgresql-16 postgresql-client-16", flush=True)
    print("    sudo -u postgres createuser -P hermes   # password: hermes", flush=True)
    print("    sudo -u postgres createdb -O hermes hermes", flush=True)
    print("", flush=True)
    print("  macOS (Homebrew):", flush=True)
    print("    brew install postgresql@16", flush=True)
    print("    brew services start postgresql@16", flush=True)
    print("    createuser -s hermes && createdb -O hermes hermes", flush=True)
    print("", flush=True)


def run_winget_postgresql_install(*, major: int, log) -> None:
    package_id = f"PostgreSQL.PostgreSQL.{major}"
    log(f"Running: winget install -e --id {package_id}")
    subprocess.run(
        [
            "winget",
            "install",
            "-e",
            "--id",
            package_id,
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        check=False,
    )


def prompt_press_enter_when_ready(message: str) -> None:
    print("", flush=True)
    print(message, flush=True)
    print("Press Enter when PostgreSQL is listening...", flush=True)
    input()


def prompt_database_url(default: str) -> str:
    print("", flush=True)
    print(f"Database URL [{default}]: ", end="", flush=True)
    raw = input().strip()
    return raw or default
