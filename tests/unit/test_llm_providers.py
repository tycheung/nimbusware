from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from orchestrator.llm.providers import (
    AnthropicProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    list_registered_providers,
    provider_for_preset,
)

REPO = Path(__file__).resolve().parents[2]


def test_list_registered_providers_includes_ollama() -> None:
    presets = list_registered_providers(REPO)
    assert any(p["id"] == "ollama" for p in presets)


def test_provider_for_preset_ollama() -> None:
    provider = provider_for_preset(REPO, provider_id="ollama")
    assert isinstance(provider, OllamaProvider)


def test_ollama_provider_probe_unreachable() -> None:
    provider = OllamaProvider(base_url="http://127.0.0.1:59999")
    result = provider.probe(timeout_seconds=0.5)
    assert result["ok"] is False


def test_openai_provider_probe_missing_key() -> None:
    provider = OpenAICompatibleProvider(
        provider_id="openai",
        base_url="https://api.openai.com/v1",
        api_key="",
    )
    assert provider.probe()["ok"] is False


def test_provider_for_preset_anthropic() -> None:
    provider = provider_for_preset(REPO, provider_id="anthropic", api_key="sk-ant-test")
    assert isinstance(provider, AnthropicProvider)


def test_anthropic_provider_probe_missing_key() -> None:
    provider = AnthropicProvider(
        base_url="https://api.anthropic.com",
        api_key="",
    )
    assert provider.probe()["ok"] is False


def test_anthropic_provider_chat_json_parses_response() -> None:
    provider = AnthropicProvider(
        base_url="https://api.anthropic.com",
        api_key="sk-ant-test",
    )
    fake = {
        "content": [{"type": "text", "text": '{"verdict": "PASS"}'}],
    }
    with patch("httpx.post") as post:
        post.return_value.json.return_value = fake
        post.return_value.raise_for_status = lambda: None
        out = provider.chat_json(
            model_id="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": "hi"}],
        )
    assert out["verdict"] == "PASS"


def test_openai_provider_chat_json_parses_response() -> None:
    provider = OpenAICompatibleProvider(
        provider_id="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
    )
    fake = {
        "choices": [{"message": {"content": '{"verdict": "PASS"}'}}],
    }
    with patch("httpx.post") as post:
        post.return_value.json.return_value = fake
        post.return_value.raise_for_status = lambda: None
        out = provider.chat_json(
            model_id="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}]
        )
    assert out["verdict"] == "PASS"
