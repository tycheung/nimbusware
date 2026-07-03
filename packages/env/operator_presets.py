from __future__ import annotations

import os

OPERATOR_PRESETS: dict[str, dict[str, str]] = {
    "offline": {
        "NIMBUSWARE_QUICK_MODE": "1",
        "NIMBUSWARE_SKIP_PREFLIGHT": "1",
        "NIMBUSWARE_USE_LLM": "0",
        "NIMBUSWARE_CONFIG_FROM_FILES": "1",
        "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE": "quick_local",
    },
    "local-llm": {
        "NIMBUSWARE_USE_LLM": "1",
        "NIMBUSWARE_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "NIMBUSWARE_SKIP_PREFLIGHT": "0",
        "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE": "micro_slice",
    },
    "production": {
        "NIMBUSWARE_USE_LLM": "1",
        "NIMBUSWARE_CONFIG_FROM_DB": "1",
        "NIMBUSWARE_SKIP_PREFLIGHT": "0",
        "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE": "nimbusware_production",
    },
}


def apply_operator_preset(name: str) -> list[str]:
    """Apply a named operator preset to ``os.environ``; return trace of keys set."""
    key = name.strip()
    preset = OPERATOR_PRESETS.get(key)
    if preset is None:
        known = ", ".join(sorted(OPERATOR_PRESETS))
        msg = f"unknown operator preset: {name!r} (known: {known})"
        raise KeyError(msg)
    trace: list[str] = []
    for env_key, value in preset.items():
        os.environ[env_key] = value
        trace.append(f"{env_key}={value}")
    return trace
