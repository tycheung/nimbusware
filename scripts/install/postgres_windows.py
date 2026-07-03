"""Download and install PostgreSQL on Windows (EDB community installer).

Fetches the official ``.exe`` from ``get.enterprisedb.com``. By default launches the
**interactive** GUI wizard (recommended). Optional silent mode via ``interactive=False``.
"""

from __future__ import annotations

import ctypes
import getpass
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

ENV_POSTGRES_PASSWORD = "NIMBUSWARE_POSTGRES_SUPERPASSWORD"

EDB_DOWNLOAD_BASE = "https://get.enterprisedb.com/postgresql"
DEFAULT_MAJOR = 16
# Matches docker-compose / CI Postgres 16; override with --postgres-build.
DEFAULT_BUILD = "16.9-1"
NIMBUSWARE_DB_USER = "nimbusware"
NIMBUSWARE_DB_PASSWORD = "nimbusware"
NIMBUSWARE_DB_NAME = "nimbusware"


class PostgresWindowsError(RuntimeError):
    pass


def is_windows() -> bool:
    return sys.platform == "win32"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except OSError:
        return False


def installer_filename(build: str) -> str:
    return f"postgresql-{build}-windows-x64.exe"


def installer_url(build: str) -> str:
    return f"{EDB_DOWNLOAD_BASE}/{installer_filename(build)}"


