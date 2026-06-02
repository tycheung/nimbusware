"""RoleRegistry loader failure-mode + contract parity."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.registry_db import load_registry_from_postgres


def _write_yaml(tmp_path: Path, content: str, *, name: str = "roles.yaml") -> Path:
    """Write a YAML file under tmp_path; allow per-axis unique filename."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _mock_psycopg_connect(rows: list[tuple[str, str]]) -> MagicMock:
    """Return a psycopg.connect mock wired with fetchall() -> rows.

    Mirrors the two-layer context-manager pattern in registry_db.py:
    ``with psycopg.connect(conninfo) as conn: with conn.cursor() as cur: ...``
    """
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=None)
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=None)
    connect = MagicMock(return_value=conn)
    return connect


def test_from_yaml_structural_error_matrix_5_axis(tmp_path: Path) -> None:
    """Pin the 2 ValueError paths at registry.py:29-36 across 5 malformed shapes.

    A1 -- empty file '' -> safe_load returns None -> root-not-dict raise.
    A2 -- top-level list -> root-not-dict raise.
    A3 -- top-level scalar -> root-not-dict raise.
    A4 -- dict missing 'roles' key -> roles-not-list raise (None arm).
    A5 -- dict with 'roles' as dict -> roles-not-list raise (wrong-type arm).
    """
    a1 = _write_yaml(tmp_path, "", name="a1.yaml")
    with pytest.raises(ValueError, match="root must be a mapping"):
        RoleRegistry.from_yaml(a1)

    a2 = _write_yaml(tmp_path, "- 1\n- 2\n", name="a2.yaml")
    with pytest.raises(ValueError, match="root must be a mapping"):
        RoleRegistry.from_yaml(a2)

    a3 = _write_yaml(tmp_path, "hello\n", name="a3.yaml")
    with pytest.raises(ValueError, match="root must be a mapping"):
        RoleRegistry.from_yaml(a3)

    a4 = _write_yaml(tmp_path, "version: 1\n", name="a4.yaml")
    with pytest.raises(ValueError, match=r"must contain a 'roles' list"):
        RoleRegistry.from_yaml(a4)

    a5 = _write_yaml(tmp_path, "roles:\n  a: b\n", name="a5.yaml")
    with pytest.raises(ValueError, match=r"must contain a 'roles' list"):
        RoleRegistry.from_yaml(a5)


def test_from_yaml_graceful_skip_happy_path_5_axis(tmp_path: Path) -> None:
    """Pin the non-raising graceful-skip paths at registry.py:37-44.

    Each axis verifies the loop CONTINUES after skip (does NOT early-return)
    by co-asserting a valid sibling entry survives in the resulting registry.

    B1 -- empty 'roles: []' -> empty registry, no error (asymmetric vs DB).
    B2 -- non-dict items skipped via 'if not isinstance(item, dict)' guard.
    B3 -- item missing taxonomy_key -> skipped via 'isinstance(key, str)' guard.
    B4 -- item missing role_id -> skipped via 'and rid' short-circuit.
    B5 -- non-string taxonomy_key (int) -> skipped via 'isinstance(key, str)'.
    """
    b1 = _write_yaml(tmp_path, "roles: []\n", name="b1.yaml")
    reg_b1 = RoleRegistry.from_yaml(b1)
    assert reg_b1.known_taxonomy_keys() == frozenset(), (
        "B1: empty roles list must yield empty registry with no error "
        "(asymmetric vs DB path which raises on empty rows)"
    )

    valid_uuid = str(uuid4())
    b2_content = (
        "roles:\n"
        "  - 'not a dict'\n"
        "  - 42\n"
        f"  - {{taxonomy_key: valid_b2, role_id: '{valid_uuid}'}}\n"
    )
    reg_b2 = RoleRegistry.from_yaml(_write_yaml(tmp_path, b2_content, name="b2.yaml"))
    assert reg_b2.known_taxonomy_keys() == frozenset({"valid_b2"}), (
        "B2: non-dict items must be skipped; only the valid dict entry survives"
    )

    b3_content = (
        "roles:\n"
        f"  - {{role_id: '{valid_uuid}'}}\n"
        f"  - {{taxonomy_key: valid_b3, role_id: '{valid_uuid}'}}\n"
    )
    reg_b3 = RoleRegistry.from_yaml(_write_yaml(tmp_path, b3_content, name="b3.yaml"))
    assert reg_b3.known_taxonomy_keys() == frozenset({"valid_b3"}), (
        "B3: item missing taxonomy_key skipped (key=None not isinstance str)"
    )

    b4_content = (
        "roles:\n"
        "  - {taxonomy_key: orphan_b4}\n"
        f"  - {{taxonomy_key: valid_b4, role_id: '{valid_uuid}'}}\n"
    )
    reg_b4 = RoleRegistry.from_yaml(_write_yaml(tmp_path, b4_content, name="b4.yaml"))
    assert reg_b4.known_taxonomy_keys() == frozenset({"valid_b4"}), (
        "B4: item missing role_id skipped via 'and rid' short-circuit"
    )

    b5_content = (
        "roles:\n"
        f"  - {{taxonomy_key: 42, role_id: '{valid_uuid}'}}\n"
        f"  - {{taxonomy_key: valid_b5, role_id: '{valid_uuid}'}}\n"
    )
    reg_b5 = RoleRegistry.from_yaml(_write_yaml(tmp_path, b5_content, name="b5.yaml"))
    assert reg_b5.known_taxonomy_keys() == frozenset({"valid_b5"}), (
        "B5: non-string taxonomy_key (int) skipped via isinstance(key, str) guard"
    )


