from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from agent_core.models import (
    FindingFixStrictnessSettings,
    NetworkEgressPolicySnapshot,
    PolicySnapshotV1,
)
from agent_core.yaml_io import atomic_write_yaml, dump_yaml, load_yaml
from orchestrator.network_egress_normalize import normalize_domain_allowlist_entry


def _merge_finding_strictness(
    layers: list[dict[str, Any] | None],
) -> FindingFixStrictnessSettings:
    merged: dict[str, Any] = {}
    for layer in layers:
        if not layer:
            continue
        fs = layer.get("finding_fix_strictness")
        if isinstance(fs, dict):
            merged.update(fs)
    if not merged:
        merged = {
            "minimum_severity_requiring_fixes": "MEDIUM",
            "also_require_fixes_for_low_severity": False,
        }
    return FindingFixStrictnessSettings.model_validate(merged)


def _merge_uuid_allowlist(layers: list[dict[str, Any] | None], key: str) -> list[UUID]:
    acc: list[UUID] = []
    for layer in layers:
        if not layer:
            continue
        ne = layer.get("network_egress")
        if not isinstance(ne, dict):
            continue
        raw = ne.get(key)
        if raw is None:
            continue
        if raw == []:
            acc = []
            continue
        if isinstance(raw, list):
            for item in raw:
                acc.append(UUID(str(item)))
            seen: set[UUID] = set()
            deduped: list[UUID] = []
            for u in acc:
                if u not in seen:
                    seen.add(u)
                    deduped.append(u)
            acc = deduped
    return acc


def _merge_str_allowlist(layers: list[dict[str, Any] | None], key: str) -> list[str]:
    acc: list[str] = []
    for layer in layers:
        if not layer:
            continue
        ne = layer.get("network_egress")
        if not isinstance(ne, dict):
            continue
        raw = ne.get(key)
        if raw is None:
            continue
        if raw == []:
            acc = []
            continue
        if isinstance(raw, list):
            acc = [*acc, *[str(x) for x in raw]]
            seen: set[str] = set()
            deduped: list[str] = []
            for s in acc:
                if s not in seen:
                    seen.add(s)
                    deduped.append(s)
            acc = deduped
    return acc


def _merge_budget(layers: list[dict[str, Any] | None]) -> int | None:
    caps: list[int] = []
    for layer in layers:
        if not layer:
            continue
        ne = layer.get("network_egress")
        if not isinstance(ne, dict):
            continue
        b = ne.get("budget_bytes_per_run")
        if b is None:
            continue
        if isinstance(b, int) and b >= 0:
            caps.append(b)
    if not caps:
        return None
    return min(caps)


def merge_policy_snapshot(
    base_config: dict[str, Any] | None,
    workflow_profile: dict[str, Any] | None,
    run_overrides: dict[str, Any] | None,
) -> PolicySnapshotV1:
    layers_fs: list[dict[str, Any] | None] = [base_config, workflow_profile, run_overrides]
    strictness = _merge_finding_strictness(layers_fs)
    scraper = _merge_uuid_allowlist(layers_fs, "scraper_role_allowlist")
    raw_domains = _merge_str_allowlist(layers_fs, "domain_allowlist")
    domains = [normalize_domain_allowlist_entry(x) for x in raw_domains]
    budget = _merge_budget(layers_fs)
    network = NetworkEgressPolicySnapshot(
        scraper_role_allowlist=scraper,
        domain_allowlist=domains,
        budget_bytes_per_run=budget,
    )
    return PolicySnapshotV1(
        finding_fix_strictness=strictness,
        network_egress=network,
    )


def policy_snapshot_from_files(
    base_path: Path,
    workflow_path: Path,
    run_overrides: dict[str, Any] | None = None,
) -> PolicySnapshotV1:
    return merge_policy_snapshot(
        load_yaml(base_path),
        load_yaml(workflow_path),
        run_overrides,
    )


def policy_snapshot_from_materializer(
    materializer: Any,
    workflow_profile: str,
    run_overrides: dict[str, Any] | None = None,
) -> PolicySnapshotV1:
    base = materializer.get_model_routing_base()
    wf = materializer.get_workflow_profile_dict(workflow_profile)
    return merge_policy_snapshot(base, wf, run_overrides)


__all__ = [
    "atomic_write_yaml",
    "load_yaml",
    "merge_policy_snapshot",
    "policy_snapshot_from_files",
    "policy_snapshot_from_materializer",
]
