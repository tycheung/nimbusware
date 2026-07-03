from __future__ import annotations

from uuid import UUID

from env.env_flags import env_str, nimbusware_database_url
from orchestrator.model_binding_resolver import ResolvedBinding


def resolve_binding_api_key(
    binding: ResolvedBinding,
    *,
    user_id: str,
    conninfo: str | None = None,
) -> str | None:
    cid = binding.connection_id
    if cid and str(cid).strip():
        url = conninfo or nimbusware_database_url()
        if url:
            try:
                from config.provider_connections import ProviderConnectionStore

                store = ProviderConnectionStore(url)
                secret = store.get_secret(UUID(str(cid)), user_id=user_id)
                if secret and secret.api_key:
                    return secret.api_key.strip() or None
            except (ValueError, KeyError, TypeError):
                pass
    ref = binding.api_key_ref
    if isinstance(ref, str) and ref.strip():
        val = env_str(ref.strip())
        return val.strip() or None
    return None