def test_from_yaml_normalization_and_digest_contracts_5_axis(tmp_path: Path) -> None:
    """Pin the non-error contracts at registry.py:27-49.

    C1 -- taxonomy_key '  BackendWriter  ' normalized to 'backendwriter'.
    C2 -- version defaults to 0 when missing from yaml.
    C3 -- 'version: 7' propagates as int.
    C4 -- content_digest is sha256(file_bytes).hexdigest()[:16] exactly.
    C5 -- two distinct file contents -> two distinct digests.
    """
    valid_uuid = str(uuid4())
    c1_content = f"roles:\n  - {{taxonomy_key: '  BackendWriter  ', role_id: '{valid_uuid}'}}\n"
    reg_c1 = RoleRegistry.from_yaml(_write_yaml(tmp_path, c1_content, name="c1.yaml"))
    resolved_lower = reg_c1.resolve("backendwriter")
    resolved_messy = reg_c1.resolve("  BackendWriter  ")
    assert resolved_lower == UUID(valid_uuid), (
        "C1: taxonomy_key stored with strip().lower() so 'backendwriter' resolves"
    )
    assert resolved_messy == UUID(valid_uuid), (
        "C1: resolve() also applies strip+lower so original messy form resolves"
    )

    reg_c2 = RoleRegistry.from_yaml(_write_yaml(tmp_path, "roles: []\n", name="c2.yaml"))
    assert reg_c2.yaml_version == 0, (
        "C2: version defaults to 0 via int(raw.get('version', 0)) when missing"
    )

    reg_c3 = RoleRegistry.from_yaml(
        _write_yaml(tmp_path, "version: 7\nroles: []\n", name="c3.yaml"),
    )
    assert reg_c3.yaml_version == 7, "C3: version: 7 propagates from yaml"
    assert isinstance(reg_c3.yaml_version, int), (
        "C3: yaml_version must be int-typed via the int() cast"
    )

    c4_text = "version: 1\nroles: []\n"
    c4_path = _write_yaml(tmp_path, c4_text, name="c4.yaml")
    expected_digest = hashlib.sha256(c4_path.read_bytes()).hexdigest()[:16]
    reg_c4 = RoleRegistry.from_yaml(c4_path)
    assert reg_c4.content_digest_sha256_16 == expected_digest, (
        "C4: content_digest must be hashlib.sha256(file_bytes).hexdigest()[:16]"
    )

    reg_c5_a = RoleRegistry.from_yaml(
        _write_yaml(tmp_path, "version: 1\nroles: []\n", name="c5a.yaml"),
    )
    reg_c5_b = RoleRegistry.from_yaml(
        _write_yaml(tmp_path, "version: 2\nroles: []\n", name="c5b.yaml"),
    )
    assert reg_c5_a.content_digest_sha256_16 != reg_c5_b.content_digest_sha256_16, (
        "C5: distinct file contents must produce distinct digests "
        "(rules out coincidental collisions / constant-digest bug)"
    )


def test_load_registry_from_postgres_failure_and_happy_path_parity_5_axis() -> None:
    """Pin the empty-table ValueError + happy-path DB-sentinel contracts.

    D1 -- empty rows -> ValueError matching 'hermes_roles_registry is empty'.
    D2 -- same setup -> error message includes 'schema/postgres.sql' for actionability.
    D3 -- non-empty rows -> keys lower+stripped via str(key).strip().lower().
    D4 -- non-empty rows -> content_digest_sha256_16 == 'db:hermes_roles_registry' sentinel.
    D5 -- non-empty rows -> yaml_version == 0 (asymmetric vs from_yaml file-driven).
    """
    empty_connect = _mock_psycopg_connect([])
    with patch("hermes_orchestrator.registry_db.psycopg.connect", new=empty_connect):
        with pytest.raises(ValueError, match="hermes_roles_registry is empty") as exc_d1:
            load_registry_from_postgres("postgresql://fake")
    assert "schema/postgres.sql" in str(exc_d1.value), (
        "D2: error message must include bootstrap schema path for actionability"
    )

    uuid_a = str(uuid4())
    uuid_b = str(uuid4())
    rows = [("  BackendWriter  ", uuid_a), ("Planner", uuid_b)]
    happy_connect = _mock_psycopg_connect(rows)
    with patch("hermes_orchestrator.registry_db.psycopg.connect", new=happy_connect):
        reg_d = load_registry_from_postgres("postgresql://fake")

    assert reg_d.known_taxonomy_keys() == frozenset({"backendwriter", "planner"}), (
        "D3: DB rows must be normalized via str(key).strip().lower() before from_mapping"
    )
    assert reg_d.content_digest_sha256_16 == "db:hermes_roles_registry", (
        "D4: DB path must set content_digest_sha256_16 to the 'db:hermes_roles_registry' "
        "sentinel (distinct from from_yaml's sha256 hex)"
    )
    assert reg_d.yaml_version == 0, (
        "D5: DB path must hard-code yaml_version=0 in from_mapping call "
        "(asymmetric vs from_yaml which reads from file)"
    )
