from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from orchestrator.routing.credentials import resolve_binding_api_key
from orchestrator.routing.resolver import ResolvedBinding


def _binding(**kwargs: object) -> ResolvedBinding:
    base = {
        "agent_role": "planner",
        "provider_kind": "cloud",
        "provider_id": "openai_compatible",
        "model_id": "gpt-4o-mini",
        "base_url": None,
        "api_key_ref": None,
        "connection_id": None,
        "binding_source": "test",
        "params": {},
    }
    base.update(kwargs)
    return ResolvedBinding(**base)


def test_resolve_binding_api_key_from_env_ref() -> None:
    binding = _binding(api_key_ref="OPENAI_API_KEY")
    with patch(
        "orchestrator.routing.credentials.env_str",
        return_value="sk-test",
    ):
        assert resolve_binding_api_key(binding, user_id="u1") == "sk-test"


def test_resolve_binding_api_key_from_vault() -> None:
    cid = uuid4()
    binding = _binding(connection_id=str(cid))
    secret = MagicMock(api_key="vault-key")
    store = MagicMock()
    store.get_secret.return_value = secret
    with patch(
        "config.provider_connections.ProviderConnectionStore",
        return_value=store,
    ):
        with patch(
            "orchestrator.routing.credentials.nimbusware_database_url",
            return_value="postgresql://x",
        ):
            assert resolve_binding_api_key(binding, user_id="user-a") == "vault-key"
    store.get_secret.assert_called_once()
