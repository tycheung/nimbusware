from __future__ import annotations

from unittest.mock import patch

from console.services import ollama as svc


def test_list_models_builds_query() -> None:
    with patch("console.services.ollama.get_json") as get_json:
        get_json.return_value = {"models": []}
        svc.list_models(query="llama")
    get_json.assert_called_once_with("/platform/ollama/models?q=llama")


def test_admin_pull_posts_model() -> None:
    with patch("console.services.ollama.post_json") as post_json:
        post_json.return_value = {"model": "x", "status": "pulled"}
        out = svc.admin_pull_model("llama3.1:8b")
    assert out["status"] == "pulled"
    post_json.assert_called_once()
    assert post_json.call_args[0][1] == {"model": "llama3.1:8b"}
