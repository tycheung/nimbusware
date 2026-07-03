from __future__ import annotations

from unittest.mock import MagicMock, patch

from config.collab_vault_catalog import provider_catalog_for_user


def test_provider_catalog_for_user_maps_public_rows() -> None:
    store = MagicMock()
    row = MagicMock()
    store.list_for_user.return_value = [row]
    with patch(
        "config.collab_vault_catalog._row_to_public",
        return_value={"provider_id": "openai", "model_id": "gpt-4o-mini"},
    ):
        out = provider_catalog_for_user(store, user_id="u1", tenant_id="t1")
    store.list_for_user.assert_called_once_with(user_id="u1", tenant_id="t1")
    assert out == [{"provider_id": "openai", "model_id": "gpt-4o-mini"}]
