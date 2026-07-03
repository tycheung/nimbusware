from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import yaml

from agent_core.mapping import mapping_or_empty
from env import find_repo_root
from iam.constants import DEFAULT_TENANT_SLUG

T = TypeVar("T")


def enterprise_policies_path(yaml_name: str, repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / yaml_name


def load_tenant_policies(
    yaml_name: str,
    parse_entry: Callable[[str, dict[str, Any]], T | None],
    *,
    repo_root: Path | None = None,
) -> dict[str, T]:
    path = enterprise_policies_path(yaml_name, repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, T] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        parsed = parse_entry(slug_s, entry)
        if parsed is not None:
            out[slug_s] = parsed
    return out


def save_tenant_policies(
    yaml_name: str,
    policies: dict[str, T],
    serialize_entry: Callable[[T], dict[str, Any]],
    *,
    repo_root: Path | None = None,
) -> None:
    path = enterprise_policies_path(yaml_name, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: serialize_entry(policy)
        for slug, policy in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_policy(
    tenant_slug: str | None,
    load_fn: Callable[..., dict[str, T]],
    default_factory: Callable[[str], T],
    *,
    repo_root: Path | None = None,
) -> T:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fn(repo_root=repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return default_factory(slug)
