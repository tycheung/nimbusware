from __future__ import annotations

from uuid import UUID

import psycopg

from nimbusware_orchestrator.registry import RoleRegistry


def load_registry_from_postgres(conninfo: str) -> RoleRegistry:
    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT taxonomy_key, role_id
                FROM nimbusware_roles_registry
                ORDER BY taxonomy_key
                """,
            )
            rows = cur.fetchall()
    if not rows:
        msg = (
            "nimbusware_roles_registry is empty; apply "
            "packages/nimbusware_store/schema/postgres.sql (bootstrap to an empty database)"
        )
        raise ValueError(msg)
    mapping: dict[str, UUID] = {}
    for key, rid in rows:
        mapping[str(key).strip().lower()] = UUID(str(rid))
    return RoleRegistry.from_mapping(
        mapping,
        yaml_version=0,
        content_digest_sha256_16="db:nimbusware_roles_registry",
    )
