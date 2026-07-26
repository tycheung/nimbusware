"""Minimal worker capability probe (`sak421-c` / `sak433-d` / `sak489-c` — broker-first under CAPACITY)."""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_capacity_enabled
from hw.capacity_route import refuse_legacy

_MSG = (
    "minimal_worker hardware probe unavailable under "
    "NIMBUSWARE_BROKER_CAPACITY=1|2; use SwissArmyNoife /v1/sak/capacity"
)


def probe_minimal_worker_capabilities() -> dict[str, Any]:
    """Lightweight hardware + mesh capability snapshot for node registration."""
    caps: dict[str, Any] = {"mesh_worker": True, "minimal_worker": True}
    try:
        if broker_capacity_enabled():
            from broker_client.capacity_bridge import try_broker_probe_dict
            from hw.profile import profile_from_probe

            hit = try_broker_probe_dict()
            if hit is not None:
                profile = profile_from_probe(hit)
                caps["hardware_tier"] = getattr(profile, "tier", None) or hit.get("tier")
                caps["context_tokens"] = getattr(profile, "context_tokens", None)
                caps["capacity_source"] = "broker"
            else:
                refuse_legacy(_MSG)
        else:
            from hw.probe import probe_hardware
            from hw.profile import profile_from_probe

            raw = probe_hardware()
            profile = profile_from_probe(raw)
            caps["hardware_tier"] = getattr(profile, "tier", None) or raw.get("tier")
            caps["context_tokens"] = getattr(profile, "context_tokens", None)
            caps["capacity_source"] = "local"
    except RuntimeError:
        raise
    except Exception as exc:
        # sak435-c: under CAPACITY peel, do not soft-degrade to unknown.
        if broker_capacity_enabled():
            raise RuntimeError(f"{_MSG}: {exc}") from exc
        caps["hardware_tier"] = "unknown"
        caps.setdefault("capacity_source", "unknown")
    try:
        import httpx

        from env.env_flags import nimbusware_ollama_base_url

        url = nimbusware_ollama_base_url().rstrip("/") + "/api/tags"
        resp = httpx.get(url, timeout=3.0)
        if resp.status_code == 200:
            body = resp.json()
            models = body.get("models") if isinstance(body, dict) else None
            if isinstance(models, list):
                caps["ollama_models"] = len(models)
        elif broker_capacity_enabled():
            # sak489-c: Ollama sidecar miss is not silent under CAPACITY peel.
            raise RuntimeError(f"{_MSG}: ollama sidecar status={resp.status_code}")
    except RuntimeError:
        raise
    except Exception as exc:
        if broker_capacity_enabled():
            raise RuntimeError(f"{_MSG}: ollama sidecar unreachable") from exc
    return caps