def probe_build_exists(build: str, *, timeout_s: float = 15.0) -> bool:
    req = urllib.request.Request(installer_url(build), method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as exc:
        return exc.code == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def resolve_build(*, major: int, build: str | None) -> str:
    if build:
        if not probe_build_exists(build):
            raise PostgresWindowsError(
                f"Installer not found for build {build!r}: {installer_url(build)}",
            )
        return build
    # Try patch releases for this major (newest first).
    candidates = (
        [f"{major}.9-{patch}" for patch in range(5, 0, -1)]
        + [f"{major}.8-{patch}" for patch in range(5, 0, -1)]
        + [
            f"{major}.7-1",
            f"{major}.6-2",
            f"{major}.6-1",
            f"{major}.5-1",
            f"{major}.4-1",
        ]
    )
    for candidate in candidates:
        if candidate.startswith(f"{major}.") and probe_build_exists(candidate):
            return candidate
    raise PostgresWindowsError(
        f"Could not find a downloadable PostgreSQL {major} Windows installer on EDB. "
        f"Pass --postgres-build explicitly (see {EDB_DOWNLOAD_BASE}).",
    )


def psql_bin_for_major(major: int) -> Path | None:
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidate = Path(program_files) / "PostgreSQL" / str(major) / "bin" / "psql.exe"
    return candidate if candidate.is_file() else None


def discover_installed_postgres_major(*, preferred: int = DEFAULT_MAJOR) -> int | None:
    if psql_bin_for_major(preferred):
        return preferred
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    pg_root = program_files / "PostgreSQL"
    if pg_root.is_dir():
        majors: list[int] = []
        for child in pg_root.iterdir():
            if child.is_dir() and (child / "bin" / "psql.exe").is_file():
                try:
                    majors.append(int(child.name))
                except ValueError:
                    continue
        if majors:
            return max(majors)
    psql_on_path = shutil.which("psql")
    if psql_on_path:
        parts = Path(psql_on_path).parts
        for i, part in enumerate(parts):
            if part == "PostgreSQL" and i + 1 < len(parts):
                try:
                    return int(parts[i + 1])
                except ValueError:
                    break
    return None


def postgres_is_installed(*, preferred_major: int = DEFAULT_MAJOR) -> bool:
    return discover_installed_postgres_major(preferred=preferred_major) is not None


def postgres_port_open(
    host: str = "127.0.0.1",
    port: int = 5432,
    *,
    timeout_s: float = 2.0,
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def wait_for_postgres_port(
    host: str = "127.0.0.1",
    port: int = 5432,
    *,
    attempts: int = 30,
    sleep_s: float = 2.0,
    log,
) -> bool:
    log(f"Waiting for PostgreSQL on {host}:{port} ...")
    for i in range(attempts):
        if postgres_port_open(host, port):
            log("PostgreSQL port is accepting connections.")
            return True
        if i < attempts - 1:
            time.sleep(sleep_s)
    return False


def _parse_database_url(url: str) -> tuple[str, str, str, str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"Not a PostgreSQL URL: {url!r}")
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 5432)
    dbname = unquote((parsed.path or "/").lstrip("/") or "postgres")
    return user, password, host, port, dbname


def _psql_database_url_probe(url: str, *, major: int | None = None) -> bool:
    try:
        user, password, host, port, dbname = _parse_database_url(url)
    except ValueError:
        return False
    psql = psql_bin_for_major(major) if major else None
    if psql is None:
        on_path = shutil.which("psql")
        psql = Path(on_path) if on_path else None
    if psql is None:
        return False
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    proc = subprocess.run(
        [
            str(psql),
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            dbname,
            "-tAc",
            "SELECT 1",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.returncode == 0


def postgres_reachable(
    url: str,
    *,
    timeout_s: float = 2.0,
    major: int | None = None,
) -> bool:
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=int(timeout_s)):
            return True
    except ImportError:
        pass
    except Exception:
        pass
    return _psql_database_url_probe(url, major=major)


def wait_for_postgres_url(
    url: str,
    *,
    attempts: int = 30,
    sleep_s: float = 2.0,
    major: int | None = None,
    log,
) -> bool:
    log(f"Waiting for PostgreSQL at {url} ...")
    for i in range(attempts):
        if postgres_reachable(url, major=major):
            log("PostgreSQL is accepting connections.")
            return True
        if i < attempts - 1:
            time.sleep(sleep_s)
    return False


def prepend_postgres_bin(major: int) -> Path | None:
    bin_dir = psql_bin_for_major(major)
    if bin_dir is None:
        return None
    bin_path = str(bin_dir.parent)
    os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
    return bin_dir


def _download(url: str, dest: Path, *, log) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        log(f"Using cached installer: {dest}")
        return
    log(f"Downloading {url}")
    log(f"  -> {dest}")
    last_pct = [-1]

    def report(block_count: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        done = min(block_count * block_size, total_size)
        pct = done * 100 // total_size
        if pct >= last_pct[0] + 5:
            last_pct[0] = pct
            log(f"  ... {pct}%")

    urllib.request.urlretrieve(url, dest, reporthook=report)  # noqa: S310


def _installer_args(
    *,
    superpassword: str,
    port: int,
    prefix: Path | None,
) -> list[str]:
    args = [
        "--mode",
        "unattended",
        "--unattendedmodeui",
        "none",
        "--enable-components",
        "server,commandlinetools",
        "--disable-components",
        "stackbuilder",
        "--superaccount",
        "postgres",
        "--superpassword",
        superpassword,
        "--servicepassword",
        superpassword,
        "--serverport",
        str(port),
    ]
    if prefix is not None:
        args.extend(["--prefix", str(prefix)])
    return args


def _try_start_service(major: int, *, log) -> None:
    if not is_admin():
        log(
            "Skipping Windows service start (not running as Administrator). "
            "If PostgreSQL is not running, start service postgresql-x64-"
            f"{major} from services.msc or re-run setup as Admin.",
        )
        return
    for name in (f"postgresql-x64-{major}", f"postgresql-{major}"):
        proc = subprocess.run(
            ["sc", "query", name],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            continue
        log(f"Starting Windows service {name}...")
        start = subprocess.run(
            ["net", "start", name],
            capture_output=True,
            text=True,
        )
        if start.returncode != 0:
            combined = ((start.stdout or "") + (start.stderr or "")).lower()
            if "access is denied" in combined or "error 5" in combined:
                log(
                    f"Could not start {name} (Access denied). "
                    "Start the service manually if Postgres is not already running.",
                )
            else:
                log((start.stdout or "") + (start.stderr or ""))
        return


def _run_installer_elevated(
    exe: Path,
    args: list[str],
    *,
    major: int,
    interactive: bool,
    log,
) -> None:
    if interactive:
        log(f"Launching PostgreSQL installer GUI: {exe}")
        log("Complete the setup wizard (use port 5432; note the postgres superuser password).")
        launch_args: list[str] = []
    else:
        log(f"Launching PostgreSQL silent installer: {exe.name}")
        launch_args = args
    arg_str = subprocess.list2cmdline([str(exe), *launch_args]) if launch_args else ""
    if is_admin():
        cmd = [str(exe), *launch_args]
        _run_checked(cmd, log=log)
        if not interactive:
            _try_start_service(major, log=log)
        return
    ret = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None,
        "runas",
        str(exe),
        arg_str if launch_args else None,
        None,
        1,  # SW_SHOWNORMAL
    )
    if ret <= 32:
        raise PostgresWindowsError(
            "Could not launch the PostgreSQL installer elevated (ShellExecute "
            f"returned {ret}). Re-run PowerShell as Administrator, or approve the UAC prompt.",
        )
    if interactive:
        log("Installer opened in a separate window (UAC). Finish the wizard, then continue here.")
        return
    log("Silent installer launched with elevation.")
    import time

    for _ in range(120):
        if psql_bin_for_major(major):
            _try_start_service(major, log=log)
            return
        time.sleep(3)
    raise PostgresWindowsError(
        "Installer started but PostgreSQL bin directory was not found after 6 minutes. "
        "Complete the installer manually, then re-run setup.",
    )


def _wait_for_installer_gui(major: int, *, log) -> None:
    log("")
    log("When the PostgreSQL installer finishes, press Enter to continue...")
    try:
        input()
    except EOFError:
        pass
    if not psql_bin_for_major(major):
        raise PostgresWindowsError(
            f"PostgreSQL {major} still not found under Program Files. "
            "Finish the installer or install to the default location, then try again.",
        )


def _run_checked(cmd: list[str], *, log, env: dict[str, str] | None = None) -> None:
    log(f"  $ {subprocess.list2cmdline(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def _psql_probe(major: int, superpassword: str) -> tuple[bool, str]:
    psql = psql_bin_for_major(major)
    if psql is None:
        return False, "psql.exe not found"
    env = os.environ.copy()
    env["PGPASSWORD"] = superpassword
    proc = subprocess.run(
        [
            str(psql),
            "-h",
            "127.0.0.1",
            "-p",
            "5432",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-tAc",
            "SELECT 1",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    err = ((proc.stderr or "") + (proc.stdout or "")).strip()
    return False, err


def _load_nimbusware_dotenv(repo_root: Path | None) -> Path | None:
    if repo_root is None:
        return None
    packages = repo_root / "packages"
    if str(packages) not in sys.path:
        sys.path.insert(0, str(packages))
    from nimbusware_env import load_dotenv  # noqa: PLC0415

    return load_dotenv(repo_root=repo_root)


def _save_postgres_password_to_env(repo_root: Path, password: str, *, log) -> None:
    from nimbusware_env import set_env_var  # noqa: PLC0415

    path = set_env_var(ENV_POSTGRES_PASSWORD, password, repo_root=repo_root)
    log(f"Saved {ENV_POSTGRES_PASSWORD} to {path}")


def resolve_postgres_superpassword(
    major: int,
    *,
    repo_root: Path | None,
    cli_password: str | None,
    log,
) -> str:
    _load_nimbusware_dotenv(repo_root)
    tried: list[str] = []
    for candidate in (
        cli_password,
        os.environ.get(ENV_POSTGRES_PASSWORD, "").strip(),
        "nimbusware_setup",
    ):
        if not candidate or candidate in tried:
            continue
        tried.append(candidate)
        ok, err = _psql_probe(major, candidate)
        if ok:
            os.environ[ENV_POSTGRES_PASSWORD] = candidate
            return candidate
        if "password authentication failed" in err.lower():
            log(
                f"{ENV_POSTGRES_PASSWORD} in .env did not authenticate "
                "(wrong postgres superuser password).",
            )
        elif err:
            log(f"PostgreSQL connection check failed: {err}")

    log("")
    log("Enter the password you set for the PostgreSQL 'postgres' user in the installer wizard.")
    for attempt in range(5):
        try:
            entered = getpass.getpass("postgres superuser password: ")
        except (EOFError, KeyboardInterrupt) as exc:
            raise PostgresWindowsError("Password entry cancelled.") from exc
        if not entered:
            log("Password cannot be empty.")
            continue
        ok, err = _psql_probe(major, entered)
        if ok:
            if repo_root:
                _save_postgres_password_to_env(repo_root, entered, log=log)
            os.environ[ENV_POSTGRES_PASSWORD] = entered
            return entered
        log("Authentication failed. Try again.")
        if err and "password authentication failed" not in err.lower():
            log(err)
    raise PostgresWindowsError(
        "Could not authenticate as PostgreSQL user 'postgres'. "
        f"Set {ENV_POSTGRES_PASSWORD} in .env or verify the server is running.",
    )


def ensure_nimbusware_role(
    major: int,
    *,
    superpassword: str,
    log,
) -> None:
    psql = psql_bin_for_major(major)
    if psql is None:
        raise PostgresWindowsError(f"psql.exe not found under PostgreSQL {major}")
    env = os.environ.copy()
    env["PGPASSWORD"] = superpassword
    host = "127.0.0.1"
    port = "5432"
    base = [str(psql), "-h", host, "-p", port, "-U", "postgres", "-v", "ON_ERROR_STOP=1"]
    # Use $tag$ not $$ so PowerShell parents do not treat $ as variables.
    sql_user = (
        f"DO $nw$ BEGIN CREATE USER {NIMBUSWARE_DB_USER} WITH PASSWORD "
        f"'{NIMBUSWARE_DB_PASSWORD}' CREATEDB; EXCEPTION WHEN duplicate_object THEN "
        f"ALTER USER {NIMBUSWARE_DB_USER} WITH PASSWORD '{NIMBUSWARE_DB_PASSWORD}'; "
        f"END $nw$;"
    )
    sql_db = f"SELECT 'ok' FROM pg_database WHERE datname = '{NIMBUSWARE_DB_NAME}';"
    log("Creating application database role (if missing)...")
    _run_checked([*base, "-d", "postgres", "-c", sql_user], log=log, env=env)
    proc = subprocess.run(
        [*base, "-d", "postgres", "-tAc", sql_db],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    if proc.stdout.strip():
        log(f"Database {NIMBUSWARE_DB_NAME!r} already exists.")
        return
    log(f"Creating database {NIMBUSWARE_DB_NAME!r}...")
    _run_checked(
        [
            *base,
            "-d",
            "postgres",
            "-c",
            f"CREATE DATABASE {NIMBUSWARE_DB_NAME} OWNER {NIMBUSWARE_DB_USER};",
        ],
        log=log,
        env=env,
    )


def configure_existing_postgres(
    *,
    major: int,
    database_url: str,
    repo_root: Path | None,
    cli_password: str | None,
    log,
) -> Path:
    """Start an on-disk PostgreSQL install and create the nimbusware role/database."""
    psql_path = psql_bin_for_major(major)
    if psql_path is None:
        raise PostgresWindowsError(f"PostgreSQL {major} binaries not found")
    log(f"PostgreSQL {major} already installed: {psql_path.parent.parent}")
    prepend_postgres_bin(major)
    if postgres_reachable(database_url, major=major):
        log("Database URL is already reachable.")
        bin_dir = prepend_postgres_bin(major)
        if bin_dir is None:
            raise PostgresWindowsError(f"PostgreSQL {major} install did not produce psql.exe")
        return bin_dir

    if not postgres_port_open():
        log("PostgreSQL is installed but port 5432 is closed; attempting to start the service...")
        _try_start_service(major, log=log)
        if not wait_for_postgres_port(log=log):
            raise PostgresWindowsError(
                "PostgreSQL is installed but not listening on port 5432. "
                "Start the postgresql-x64-"
                f"{major} service from services.msc (or run setup as Administrator), then retry.",
            )
    pw = resolve_postgres_superpassword(
        major,
        repo_root=repo_root,
        cli_password=cli_password,
        log=log,
    )
    ensure_nimbusware_role(major, superpassword=pw, log=log)
    if not wait_for_postgres_url(
        database_url,
        attempts=15,
        sleep_s=2.0,
        major=major,
        log=log,
    ):
        raise PostgresWindowsError(
            f"Created role/database but {database_url} is not accepting connections. "
            "Check pg_hba.conf or set NIMBUSWARE_DATABASE_URL to a working URL.",
        )
    bin_dir = prepend_postgres_bin(major)
    if bin_dir is None:
        raise PostgresWindowsError(f"PostgreSQL {major} install did not produce psql.exe")
    return bin_dir


def try_boot_installed_postgres(
    *,
    preferred_major: int,
    database_url: str,
    repo_root: Path | None,
    cli_password: str | None,
    log,
) -> bool:
    """If Postgres is installed locally, start it and configure Nimbusware. Returns True on success."""
    discovered = discover_installed_postgres_major(preferred=preferred_major)
    if discovered is None:
        return False
    configure_existing_postgres(
        major=discovered,
        database_url=database_url,
        repo_root=repo_root,
        cli_password=cli_password,
        log=log,
    )
    return postgres_reachable(database_url, major=discovered)


def install_postgresql_windows(
    *,
    major: int = DEFAULT_MAJOR,
    build: str | None = None,
    cache_dir: Path | None = None,
    superpassword: str | None = None,
    port: int = 5432,
    interactive: bool = True,
    repo_root: Path | None = None,
    database_url: str | None = None,
    log=print,
) -> Path:
    """Install Postgres if missing, else boot existing install and create nimbusware DB."""
    if not is_windows():
        raise PostgresWindowsError("Native PostgreSQL install is only supported on Windows.")
    _load_nimbusware_dotenv(repo_root)
    if repo_root:
        env_file = repo_root / ".env"
        if env_file.is_file():
            log(f"Using environment from {env_file}")
        else:
            log(f"No .env at {env_file} (copy .env.example); will create entries as needed.")
    db_url = (database_url or os.environ.get("NIMBUSWARE_DATABASE_URL", "")).strip()
    if not db_url:
        db_url = f"postgresql://{NIMBUSWARE_DB_USER}:{NIMBUSWARE_DB_PASSWORD}@127.0.0.1:{port}/{NIMBUSWARE_DB_NAME}"

    discovered = discover_installed_postgres_major(preferred=major)
    if discovered is not None:
        return configure_existing_postgres(
            major=discovered,
            database_url=db_url,
            repo_root=repo_root,
            cli_password=superpassword,
            log=log,
        )

    log("PostgreSQL not found on this machine; downloading the installer...")
    resolved_build = resolve_build(major=major, build=build)
    cache = cache_dir or (Path.home() / ".cache" / "nimbusware_install")
    exe_path = cache / installer_filename(resolved_build)
    _download(installer_url(resolved_build), exe_path, log=log)

    pw = superpassword or os.environ.get(ENV_POSTGRES_PASSWORD, "").strip() or "nimbusware_setup"
    silent_args = _installer_args(superpassword=pw, port=port, prefix=None)

    _run_installer_elevated(
        exe_path,
        silent_args,
        major=major,
        interactive=interactive,
        log=log,
    )
    if interactive:
        _wait_for_installer_gui(major, log=log)

    installed_major = discover_installed_postgres_major(preferred=major)
    if installed_major is None:
        raise PostgresWindowsError(
            f"PostgreSQL {major} install did not produce psql.exe under Program Files.",
        )
    return configure_existing_postgres(
        major=installed_major,
        database_url=db_url,
        repo_root=repo_root,
        cli_password=superpassword,
        log=log,
    )
