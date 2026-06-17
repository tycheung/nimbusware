"""Provider preset catalog and connection probes (v1.2 Track C2 / A1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import httpx
import yaml

ConnectionKind = Literal["api_key", "subscription"]


def load_provider_presets(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "model_providers.yaml"
    if not path.is_file():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return []
    providers = doc.get("providers")
    if not isinstance(providers, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in providers:
        if not isinstance(raw, dict):
            continue
        pid = str(raw.get("id") or "").strip()
        if not pid:
            continue
        out.append(
            {
                "id": pid,
                "kind": str(raw.get("kind") or "cloud"),
                "label": str(raw.get("label") or pid),
                "connection_kind": str(raw.get("connection_kind") or "api_key"),
                "default_base_url": raw.get("default_base_url"),
                "probe_health_path": str(raw.get("probe_health_path") or "/models"),
            },
        )
    return out


def preset_by_id(repo_root: Path, provider_id: str) -> dict[str, Any] | None:
    for row in load_provider_presets(repo_root):
        if row["id"] == provider_id:
            return row
    return None


def probe_api_key_connection(
    *,
    base_url: str,
    api_key: str,
    health_path: str = "/models",
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    root = base_url.strip().rstrip("/")
    path = health_path if health_path.startswith("/") else f"/{health_path}"
    url = f"{root}{path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = httpx.get(url, headers=headers, timeout=timeout_seconds)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return {"ok": False, "message": str(exc), "url": url}
    return {"ok": True, "message": "provider reachable", "url": url}


def probe_subscription_connection(*, subscription_connected: bool) -> dict[str, Any]:
    if subscription_connected:
        return {
            "ok": True,
            "message": "subscription marked connected on this machine",
        }
    return {
        "ok": False,
        "message": "subscription not connected — use desktop app or Connect flow",
    }


def probe_connection_row(
    repo_root: Path,
    *,
    provider_id: str,
    connection_kind: str,
    base_url: str | None,
    api_key: str | None,
    subscription_connected: bool,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    if connection_kind == "subscription":
        return probe_subscription_connection(subscription_connected=subscription_connected)

    preset = preset_by_id(repo_root, provider_id) or {}
    resolved_base = (base_url or preset.get("default_base_url") or "").strip()
    if not resolved_base:
        return {"ok": False, "message": "base_url required for custom provider"}
    if not api_key:
        return {"ok": False, "message": "API key not set"}
    health = str(preset.get("probe_health_path") or "/models")
    return probe_api_key_connection(
        base_url=resolved_base,
        api_key=api_key,
        health_path=health,
        timeout_seconds=timeout_seconds,
    )


def google_openai_base_url() -> str:
    return "https://generativelanguage.googleapis.com/v1beta/openai"
