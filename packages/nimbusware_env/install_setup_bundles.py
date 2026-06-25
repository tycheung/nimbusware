from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SETUP_BUNDLE_DEFAULT = "default"
SETUP_BUNDLE_ENTERPRISE = "enterprise"
SETUP_BUNDLE_CHOICES = (SETUP_BUNDLE_DEFAULT, SETUP_BUNDLE_ENTERPRISE)

_BUNDLES_DIR = Path(__file__).resolve().parents[2] / "configs" / "install" / "bundles"


def bundles_dir(repo_root: Path | None = None) -> Path:
    if repo_root is not None:
        candidate = repo_root / "configs" / "install" / "bundles"
        if candidate.is_dir():
            return candidate
    return _BUNDLES_DIR


def load_setup_bundle(bundle_id: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    if bundle_id not in SETUP_BUNDLE_CHOICES:
        raise ValueError(f"unknown setup bundle: {bundle_id}")
    root = bundles_dir(repo_root)
    env_path = root / f"{bundle_id}.env.yaml"
    if not env_path.is_file():
        raise FileNotFoundError(env_path)
    data = yaml.safe_load(env_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid bundle file: {env_path}")
    config_path = root / f"{bundle_id}.config.yaml"
    if config_path.is_file():
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(config_data, dict):
            data["config"] = config_data
    data.setdefault("bundle_id", bundle_id)
    return data


def bundle_env_vars(bundle: dict[str, Any]) -> dict[str, str]:
    raw = bundle.get("env")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def bundle_edition(bundle: dict[str, Any]) -> str:
    edition = str(bundle.get("edition") or "").strip().lower()
    if edition in ("individual", "enterprise"):
        return edition
    return (
        SETUP_BUNDLE_ENTERPRISE
        if bundle.get("bundle_id") == SETUP_BUNDLE_ENTERPRISE
        else SETUP_BUNDLE_DEFAULT
    )


def apply_setup_bundle_env(
    repo_root: Path,
    bundle_id: str,
    *,
    log: Any | None = None,
) -> dict[str, str]:
    from nimbusware_env import set_env_var

    bundle = load_setup_bundle(bundle_id, repo_root=repo_root)
    applied: dict[str, str] = {}
    for key, value in bundle_env_vars(bundle).items():
        path = set_env_var(key, value, repo_root=repo_root)
        applied[key] = value
        if log is not None:
            log(f"  Setup bundle {bundle_id}: {key}={value} ({path})")
    return applied


def seed_enterprise_fleet_enforcement(repo_root: Path, bundle: dict[str, Any]) -> None:
    config = bundle.get("config")
    if not isinstance(config, dict):
        return
    fleet = config.get("fleet_enforcement")
    if not isinstance(fleet, dict):
        return
    target = repo_root / "configs" / "enterprise" / "fleet_enforcement_policies.yaml"
    if not target.is_file():
        return
    existing = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(existing, dict):
        existing = {"version": 1, "tenants": {}}
    tenants = existing.setdefault("tenants", {})
    if not isinstance(tenants, dict):
        tenants = {}
        existing["tenants"] = tenants
    default_tenant = tenants.setdefault("default", {})
    if not isinstance(default_tenant, dict):
        default_tenant = {}
        tenants["default"] = default_tenant
    for tenant_id, policy in fleet.items():
        if not isinstance(policy, dict):
            continue
        entry = tenants.setdefault(str(tenant_id), {})
        if isinstance(entry, dict):
            entry.update(policy)
    target.write_text(yaml.safe_dump(existing, sort_keys=False), encoding="utf-8")
