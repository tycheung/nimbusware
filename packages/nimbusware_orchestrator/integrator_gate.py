"""Integrator gate: YAML ``enabled``, bundle id from catalog map, optional ``project_tags``.

Catalog bundle tags feed tag-recall scoring in ``ModuleIntegrator`` when the pipeline
passes ``bundle_tags`` in the project profile (see ``load_bundle_tags_for_bundle_id``).

Optional ``integrator_gate.min_score_to_pass`` overrides
``configs/integrator/thresholds.yaml`` when present; non-empty
``NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS`` overrides both (float, clamped ``0..1``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_extensions.bundle_memory import blend_bundle_rank_score
from nimbusware_extensions.catalog import load_bundle_catalog_content
from nimbusware_extensions.phase2 import ModuleIntegrator
from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict
from nimbusware_env.env_flags import env_str


def load_integrator_gate_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    """Return workflow ``integrator_gate`` mapping, or ``None`` if missing/unusable."""
    return _integrator_gate_workflow_dict(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )


def _integrator_gate_workflow_dict(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    """Return workflow ``integrator_gate`` mapping, or ``None`` if missing/unusable."""
    if workflow_profile is None or not str(workflow_profile).strip():
        return None
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return None
    block = raw.get("integrator_gate")
    return block if isinstance(block, dict) else None


def integrator_gate_workflow_enabled(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """True when workflow YAML ``integrator_gate.enabled`` is truthy.

    Missing file or invalid profile returns ``False`` (caller falls back to env + catalog YAML).
    """
    block = _integrator_gate_workflow_dict(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if not block:
        return False
    return bool(block.get("enabled", False))


def load_integrator_gate_emit_enabled(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """Read ``enabled`` from integrator thresholds (default False)."""
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            raw = config_materializer.get_integrator_thresholds()
        except KeyError:
            return False
    else:
        path = repo_root / "configs" / "integrator" / "thresholds.yaml"
        if not path.is_file():
            return False
        raw = load_yaml(path)
    return bool(raw.get("enabled", False))


def select_bundle_id_for_workflow(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> str:
    """Resolve bundle id: ``workflow_bundle_map`` in catalog, else first bundle, else default."""
    raw = load_bundle_catalog_content(repo_root, config_materializer=config_materializer)
    if raw is None:
        return "auth-rbac-starter"
    wmap = raw.get("workflow_bundle_map")
    if isinstance(wmap, dict) and workflow_profile:
        key = workflow_profile.strip()
        if key in wmap and wmap[key] is not None:
            return str(wmap[key])
    bundles = raw.get("bundles") if isinstance(raw.get("bundles"), list) else []
    if bundles and isinstance(bundles[0], dict) and bundles[0].get("id"):
        return str(bundles[0]["id"])
    return "auth-rbac-starter"


def workflow_profile_from_run_created_rows(rows: list[dict[str, Any]]) -> str | None:
    """First ``run.created`` payload ``workflow_profile`` from store rows."""
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        pl = row.get("payload") or {}
        wf = pl.get("workflow_profile")
        return str(wf) if wf is not None else None
    return None


def _bundle_entry_for_id(
    repo_root: Path,
    bundle_id: str,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    raw = load_bundle_catalog_content(repo_root, config_materializer=config_materializer)
    if raw is None:
        return None
    bundles_raw = raw.get("bundles")
    bundles: list[Any] = bundles_raw if isinstance(bundles_raw, list) else []
    bid = str(bundle_id).strip()
    for b in bundles:
        if isinstance(b, dict) and str(b.get("id", "")).strip() == bid:
            return b
    return None


def load_bundle_tags_for_bundle_id(
    repo_root: Path,
    bundle_id: str,
    *,
    config_materializer: Any | None = None,
) -> list[str]:
    """Return ``tags`` from ``configs/bundles/catalog.yaml`` for ``bundle_id``, or []."""
    b = _bundle_entry_for_id(repo_root, bundle_id, config_materializer=config_materializer)
    if b is None:
        return []
    tags = b.get("tags")
    if not isinstance(tags, list):
        return []
    return [str(t).strip() for t in tags if str(t).strip()]


def load_bundle_title_for_bundle_id(
    repo_root: Path,
    bundle_id: str,
    *,
    config_materializer: Any | None = None,
) -> str:
    """Return bundle ``title`` from catalog for ``bundle_id``, or empty string."""
    b = _bundle_entry_for_id(repo_root, bundle_id, config_materializer=config_materializer)
    if b is None:
        return ""
    t = b.get("title")
    return str(t).strip() if t is not None else ""


def load_integrator_min_score_from_thresholds(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> float:
    """``min_score_to_pass`` from integrator thresholds (default ``0.0``)."""
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            raw = config_materializer.get_integrator_thresholds()
        except KeyError:
            return 0.0
    else:
        path = repo_root / "configs" / "integrator" / "thresholds.yaml"
        if not path.is_file():
            return 0.0
        raw = load_yaml(path)
    try:
        return float(raw.get("min_score_to_pass", 0.0))
    except (TypeError, ValueError):
        return 0.0


def parse_integrator_gate_min_score_to_pass(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> float | None:
    """Workflow ``integrator_gate.min_score_to_pass`` when set and valid, else ``None``."""
    block = _integrator_gate_workflow_dict(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if block is None:
        return None
    raw = block.get("min_score_to_pass")
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, v))


def effective_integrator_min_score_to_pass(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> float:
    """Resolve min score: env (non-empty) beats workflow, then ``thresholds.yaml``."""
    env_raw = env_str("NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS")
    if env_raw:
        try:
            return max(0.0, min(1.0, float(env_raw)))
        except ValueError:
            pass
    wf = parse_integrator_gate_min_score_to_pass(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if wf is not None:
        return wf
    return load_integrator_min_score_from_thresholds(
        repo_root,
        config_materializer=config_materializer,
    )


def parse_integrator_gate_project_tags(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> list[str] | None:
    """Explicit ``integrator_gate.project_tags`` from workflow YAML, or ``None``.

    ``None`` means callers should align project tags with the selected bundle’s catalog
    tags (neutral pass when the bundle lists tags). Malformed ``project_tags`` values
    degrade to ``None``.
    """
    block = _integrator_gate_workflow_dict(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if block is None:
        return None
    pt = block.get("project_tags")
    if pt is None:
        return None
    if not isinstance(pt, list):
        return None
    out = [str(t).strip() for t in pt if str(t).strip()]
    return out or None


def rank_bundle_compatibility_candidates(
    repo_root: Path,
    project_tags: list[str],
    *,
    integrator: ModuleIntegrator,
    config_materializer: Any | None = None,
    limit: int = 10,
    bundle_outcome_store: Any | None = None,
) -> list[dict[str, Any]]:
    """Score every catalog bundle against ``project_tags`` (descending, capped).

    Each row: ``bundle_id``, ``score``, ``passes_gate``, optional ``title``.
    Per-candidate ``bundle_tags`` come from the catalog entry (tag-recall scoring).
    """
    raw = load_bundle_catalog_content(repo_root, config_materializer=config_materializer)
    if raw is None:
        return []
    bundles_raw = raw.get("bundles")
    bundles: list[Any] = bundles_raw if isinstance(bundles_raw, list) else []
    cap = max(1, int(limit))
    rows: list[dict[str, Any]] = []
    ptags = [str(t).strip() for t in project_tags if str(t).strip()]
    for b in bundles:
        if not isinstance(b, dict):
            continue
        bid_raw = b.get("id")
        if bid_raw is None:
            continue
        bid = str(bid_raw).strip()
        if not bid:
            continue
        tags_raw = b.get("tags")
        bundle_tags = (
            [str(t).strip() for t in tags_raw if str(t).strip()]
            if isinstance(tags_raw, list)
            else []
        )
        if bundle_tags:
            profile: dict[str, Any] = {"tags": ptags, "bundle_tags": bundle_tags}
        else:
            profile = {"tags": ptags}
        score = integrator.score_fit(bid, profile)
        row: dict[str, Any] = {
            "bundle_id": bid,
            "score": score,
            "passes_gate": integrator.passes_gate(bid, profile),
        }
        title_raw = b.get("title")
        if title_raw is not None:
            title = str(title_raw).strip()
            if title:
                row["title"] = title
        rows.append(row)
    stats = bundle_outcome_store.success_stats() if bundle_outcome_store is not None else {}
    if stats:
        for row in rows:
            base = float(row.get("score", 0.0))
            row["score"] = blend_bundle_rank_score(
                base,
                bundle_id=str(row.get("bundle_id", "")),
                stats=stats,
            )
    rows.sort(key=lambda r: (-float(r.get("score", 0.0)), str(r.get("bundle_id", ""))))
    return rows[:cap]
