"""Extension building blocks: personas, bundles, escalation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from agent_core.yaml_io import load_yaml
from nimbusware_extensions.personas import PersonaShelf
from nimbusware_store.protocol import EventStore


@runtime_checkable
class ModuleIntegratorPort(Protocol):
    """Integration path + compatibility gate thresholds."""

    def score_fit(self, bundle_id: str, project_profile: dict[str, Any]) -> float: ...


class ModuleIntegrator:
    """Default integrator: deterministic score from bundle tags overlap + YAML threshold."""

    def __init__(self, *, min_score_to_pass: float = 0.0) -> None:
        self._min_score = min_score_to_pass

    @property
    def min_score_to_pass(self) -> float:
        return self._min_score

    @classmethod
    def from_yaml(cls, path: Path) -> ModuleIntegrator:
        raw = load_yaml(path)
        return cls(min_score_to_pass=float(raw.get("min_score_to_pass", 0.0)))

    def score_fit(self, bundle_id: str, project_profile: dict[str, Any]) -> float:
        """Compatibility score.

        When ``project_profile`` includes non-empty ``bundle_tags`` (catalog tags for the
        mapped bundle), score is tag recall: ``|project_tags ∩ bundle_tags| / |bundle_tags|``.
        Otherwise use the tag-free fallback heuristic (bundle id listed as a tag
        → 1.0, else 0.5/0.0).
        """
        bundle_tags_raw = project_profile.get("bundle_tags")
        if isinstance(bundle_tags_raw, list) and bundle_tags_raw:
            tags = project_profile.get("tags")
            if not isinstance(tags, list):
                tags = []
            proj = {str(t).lower() for t in tags if str(t).strip()}
            bset = {str(t).lower() for t in bundle_tags_raw if str(t).strip()}
            if not bset:
                return 0.0
            return len(proj & bset) / max(len(bset), 1)
        tags = project_profile.get("tags")
        if not isinstance(tags, list):
            return 0.0
        tag_set = {str(t).lower() for t in tags}
        if bundle_id.lower() in tag_set:
            return 1.0
        return 0.5 if tag_set else 0.0

    def passes_gate(self, bundle_id: str, project_profile: dict[str, Any]) -> bool:
        return self.score_fit(bundle_id, project_profile) >= self._min_score


@runtime_checkable
class AgentEvaluatorPort(Protocol):
    """§3B.3 Agent Evaluator lifecycle."""

    def evaluate(self, persona_id: str) -> dict[str, Any]: ...


AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD = 0.75
AGENT_EVALUATOR_STRONG_SCORE_THRESHOLD = 0.90


def agent_evaluator_score_band(
    score: float,
    *,
    promotion_threshold: float = AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD,
    strong_threshold: float = AGENT_EVALUATOR_STRONG_SCORE_THRESHOLD,
) -> str:
    """Depth label for rules/LLM evaluator scoring."""
    if score < promotion_threshold:
        return "below_threshold"
    if score < strong_threshold:
        return "meets_threshold"
    return "strong"


class AgentEvaluator:
    def evaluate(
        self,
        persona_id: str,
        *,
        persona_assignment: dict[str, Any] | None = None,
        shelf: PersonaShelf | None = None,
    ) -> dict[str, Any]:
        """Deterministic rules loop v1: catalog + optional composite assignment coverage."""
        pid = str(persona_id).strip() or "default"
        gaps: list[str] = []
        coverage: dict[str, Any] = {}

        if shelf is None:
            return {
                "persona_id": pid,
                "status": "invalid",
                "gaps": ["shelf_unavailable"],
                "coverage": coverage,
            }

        all_ids = shelf.all_persona_ids()
        if pid != "default" and pid not in all_ids:
            gaps.append(f"workflow_persona_id_not_in_catalog:{pid}")

        def _slot_id(raw: object) -> str | None:
            if isinstance(raw, str):
                s = raw.strip()
                return s or None
            if isinstance(raw, dict):
                val = raw.get("id")
                if val is None:
                    val = raw.get("persona_id")
                if val is not None:
                    s = str(val).strip()
                    return s or None
            return None

        if isinstance(persona_assignment, dict):
            ba_id = _slot_id(persona_assignment.get("business_area"))
            dr_id = _slot_id(persona_assignment.get("development_role"))
            if ba_id:
                entry = shelf.find_entry("business_area", ba_id)
                if entry is None:
                    gaps.append(f"business_area_not_on_shelf:{ba_id}")
                else:
                    slot: dict[str, Any] = {"id": ba_id}
                    ps = entry.get("probation_status")
                    if isinstance(ps, str) and ps.strip():
                        slot["probation_status"] = ps.strip()
                    ver = entry.get("version")
                    if isinstance(ver, int) and not isinstance(ver, bool):
                        slot["version"] = ver
                    coverage["business_area"] = slot
            if dr_id:
                entry = shelf.find_entry("development_role", dr_id)
                if entry is None:
                    gaps.append(f"development_role_not_on_shelf:{dr_id}")
                else:
                    slot = {"id": dr_id}
                    ps = entry.get("probation_status")
                    if isinstance(ps, str) and ps.strip():
                        slot["probation_status"] = ps.strip()
                    ver = entry.get("version")
                    if isinstance(ver, int) and not isinstance(ver, bool):
                        slot["version"] = ver
                    coverage["development_role"] = slot

        scope_overlaps: list[str] = []
        if shelf is not None:
            from nimbusware_extensions.persona_scope_overlap import scope_in_overlaps_for_assignment

            scope_overlaps = scope_in_overlaps_for_assignment(
                shelf=shelf,
                persona_assignment=persona_assignment,
            )
            for warning in scope_overlaps:
                gaps.append(f"scope_in_overlap:{warning[:120]}")

        if gaps:
            status = "invalid"
        elif pid == "default" and not (isinstance(persona_assignment, dict) and persona_assignment):
            status = "gap"
            gaps.append("no_persona_assignment_on_run")
        else:
            status = "ok"

        covered_slots = 0
        if isinstance(coverage.get("business_area"), dict):
            covered_slots += 1
        if isinstance(coverage.get("development_role"), dict):
            covered_slots += 1
        required_slots = 2
        coverage_ratio = covered_slots / required_slots
        gap_penalty = min(len(gaps), 3) * 0.25
        score = max(0.0, min(1.0, coverage_ratio - gap_penalty))
        score = round(score, 3)

        return {
            "persona_id": pid,
            "status": status,
            "gaps": gaps,
            "coverage": coverage,
            "coverage_ratio": coverage_ratio,
            "score": score,
            "scope_overlaps": scope_overlaps,
            "promotion_ready": status == "ok"
            and score >= AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD,
            "score_band": agent_evaluator_score_band(score),
        }

    def emit_evaluation_stage_started(
        self,
        store: EventStore,
        *,
        run_id: UUID,
        persona_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append ``stage.started`` for persona evaluation (no new ``event_type``)."""
        from datetime import datetime, timezone
        from uuid import uuid4

        from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

        envelope_meta: dict[str, Any] = dict(metadata) if metadata else {}
        store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=envelope_meta,
                payload=StageStartedPayload(stage_name=f"agent_eval:{persona_id}", attempt=1),
            ),
        )


