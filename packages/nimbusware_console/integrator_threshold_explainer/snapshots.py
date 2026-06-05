from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.integrator_gate import (
    integrator_gate_workflow_enabled,
    load_integrator_gate_emit_enabled,
)
from nimbusware_config.workflow_read import (
    load_yaml,
)


def _thresholds_snapshot(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            raw = config_materializer.get_integrator_thresholds()
        except KeyError:
            return {
                "relpath": "configs/integrator/thresholds.yaml",
                "exists": False,
                "source": "materializer",
                "enabled": None,
                "min_score_to_pass": None,
                "top_level_version_int": None,
            }
        snap: dict[str, Any] = {
            "relpath": "configs/integrator/thresholds.yaml",
            "exists": True,
            "source": "materializer",
            "thresholds_yaml_file_bytes": None,
        }
        if not isinstance(raw, dict):
            snap["enabled"] = None
            snap["min_score_to_pass"] = None
            snap["top_level_version_int"] = None
            return snap
        snap["enabled"] = bool(raw.get("enabled", False))
        try:
            snap["min_score_to_pass"] = float(raw.get("min_score_to_pass", 0.0))
        except (TypeError, ValueError):
            snap["min_score_to_pass"] = None
        raw_v = raw.get("version")
        snap["top_level_version_int"] = (
            int(raw_v) if type(raw_v) is int and not isinstance(raw_v, bool) else None
        )
        return snap
    return _thresholds_disk_snapshot(repo_root)


def _thresholds_disk_snapshot(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs" / "integrator" / "thresholds.yaml"
    snap: dict[str, Any] = {
        "relpath": "configs/integrator/thresholds.yaml",
        "exists": path.is_file(),
        "thresholds_yaml_file_bytes": None,
    }
    if path.is_file():
        try:
            snap["thresholds_yaml_file_bytes"] = int(path.stat().st_size)
        except OSError:
            snap["thresholds_yaml_file_bytes"] = None
    if not path.is_file():
        snap["enabled"] = None
        snap["min_score_to_pass"] = None
        snap["top_level_version_int"] = None
        return snap
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        snap["enabled"] = None
        snap["min_score_to_pass"] = None
        snap["top_level_version_int"] = None
        return snap
    snap["enabled"] = bool(raw.get("enabled", False))
    try:
        snap["min_score_to_pass"] = float(raw.get("min_score_to_pass", 0.0))
    except (TypeError, ValueError):
        snap["min_score_to_pass"] = None
    raw_v = raw.get("version")
    snap["top_level_version_int"] = (
        int(raw_v) if type(raw_v) is int and not isinstance(raw_v, bool) else None
    )
    return snap


def _env_min_score_to_pass_breakdown() -> dict[str, Any]:
    raw = os.environ.get("NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS", "").strip()
    if not raw:
        return {
            "raw": "",
            "parses": False,
            "value": None,
            "invalid": False,
            "overrides_yaml": False,
        }
    try:
        v = max(0.0, min(1.0, float(raw)))
    except ValueError:
        return {
            "raw": raw,
            "parses": False,
            "value": None,
            "invalid": True,
            "overrides_yaml": False,
        }
    return {"raw": raw, "parses": True, "value": v, "invalid": False, "overrides_yaml": True}


def _emit_integrator_gate_breakdown(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    env_raw = os.environ.get("NIMBUSWARE_EMIT_INTEGRATOR_GATE", "")
    env = env_raw.strip().lower()
    forces_off = env in ("0", "false", "no")
    forces_on = env in ("1", "true", "yes")
    yaml_on = load_integrator_gate_emit_enabled(
        repo_root,
        config_materializer=config_materializer,
    )
    wf_on = integrator_gate_workflow_enabled(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    has_thr = False
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            config_materializer.get_integrator_thresholds()
            has_thr = True
        except KeyError:
            has_thr = False
    else:
        thr_path = repo_root / "configs" / "integrator" / "thresholds.yaml"
        has_thr = thr_path.is_file()
    if forces_off:
        would_emit = False
        reason = "NIMBUSWARE_EMIT_INTEGRATOR_GATE forces off (0/false/no)"
    elif not has_thr:
        would_emit = False
        reason = "configs/integrator/thresholds.yaml missing"
    elif forces_on or yaml_on or wf_on:
        would_emit = True
        reason = (
            "thresholds file present and at least one of: NIMBUSWARE_EMIT_INTEGRATOR_GATE "
            "force-on, thresholds.yaml enabled, workflow integrator_gate.enabled"
        )
    else:
        would_emit = False
        reason = (
            "no emission: env not force-on, thresholds.enabled false, "
            "workflow integrator_gate.enabled false"
        )
    return {
        "NIMBUSWARE_EMIT_INTEGRATOR_GATE": env_raw,
        "forces_off": forces_off,
        "forces_on": forces_on,
        "catalog_thresholds_yaml_enabled": yaml_on,
        "workflow_integrator_gate_enabled": wf_on,
        "thresholds_yaml_exists": has_thr,
        "would_emit_integrator_gate_event": would_emit,
        "not_emit_reason": None if would_emit else reason,
    }
