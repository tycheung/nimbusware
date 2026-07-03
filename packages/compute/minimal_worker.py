from __future__ import annotations

from typing import Any


def probe_minimal_worker_capabilities() -> dict[str, Any]:
    """Lightweight hardware + mesh capability snapshot for node registration."""
    caps: dict[str, Any] = {"mesh_worker": True, "minimal_worker": True}
    try:
        from hw.probe import probe_hardware
        from hw.profile import profile_from_probe

        raw = probe_hardware()
        profile = profile_from_probe(raw)
        caps["hardware_tier"] = getattr(profile, "tier", None) or raw.get("tier")
        caps["context_tokens"] = getattr(profile, "context_tokens", None)
    except Exception:
        caps["hardware_tier"] = "unknown"
    try:
        import httpx

        from env.env_flags import nimbusware_ollama_base_url

        url = nimbusware_ollama_base_url().rstrip("/") + "/api/tags"
        resp = httpx.get(url, timeout=3.0)
        if resp.status_code == 200:
            body = resp.json()
            models = body.get("models") if isinstance(body, dict) else None
            if isinstance(models, list):
                caps["ollama_models"] = [
                    str(m.get("name")) for m in models if isinstance(m, dict) and m.get("name")
                ][:20]
    except Exception:
        pass
    return caps
