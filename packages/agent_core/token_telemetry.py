from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class TokenTelemetrySample:
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    compaction_saved: int = 0
    offload_saved: int = 0
    provider: str = "ollama"
    stage_name: str = ""


_lock = Lock()
_samples: list[TokenTelemetrySample] = []


def record_token_sample(sample: TokenTelemetrySample) -> None:
    with _lock:
        _samples.append(sample)
        if len(_samples) > 500:
            del _samples[: len(_samples) - 500]


def recent_token_samples(limit: int = 50) -> list[TokenTelemetrySample]:
    with _lock:
        return list(_samples[-limit:])


def token_savings_summary() -> dict[str, int]:
    with _lock:
        rows = list(_samples)
    return {
        "tokens_in": sum(r.tokens_in for r in rows),
        "tokens_out": sum(r.tokens_out for r in rows),
        "cache_read": sum(r.cache_read for r in rows),
        "cache_write": sum(r.cache_write for r in rows),
        "compaction_saved": sum(r.compaction_saved for r in rows),
        "offload_saved": sum(r.offload_saved for r in rows),
    }


def usage_from_provider_response(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage")
    if isinstance(usage, dict):
        return {
            "tokens_in": int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
            "tokens_out": int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
            "cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_write": int(usage.get("cache_creation_input_tokens") or 0),
        }
    from orchestrator.routing.chat import extract_ollama_usage

    ollama = extract_ollama_usage(response)
    return {
        "tokens_in": int(ollama.get("prompt_tokens") or 0),
        "tokens_out": int(ollama.get("completion_tokens") or 0),
        "cache_read": 0,
        "cache_write": 0,
    }