@runtime_checkable
class UniversalCritiquePort(Protocol):
    """§3B.5 universal critique pairings."""

    def pairing_for(self, producer_role: str) -> list[str]: ...


class UniversalCritiqueRouter:
    """Data-driven critique pairings (default YAML under ``configs/personas/``)."""

    _DEFAULT_CRITICS = ("product_reference_critic", "domain_critic")

    def __init__(self, pairings: dict[str, list[str]]) -> None:
        self._pairings = {k.strip().lower(): list(v) for k, v in pairings.items()}

    @classmethod
    def from_content(cls, raw: dict[str, object]) -> UniversalCritiqueRouter:
        pr = raw.get("pairings")
        if not isinstance(pr, dict):
            return cls({})
        out: dict[str, list[str]] = {}
        for k, v in pr.items():
            if isinstance(k, str) and isinstance(v, list):
                out[k] = [str(x) for x in v]
        return cls(out)

    @classmethod
    def from_yaml(cls, path: Path) -> UniversalCritiqueRouter:
        return cls.from_content(load_yaml(path))

    def known_producer_keys(self) -> frozenset[str]:
        """Taxonomy keys with explicit pairings in the loaded YAML."""
        return frozenset(self._pairings.keys())

    def pairing_for(self, producer_role: str) -> list[str]:
        key = producer_role.strip().lower()
        if key in self._pairings:
            return list(self._pairings[key])
        return list(self._DEFAULT_CRITICS)


class SecurityScanner:
    """Runs orchestrator static security scan (ruff + optional bandit)."""

    def run(self, workspace: str) -> dict[str, Any]:
        from pathlib import Path

        from nimbusware_orchestrator.security_scan import run_security_scan

        code, log, ruff_ec, bandit_ec, mypy_ec, perf_ec, n1_ec, _semgrep_ec = run_security_scan(
            Path(workspace),
        )
        return {
            "exit_code": code,
            "ruff_exit_code": ruff_ec,
            "bandit_exit_code": bandit_ec,
            "mypy_exit_code": mypy_ec,
            "ruff_perf_exit_code": perf_ec,
            "n_plus_one_exit_code": n1_ec,
            "log": log[:8000],
        }


SecurityScannerStub = SecurityScanner
