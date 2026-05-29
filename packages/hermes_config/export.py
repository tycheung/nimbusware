"""Export authoritative Postgres config rows to repo ``configs/`` (gitops review)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from hermes_config.keys import (
    KEY_CRITIQUE_PAIRINGS,
    KEY_CUSTOM_AGENTS_REGISTRY,
    KEY_ESCALATION,
    KEY_INTEGRATOR_THRESHOLDS,
    KEY_MODEL_ROUTING,
    KEY_PERSONA_SHELVES,
    KEY_ROLE_REGISTRY,
    KEY_SELF_REFINEMENT,
    NS_CUSTOM_AGENTS,
    NS_PERSONAS,
    NS_POLICY,
    NS_ROLES,
    NS_WORKFLOWS,
)
from hermes_config.protocol import ConfigStore
from hermes_orchestrator.merge import atomic_write_yaml

PathFn = Callable[[Path], Path]


_STATIC_EXPORTS: list[tuple[str, str, PathFn]] = [
    (NS_PERSONAS, KEY_PERSONA_SHELVES, lambda r: r / "configs" / "personas" / "shelves.yaml"),
    (
        NS_PERSONAS,
        KEY_CRITIQUE_PAIRINGS,
        lambda r: r / "configs" / "personas" / "critique_pairings.yaml",
    ),
    (NS_ROLES, KEY_ROLE_REGISTRY, lambda r: r / "configs" / "roles.yaml"),
    (NS_POLICY, KEY_MODEL_ROUTING, lambda r: r / "configs" / "model-routing.yaml"),
    (NS_POLICY, KEY_ESCALATION, lambda r: r / "configs" / "escalation" / "policy.yaml"),
    (
        NS_POLICY,
        KEY_INTEGRATOR_THRESHOLDS,
        lambda r: r / "configs" / "integrator" / "thresholds.yaml",
    ),
    (
        NS_POLICY,
        KEY_SELF_REFINEMENT,
        lambda r: r / "configs" / "self_refinement" / "policy.yaml",
    ),
    (
        NS_CUSTOM_AGENTS,
        KEY_CUSTOM_AGENTS_REGISTRY,
        lambda r: r / "configs" / "custom_agents" / "registry.yaml",
    ),
]


def export_config_to_repo(
    store: ConfigStore,
    repo_root: Path,
    *,
    namespaces: set[str] | None = None,
) -> dict[str, int]:
    """Write store documents to canonical YAML paths; return export counts per namespace."""
    repo = repo_root.resolve()
    counts: dict[str, int] = {}

    for ns, doc_key, path_fn in _STATIC_EXPORTS:
        if namespaces is not None and ns not in namespaces:
            continue
        row = store.get(ns, doc_key)
        if row is None:
            continue
        out_path = path_fn(repo)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_yaml(out_path, row.content)
        counts[ns] = counts.get(ns, 0) + 1

    if namespaces is None or NS_WORKFLOWS in namespaces:
        wf_dir = repo / "configs" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        for stem in store.list_keys(NS_WORKFLOWS):
            row = store.get(NS_WORKFLOWS, stem)
            if row is None:
                continue
            atomic_write_yaml(wf_dir / f"{stem}.yaml", row.content)
            counts[NS_WORKFLOWS] = counts.get(NS_WORKFLOWS, 0) + 1

    return counts


def list_store_documents(
    store: ConfigStore,
    *,
    namespaces: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Summarize documents for dry-run import (namespace, key, version, digest)."""
    out: list[dict[str, Any]] = []
    for ns, doc_key, _ in _STATIC_EXPORTS:
        if namespaces is not None and ns not in namespaces:
            continue
        row = store.get(ns, doc_key)
        if row is not None:
            out.append(
                {
                    "namespace": ns,
                    "document_key": doc_key,
                    "version": row.version,
                    "content_sha256_16": row.content_sha256_16,
                },
            )
    if namespaces is None or NS_WORKFLOWS in namespaces:
        for stem in store.list_keys(NS_WORKFLOWS):
            row = store.get(NS_WORKFLOWS, stem)
            if row is not None:
                out.append(
                    {
                        "namespace": NS_WORKFLOWS,
                        "document_key": stem,
                        "version": row.version,
                        "content_sha256_16": row.content_sha256_16,
                    },
                )
    return out
