"""Provision the Nimbusware application role/database from an admin PostgreSQL URL."""

from __future__ import annotations

import os
from collections.abc import Callable
from urllib.parse import quote, unquote, urlparse

NIMBUSWARE_DB_USER = "nimbusware"
NIMBUSWARE_DB_PASSWORD = "nimbusware"
NIMBUSWARE_DB_NAME = "nimbusware"
ENV_POSTGRES_ADMIN_URL = "NIMBUSWARE_POSTGRES_ADMIN_URL"


class PostgresProvisionError(RuntimeError):
    pass


def default_app_database_url(*, host: str = "127.0.0.1", port: str = "5432") -> str:
    user = quote(NIMBUSWARE_DB_USER, safe="")
    password = quote(NIMBUSWARE_DB_PASSWORD, safe="")
    return f"postgresql://{user}:{password}@{host}:{port}/{NIMBUSWARE_DB_NAME}"


def parse_database_url(url: str) -> tuple[str, str, str, str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("postgresql", "postgres"):
        raise PostgresProvisionError(f"Expected postgresql:// URL, got scheme {parsed.scheme!r}")
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 5432)
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    dbname = unquote((parsed.path or "/").lstrip("/") or "postgres")
    if not user:
        raise PostgresProvisionError("Database URL is missing a username")
    return user, password, host, port, dbname


def build_database_url(
    *,
    user: str,
    password: str,
    host: str,
    port: str,
    dbname: str,
) -> str:
    user_q = quote(user, safe="")
    password_q = quote(password, safe="")
    return f"postgresql://{user_q}:{password_q}@{host}:{port}/{dbname}"


def _connect(url: str, *, timeout_s: float = 5.0):
    try:
        import psycopg  # noqa: PLC0415
    except ImportError as exc:
        raise PostgresProvisionError(
            "psycopg is required to provision PostgreSQL. Run `poetry install` first.",
        ) from exc
    return psycopg.connect(url, connect_timeout=int(timeout_s))


def postgres_url_reachable(url: str, *, timeout_s: float = 2.0) -> bool:
    try:
        with _connect(url, timeout_s=timeout_s):
            return True
    except Exception:
        return False


def provision_nimbusware_role(conn, *, log: Callable[[str], object] | None = None) -> None:
    def _log(msg: str) -> None:
        if log:
            log(msg)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM pg_roles WHERE rolname = %s
            """,
            (NIMBUSWARE_DB_USER,),
        )
        if cur.fetchone():
            _log(f"Role {NIMBUSWARE_DB_USER!r} already exists; updating password.")
            cur.execute(
                f"ALTER ROLE {NIMBUSWARE_DB_USER} WITH LOGIN PASSWORD %s CREATEDB",
                (NIMBUSWARE_DB_PASSWORD,),
            )
        else:
            _log(f"Creating role {NIMBUSWARE_DB_USER!r}...")
            cur.execute(
                f"CREATE ROLE {NIMBUSWARE_DB_USER} WITH LOGIN PASSWORD %s CREATEDB",
                (NIMBUSWARE_DB_PASSWORD,),
            )
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (NIMBUSWARE_DB_NAME,),
        )
        if cur.fetchone():
            _log(f"Database {NIMBUSWARE_DB_NAME!r} already exists.")
        else:
            _log(f"Creating database {NIMBUSWARE_DB_NAME!r}...")
            cur.execute(f"CREATE DATABASE {NIMBUSWARE_DB_NAME} OWNER {NIMBUSWARE_DB_USER}")


def provision_from_admin_url(
    admin_url: str,
    *,
    log: Callable[[str], object] | None = None,
) -> str:
    """Create nimbusware role/database using admin credentials; return app URL."""
    _user, _password, host, port, _dbname = parse_database_url(admin_url)
    if log:
        log(f"Connecting to PostgreSQL admin endpoint at {host}:{port}...")
    try:
        with _connect(admin_url) as conn:
            conn.autocommit = True
            provision_nimbusware_role(conn, log=log)
    except PostgresProvisionError:
        raise
    except Exception as exc:
        raise PostgresProvisionError(
            f"Could not provision PostgreSQL using admin URL: {exc}",
        ) from exc
    app_url = default_app_database_url(host=host, port=port)
    if not postgres_url_reachable(app_url):
        raise PostgresProvisionError(
            "Provisioning finished but the application database URL is not reachable yet.",
        )
    return app_url


def resolve_admin_url(
    *,
    cli_admin_url: str | None,
    env: dict[str, str] | None = None,
) -> str | None:
    merged = os.environ if env is None else {**os.environ, **env}
    for candidate in (
        (cli_admin_url or "").strip(),
        merged.get(ENV_POSTGRES_ADMIN_URL, "").strip(),
    ):
        if candidate:
            return candidate
    return None
