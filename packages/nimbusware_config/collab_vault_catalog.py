from __future__ import annotations

from typing import Any

from nimbusware_config.provider_connections import ProviderConnectionStore, _row_to_public


def provider_catalog_for_user(
    store: ProviderConnectionStore,
    *,
    user_id: str,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    return [_row_to_public(r) for r in store.list_for_user(user_id=user_id, tenant_id=tenant_id)]
