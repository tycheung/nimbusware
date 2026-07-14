"""Apply Nimbusware ``postgres.sql`` (platform + Nimbusware agent schema) using ``psql`` when available."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def find_psql_binary() -> str | None:
    on_path = shutil.which("psql")
    if on_path:
        return on_path
    if sys.platform == "win32":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        for major in (17, 16, 15, 14):
            candidate = program_files / "PostgreSQL" / str(major) / "bin" / "psql.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def _connection_args(url: str) -> tuple[list[str], dict[str, str]]:
    parsed = urlparse(url)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"Not a PostgreSQL URL: {url!r}")
    env = os.environ.copy()
    password = unquote(parsed.password or "")
    if password:
        env["PGPASSWORD"] = password
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 5432)
    user = unquote(parsed.username or "")
    dbname = unquote((parsed.path or "/").lstrip("/") or "postgres")
    args = [
        "-h",
        host,
        "-p",
        port,
        "-U",
        user,
        "-d",
        dbname,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    return args, env


def apply_sql_file(url: str, sql_path: Path, *, log=print, reset: bool = False) -> bool:
    """Apply a SQL file. Returns True on success.

    When ``reset`` is True (or ``sql_path`` is the bootstrap ``postgres.sql``),
    drop and recreate ``public`` before applying so leftover tables cannot drift.
    """
    if not sql_path.is_file():
        raise FileNotFoundError(sql_path)
    reset_path = sql_path.parent / "reset_public.sql"
    should_reset = reset or sql_path.name == "postgres.sql"
    files: list[Path] = []
    if should_reset and reset_path.is_file():
        files.append(reset_path)
    files.append(sql_path)
    psql = find_psql_binary()
    if psql:
        conn_args, env = _connection_args(url)
        for path in files:
            cmd = [psql, *conn_args, "-f", str(path)]
            log(f"  $ {' '.join(cmd)}")
            proc = subprocess.run(cmd, env=env, text=True)
            if proc.returncode != 0:
                return False
        return True
    # psycopg cannot reliably execute multi-statement bootstrap SQL on all platforms.
    try:
        import psycopg
    except ImportError:
        return False
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for path in files:
                cur.execute(path.read_text(encoding="utf-8"))
    return True


def reset_and_apply_schema(url: str, *, log=print) -> bool:
    """Drop public schema and apply packages/store/schema/postgres.sql."""
    repo = Path(__file__).resolve().parents[2]
    sql_path = repo / "packages" / "store" / "schema" / "postgres.sql"
    return apply_sql_file(url, sql_path, log=log, reset=True)


def event_store_present(url: str) -> bool:
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=5) as conn:
            row = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'event_store'",
            ).fetchone()
        return row is not None
    except Exception:
        return False
