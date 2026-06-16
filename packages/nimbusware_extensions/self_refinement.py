from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.yaml_io import load_yaml
from nimbusware_extensions.personas import PersonaShelf


@dataclass(frozen=True)
class SelfRefinementPolicy:
    version: int
    enabled: bool
    description: str
    max_iterations: int = 3
    auto_promote_probation: bool = False
    llm_critique_enabled: bool = False


class SelfRefinementEvaluator:
    def evaluate(
        self,
        *,
        persona_assignment: dict[str, Any] | None,
        shelf: PersonaShelf | None,
    ) -> dict[str, Any]:
        gaps: list[str] = []
        coverage: dict[str, Any] = {}

        if shelf is None:
            return {
                "status": "invalid",
                "gaps": ["shelf_unavailable"],
                "coverage": {},
                "promotion_ready": False,
            }

        def _slot_id(raw: object) -> str | None:
            if isinstance(raw, str):
                rid = raw.strip()
                return rid or None
            if isinstance(raw, dict):
                val = raw.get("id")
                if val is None:
                    val = raw.get("persona_id")
                if val is not None:
                    rid = str(val).strip()
                    return rid or None
            return None

        if not (isinstance(persona_assignment, dict) and persona_assignment):
            return {
                "status": "gap",
                "gaps": ["no_persona_assignment_on_run"],
                "coverage": {},
                "promotion_ready": False,
            }

        def _slot_eval(*, shelf_name: str, field: str, gap_prefix: str) -> None:
            sid = _slot_id(persona_assignment.get(field))
            if not sid:
                gaps.append(f"{gap_prefix}_missing")
                return
            entry = shelf.find_entry(shelf_name, sid)
            if entry is None:
                gaps.append(f"{gap_prefix}_not_on_shelf:{sid}")
                return
            out: dict[str, Any] = {"id": sid}
            status = entry.get("probation_status")
            if isinstance(status, str) and status.strip():
                clean = status.strip()
                out["probation_status"] = clean
                if clean == "probation":
                    gaps.append(f"probation_not_cleared:{sid}")
            ver = entry.get("version")
            if isinstance(ver, int) and not isinstance(ver, bool):
                out["version"] = ver
            cap = entry.get("capability_profile")
            if not isinstance(cap, str) or not cap.strip():
                gaps.append(f"capability_profile_missing:{sid}")
            else:
                out["capability_profile_len"] = len(cap.strip())
            boundary = entry.get("boundary_statement")
            if not isinstance(boundary, str) or not boundary.strip():
                gaps.append(f"boundary_statement_missing:{sid}")
            else:
                out["boundary_statement_len"] = len(boundary.strip())
            scope_in = entry.get("scope_in")
            if not isinstance(scope_in, list) or not scope_in:
                gaps.append(f"scope_in_missing:{sid}")
            else:
                out["scope_in_count"] = len(scope_in)
            scope_out = entry.get("scope_out")
            if not isinstance(scope_out, list) or not scope_out:
                gaps.append(f"scope_out_missing:{sid}")
            else:
                out["scope_out_count"] = len(scope_out)
            coverage[field] = out

        _slot_eval(
            shelf_name="business_area",
            field="business_area",
            gap_prefix="business_area",
        )
        _slot_eval(
            shelf_name="development_role",
            field="development_role",
            gap_prefix="development_role",
        )

        if gaps:
            status = "invalid"
            promotion_ready = False
        else:
            status = "ok"
            promotion_ready = True
        return {
            "status": status,
            "gaps": gaps,
            "coverage": coverage,
            "promotion_ready": promotion_ready,
        }


def _coerce_int(raw: object, default: int = 0) -> int:
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return default


def _coerce_max_iterations(raw: object, default: int = 3) -> int:
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        val = int(raw.strip())
        return val if val >= 1 else default
    return default


def self_refinement_policy_from_mapping(raw: dict[str, object]) -> SelfRefinementPolicy:
    return SelfRefinementPolicy(
        version=_coerce_int(raw.get("version", 0)),
        enabled=bool(raw.get("enabled", False)),
        description=str(raw.get("description", "")).strip(),
        max_iterations=_coerce_max_iterations(raw.get("max_iterations")),
        auto_promote_probation=bool(raw.get("auto_promote_probation", False)),
        llm_critique_enabled=bool(raw.get("llm_critique_enabled", False)),
    )


def load_self_refinement_policy(path: Path) -> SelfRefinementPolicy:
    return self_refinement_policy_from_mapping(load_yaml(path))
