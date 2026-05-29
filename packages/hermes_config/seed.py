"""Bootstrap Postgres config from repo ``configs/`` (gitops / tests)."""



from __future__ import annotations

from pathlib import Path

from hermes_config.keys import (
    KEY_BUNDLE_CATALOG,
    KEY_CRITIQUE_PAIRINGS,
    KEY_ESCALATION,
    KEY_INTEGRATOR_THRESHOLDS,
    KEY_MODEL_ROUTING,
    KEY_PERSONA_SHELVES,
    KEY_ROLE_REGISTRY,
    KEY_SELF_REFINEMENT,
    NS_PERSONAS,
    NS_POLICY,
    NS_ROLES,
    NS_WORKFLOWS,
)
from hermes_config.protocol import ConfigStore
from hermes_orchestrator.merge import load_yaml


def seed_t2_policy_documents_from_repo(repo_root: Path, store: ConfigStore) -> dict[str, int]:

    """Load T2 policy YAML into ``hermes_config_document``."""

    repo = repo_root.resolve()

    counts: dict[str, int] = {}



    t2_paths: list[tuple[str, str, Path]] = [

        (NS_POLICY, KEY_ESCALATION, repo / "configs" / "escalation" / "policy.yaml"),

        (NS_POLICY, KEY_INTEGRATOR_THRESHOLDS, repo / "configs" / "integrator" / "thresholds.yaml"),

        (NS_POLICY, KEY_SELF_REFINEMENT, repo / "configs" / "self_refinement" / "policy.yaml"),
        (NS_POLICY, KEY_BUNDLE_CATALOG, repo / "configs" / "bundles" / "catalog.yaml"),

        (
            NS_PERSONAS,
            KEY_CRITIQUE_PAIRINGS,
            repo / "configs" / "personas" / "critique_pairings.yaml",
        ),

    ]

    for ns, key, path in t2_paths:

        if path.is_file():

            store.upsert(ns, key, load_yaml(path))

            counts[ns] = counts.get(ns, 0) + 1

    return counts





def seed_config_from_repo(repo_root: Path, store: ConfigStore) -> dict[str, int]:

    """Load YAML files into ``hermes_config_document``; return upserted counts per namespace."""

    repo = repo_root.resolve()

    counts: dict[str, int] = {}



    personas_path = repo / "configs" / "personas" / "shelves.yaml"

    if personas_path.is_file():

        store.upsert(NS_PERSONAS, KEY_PERSONA_SHELVES, load_yaml(personas_path))

        counts[NS_PERSONAS] = counts.get(NS_PERSONAS, 0) + 1



    roles_path = repo / "configs" / "roles.yaml"

    if roles_path.is_file():

        store.upsert(NS_ROLES, KEY_ROLE_REGISTRY, load_yaml(roles_path))

        counts[NS_ROLES] = counts.get(NS_ROLES, 0) + 1



    base = repo / "configs" / "model-routing.yaml"
    if base.is_file():
        store.upsert(NS_POLICY, KEY_MODEL_ROUTING, load_yaml(base))

        counts[NS_POLICY] = counts.get(NS_POLICY, 0) + 1



    wf_dir = repo / "configs" / "workflows"

    wf_n = 0

    if wf_dir.is_dir():

        seen: set[str] = set()

        for path in sorted(wf_dir.glob("*.yaml")) + sorted(wf_dir.glob("*.yml")):

            stem = path.stem

            if stem in seen:

                continue

            seen.add(stem)

            store.upsert(NS_WORKFLOWS, stem, load_yaml(path))

            wf_n += 1

    if wf_n:

        counts[NS_WORKFLOWS] = wf_n



    t2 = seed_t2_policy_documents_from_repo(repo, store)

    for ns, n in t2.items():

        counts[ns] = counts.get(ns, 0) + n



    return counts





def preview_seed_from_repo(
    repo_root: Path,
    *,
    namespaces: set[str] | None = None,
) -> list[dict[str, str]]:
    """List repo YAML paths that ``seed_config_from_repo`` would load (no store writes)."""
    repo = repo_root.resolve()
    out: list[dict[str, str]] = []

    def _add(ns: str, key: str, path: Path) -> None:
        if namespaces is not None and ns not in namespaces:
            return
        if path.is_file():
            out.append({"namespace": ns, "document_key": key, "path": str(path)})

    _add(NS_PERSONAS, KEY_PERSONA_SHELVES, repo / "configs" / "personas" / "shelves.yaml")
    _add(NS_ROLES, KEY_ROLE_REGISTRY, repo / "configs" / "roles.yaml")
    _add(NS_POLICY, KEY_MODEL_ROUTING, repo / "configs" / "model-routing.yaml")
    _add(NS_POLICY, KEY_ESCALATION, repo / "configs" / "escalation" / "policy.yaml")
    _add(NS_POLICY, KEY_INTEGRATOR_THRESHOLDS, repo / "configs" / "integrator" / "thresholds.yaml")
    _add(NS_POLICY, KEY_SELF_REFINEMENT, repo / "configs" / "self_refinement" / "policy.yaml")
    _add(NS_POLICY, KEY_BUNDLE_CATALOG, repo / "configs" / "bundles" / "catalog.yaml")
    _add(
        NS_PERSONAS,
        KEY_CRITIQUE_PAIRINGS,
        repo / "configs" / "personas" / "critique_pairings.yaml",
    )
    if namespaces is None or NS_WORKFLOWS in namespaces:
        wf_dir = repo / "configs" / "workflows"
        if wf_dir.is_dir():
            seen: set[str] = set()
            for path in sorted(wf_dir.glob("*.yaml")) + sorted(wf_dir.glob("*.yml")):
                if path.stem in seen:
                    continue
                seen.add(path.stem)
                out.append(
                    {
                        "namespace": NS_WORKFLOWS,
                        "document_key": path.stem,
                        "path": str(path),
                    },
                )
    return out


def seed_policy_documents_from_repo(

    repo_root: Path,

    store: ConfigStore,

    *,

    extra: dict[tuple[str, str], Path] | None = None,

) -> dict[str, int]:

    """Seed T1 + T2 documents (``extra`` reserved for follow-on paths)."""

    _ = extra

    return seed_config_from_repo(repo_root, store)


