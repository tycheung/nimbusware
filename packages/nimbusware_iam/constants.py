from __future__ import annotations

from uuid import UUID

# Shared default tenant for Individual edition and legacy rows.
DEFAULT_TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_TENANT_SLUG = "default"

API_KEY_HEADER = "X-Nimbusware-Api-Key"

# Enterprise feature flags (enabled when NIMBUSWARE_EDITION=enterprise).
ENTERPRISE_FEATURES: frozenset[str] = frozenset(
    {
        "iam",
        "fleet_memory",
        "config_notify",
        "object_store_primary",
        "redis_fleet_worker",
        "fleet_ollama_sli",
        "enterprise_console",
    },
)

# Alias for API routes that distinguish planned vs implemented (currently identical).
IMPLEMENTED_ENTERPRISE_FEATURES: frozenset[str] = ENTERPRISE_FEATURES
