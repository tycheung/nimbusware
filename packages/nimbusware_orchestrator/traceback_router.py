"""Map verifier logs / stack traces to Role Registry ``owner_role`` hints."""

from __future__ import annotations

import re
from uuid import UUID

from nimbusware_orchestrator.registry import RoleRegistry


def suggest_owner_role_from_verifier_log(log: str, registry: RoleRegistry) -> UUID | None:
    """Return a ``role_id`` when a known ``taxonomy_key`` appears as a whole word in ``log``."""
    lowered = log.lower()
    keys = sorted(registry.known_taxonomy_keys(), key=len, reverse=True)
    for key in keys:
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", lowered):
            return registry.resolve(key)
    return None
