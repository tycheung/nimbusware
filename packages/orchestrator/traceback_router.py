from __future__ import annotations

import re
from uuid import UUID

from orchestrator.registry import RoleRegistry


def suggest_owner_role_from_verifier_log(log: str, registry: RoleRegistry) -> UUID | None:
    lowered = log.lower()
    keys = sorted(registry.known_taxonomy_keys(), key=len, reverse=True)
    for key in keys:
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", lowered):
            return registry.resolve(key)
    return None
