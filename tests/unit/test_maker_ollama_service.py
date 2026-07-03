from __future__ import annotations

from unittest.mock import patch

from maker.services import ollama as svc


def test_maker_list_models_no_query() -> None:
    with patch("maker.services.ollama.get_json") as get_json:
        get_json.return_value = {"reachable": True}
        svc.list_models()
    get_json.assert_called_once_with("/platform/ollama/models")


def test_maker_set_primary_routing() -> None:
    with patch("maker.services.ollama.patch_response") as patch_resp:
        svc.set_primary_routing("llama3.1:8b")
    patch_resp.assert_called_once()
    assert patch_resp.call_args[0][1]["primary_model_id"] == "llama3.1:8b"
