from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.llm.providers.anthropic_provider import AnthropicProvider
from nimbusware_orchestrator.llm.providers.ollama_provider import OllamaProvider
from nimbusware_orchestrator.llm.providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
)
from nimbusware_orchestrator.llm.providers.protocol import LlmProvider
from nimbusware_orchestrator.provider_registry import load_provider_presets, preset_by_id

__all__ = [
    "AnthropicProvider",
    "LlmProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "provider_for_preset",
]


def provider_for_preset(
    repo_root: Path,
    *,
    provider_id: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LlmProvider:
    preset = preset_by_id(repo_root, provider_id) or {}
    kind = str(preset.get("kind") or "cloud")
    if kind == "local" or provider_id == "ollama":
        return OllamaProvider(base_url=base_url or preset.get("default_base_url"))
    if provider_id == "anthropic":
        resolved = base_url or str(preset.get("default_base_url") or "https://api.anthropic.com")
        return AnthropicProvider(
            provider_id=provider_id,
            base_url=resolved,
            api_key=api_key or "",
        )
    return OpenAICompatibleProvider(
        provider_id=provider_id,
        base_url=base_url or str(preset.get("default_base_url") or ""),
        api_key=api_key or "",
    )


def list_registered_providers(repo_root: Path) -> list[dict[str, Any]]:
    return load_provider_presets(repo_root)
