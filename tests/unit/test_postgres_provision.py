from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INSTALL_DIR = ROOT / "scripts" / "install"
if str(INSTALL_DIR) not in sys.path:
    sys.path.insert(0, str(INSTALL_DIR))

from postgres_provision import (  # noqa: E402
    PostgresProvisionError,
    build_database_url,
    default_app_database_url,
    parse_database_url,
)


def test_default_app_database_url() -> None:
    url = default_app_database_url(host="db.example", port="5433")
    assert url.startswith("postgresql://")
    assert "@db.example:5433/nimbusware" in url


def test_parse_database_url_roundtrip() -> None:
    original = "postgresql://postgres:secret@dbhost:5432/postgres"
    user, password, host, port, dbname = parse_database_url(original)
    rebuilt = build_database_url(
        user=user,
        password=password,
        host=host,
        port=port,
        dbname=dbname,
    )
    assert rebuilt == original


def test_parse_database_url_rejects_non_postgres() -> None:
    with pytest.raises(PostgresProvisionError, match="postgresql"):
        parse_database_url("mysql://user:pass@localhost/db")
