"""L1 eval-gated prompt / overlay evolution (CONTEXT only; STABLE frozen)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from orchestrator.improvement.evolution_ledger import (
    EvolutionLayer,
    EvolutionPhase,
    emit_evolution_event,
)


def evolution_prompts_dir(workspace: Path) -> Path:
    path = workspace.resolve() / ".nimbusware" / "evolution" / "prompts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def propose_overlay_from_learning(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    excerpt: str,
    discipline: str = "general",
) -> dict[str, Any] | None:
    text = excerpt.strip()
    if not text:
        return None
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    artifact_id = f"prompt-{discipline}-{digest}"
    draft = {
        "artifact_id": artifact_id,
        "layer": EvolutionLayer.PROMPT.value,
        "discipline": discipline,
        "status": "draft",
        "source_excerpt": text[:2000],
        "proposed_overlay": (
            f"[evolved:{digest}] Prefer fixing patterns related to:\n{text[:800]}\n"
        ),
    }
    path = evolution_prompts_dir(workspace) / f"{artifact_id}.json"
    path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    emit_evolution_event(
        store,
        run_id,
        phase=EvolutionPhase.PROPOSED,
        layer=EvolutionLayer.PROMPT,
        artifact_id=artifact_id,
        detail={"path": str(path), "discipline": discipline},
    )
    return draft


def score_prompt_proposal(
    store: Any,
    run_id: UUID | str,
    *,
    artifact_id: str,
    gate_pass_delta: float,
    has_p0_security: bool,
) -> EvolutionPhase:
    """Soft A/B gate: promote only if delta >= 0 and no P0 security."""
    ok = gate_pass_delta >= 0.0 and not has_p0_security
    phase = EvolutionPhase.SCORED
    emit_evolution_event(
        store,
        run_id,
        phase=phase,
        layer=EvolutionLayer.PROMPT,
        artifact_id=artifact_id,
        detail={
            "gate_pass_delta": gate_pass_delta,
            "has_p0_security": has_p0_security,
            "eligible": ok,
        },
    )
    return phase


def promote_or_reject_prompt(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    artifact_id: str,
    promote: bool,
) -> bool:
    path = evolution_prompts_dir(workspace) / f"{artifact_id}.json"
    if not path.is_file():
        emit_evolution_event(
            store,
            run_id,
            phase=EvolutionPhase.REJECTED,
            layer=EvolutionLayer.PROMPT,
            artifact_id=artifact_id,
            detail={"reason": "missing_draft"},
        )
        return False
    draft = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(draft, dict):
        return False
    if promote:
        draft["status"] = "promoted"
        promoted_path = evolution_prompts_dir(workspace) / "promoted" / f"{artifact_id}.json"
        promoted_path.parent.mkdir(parents=True, exist_ok=True)
        promoted_path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
        path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
        emit_evolution_event(
            store,
            run_id,
            phase=EvolutionPhase.PROMOTED,
            layer=EvolutionLayer.PROMPT,
            artifact_id=artifact_id,
            detail={"path": str(promoted_path)},
        )
        return True
    draft["status"] = "rejected"
    path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    emit_evolution_event(
        store,
        run_id,
        phase=EvolutionPhase.REJECTED,
        layer=EvolutionLayer.PROMPT,
        artifact_id=artifact_id,
        detail={"reason": "operator_or_gate"},
    )
    return False


def load_promoted_overlay_text(workspace: Path, *, discipline: str = "general") -> str:
    promoted = evolution_prompts_dir(workspace) / "promoted"
    if not promoted.is_dir():
        return ""
    chunks: list[str] = []
    for path in sorted(promoted.glob("prompt-*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        if str(raw.get("discipline") or "general") != discipline:
            continue
        text = str(raw.get("proposed_overlay") or "").strip()
        if text:
            chunks.append(text)
    return "\n\n".join(chunks)
