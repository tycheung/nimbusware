"""Critique pairings for run lifecycle (plan §14 #16)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.registry import RoleRegistry

CRITIQUE_STAGE_TO_PRODUCER: dict[str, str] = {
    "planner.critique": "planner",
    "implementation.critique": "backend_writer",
    "test_writer.critique": "test_writer",
    "frontend_writer.critique": "frontend_writer",
    "module_integrator.critique": "module_integrator",
    "agent_evaluator.critique": "agent_evaluator",
    "self_refinement.critique": "planner",
}

# Keep lifecycle producer accounting stable for coverage/snapshot contracts.
_EXCLUDED_PRODUCER_KEYS: frozenset[str] = frozenset({"agent_evaluator"})


def default_critique_pairings_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "personas" / "critique_pairings.yaml"


def load_critique_router(
    repo_root: Path,
    config_materializer: Any | None = None,
) -> UniversalCritiqueRouter:
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        return UniversalCritiqueRouter.from_content(
            config_materializer.get_critique_pairings(),
        )
    return UniversalCritiqueRouter.from_yaml(default_critique_pairings_path(repo_root))


def registry_producer_taxonomy_keys(registry: RoleRegistry) -> frozenset[str]:
    return frozenset(
        k
        for k in registry.known_taxonomy_keys()
        if not k.endswith("_critic") and k not in _EXCLUDED_PRODUCER_KEYS
    )


def taxonomy_keys_for_run_lifecycle(
    registry: RoleRegistry,
    router: UniversalCritiqueRouter,
) -> list[str]:
    """Registry producers plus each producer's paired critics (sorted, unique)."""
    keys: set[str] = set()
    producers = registry_producer_taxonomy_keys(registry)
    keys.update(producers)
    for prod in producers:
        keys.update(router.pairing_for(prod))
    return sorted(keys)


def critique_coverage_snapshot(
    registry: RoleRegistry,
    router: UniversalCritiqueRouter,
) -> dict[str, Any]:
    """Freeze pairing coverage for auditability on ``run.created`` metadata."""
    producers = sorted(registry_producer_taxonomy_keys(registry))
    paired: list[str] = []
    unpaired: list[str] = []
    errors: list[dict[str, str]] = []
    known = router.known_producer_keys()
    for prod in producers:
        if prod not in known:
            unpaired.append(prod)
            continue
        critics = [str(c).strip() for c in router.pairing_for(prod) if str(c).strip()]
        if critics:
            paired.append(prod)
        else:
            unpaired.append(prod)
        for critic in critics:
            try:
                registry.resolve(critic)
            except KeyError:
                errors.append({"producer": prod, "critic": critic})
    return {
        "registry_producers": producers,
        "paired_producers": paired,
        "unpaired_producers": unpaired,
        "pairing_errors": errors,
    }


def assert_critique_coverage_complete(snapshot: dict[str, Any]) -> None:
    """Raise ``ValueError`` when registry producers lack pairings (plan §3B.5)."""
    unpaired = snapshot.get("unpaired_producers")
    if isinstance(unpaired, list) and unpaired:
        msg = (
            "critique pairings incomplete: unpaired registry producers "
            f"{sorted(str(p) for p in unpaired)}"
        )
        raise ValueError(msg)
    errors = snapshot.get("pairing_errors")
    if isinstance(errors, list) and errors:
        msg = (
            "critique pairings invalid: "
            + "; ".join(
                f"{e.get('producer')!r}->{e.get('critic')!r}"
                for e in errors
                if isinstance(e, dict)
            )
        )
        raise ValueError(msg)
