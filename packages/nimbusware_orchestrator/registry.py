"""Role Registry: taxonomy_key -> RoleId ."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import yaml


class RoleRegistry:
    def __init__(
        self,
        roles_by_taxonomy: dict[str, UUID],
        *,
        yaml_version: int = 0,
        content_digest_sha256_16: str | None = None,
    ) -> None:
        self._by_taxonomy = roles_by_taxonomy
        self.yaml_version = yaml_version
        self.content_digest_sha256_16 = content_digest_sha256_16

    @classmethod
    def from_yaml(cls, path: Path) -> RoleRegistry:
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()[:16]
        raw = yaml.safe_load(content.decode("utf-8"))
        if not isinstance(raw, dict):
            msg = "roles.yaml root must be a mapping"
            raise ValueError(msg)
        yaml_version = int(raw.get("version", 0))
        entries = raw.get("roles")
        if not isinstance(entries, list):
            msg = "roles.yaml must contain a 'roles' list"
            raise ValueError(msg)
        mapping: dict[str, UUID] = {}
        for item in entries:
            if not isinstance(item, dict):
                continue
            key = item.get("taxonomy_key")
            rid = item.get("role_id")
            if isinstance(key, str) and rid:
                mapping[key.strip().lower()] = UUID(str(rid))
        return cls(
            mapping,
            yaml_version=yaml_version,
            content_digest_sha256_16=digest,
        )

    @classmethod
    def from_mapping(
        cls,
        roles_by_taxonomy: dict[str, UUID],
        *,
        yaml_version: int = 0,
        content_digest_sha256_16: str | None = None,
    ) -> RoleRegistry:
        """Build from preloaded rows (e.g. future DB adapter). Keys are normalized lowercase."""
        low = {k.strip().lower(): v for k, v in roles_by_taxonomy.items()}
        return cls(
            low,
            yaml_version=yaml_version,
            content_digest_sha256_16=content_digest_sha256_16,
        )

    def resolve(self, taxonomy_key: str) -> UUID:
        k = taxonomy_key.strip().lower()
        if k not in self._by_taxonomy:
            msg = f"Unknown role taxonomy_key: {taxonomy_key!r}"
            raise KeyError(msg)
        return self._by_taxonomy[k]

    def known_taxonomy_keys(self) -> frozenset[str]:
        return frozenset(self._by_taxonomy.keys())

    def taxonomy_key_for(self, role_id: UUID) -> str | None:
        """Reverse lookup: Role Registry UUID → taxonomy key."""
        for key, rid in self._by_taxonomy.items():
            if rid == role_id:
                return key
        return None
