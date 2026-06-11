from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agent_core.models import EventType
from nimbusware_extensions.phase2 import AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD
from nimbusware_store.protocol import EventStore

ProbationReliabilityDecision = Literal[
    "shelve",
    "notify_promote",
    "ok",
    "insufficient_data",
]


@dataclass(frozen=True)
class ProbationReliabilityMetrics:
    persona_id: str
    runs_evaluated: int
    avg_score: float | None
    below_threshold_count: int
    invalid_status_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "runs_evaluated": self.runs_evaluated,
            "avg_score": self.avg_score,
            "below_threshold_count": self.below_threshold_count,
            "invalid_status_count": self.invalid_status_count,
        }


def _evaluation_from_stage_metadata(meta: Any) -> dict[str, Any] | None:
    if not isinstance(meta, dict):
        return None
    ae = meta.get("agent_evaluator")
    if not isinstance(ae, dict):
        return None
    ev = ae.get("evaluation")
    if isinstance(ev, dict):
        return ev
    return None


def _score_from_evaluation(ev: dict[str, Any]) -> float | None:
    raw = ev.get("score")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def collect_persona_eval_metrics(
    store: EventStore,
    persona_id: str,
    *,
    run_limit: int = 10,
) -> ProbationReliabilityMetrics:
    pid = str(persona_id).strip()
    scores: list[float] = []
    below = 0
    invalid = 0
    if not pid or pid == "default":
        return ProbationReliabilityMetrics(
            persona_id=pid,
            runs_evaluated=0,
            avg_score=None,
            below_threshold_count=0,
            invalid_status_count=0,
        )

    scan_limit = max(run_limit * 4, run_limit)
    for run_id in store.list_recent_run_ids(limit=scan_limit, order="newest_first"):
        if len(scores) + invalid >= run_limit:
            break
        ev: dict[str, Any] | None = None
        for row in store.list_run_events(str(run_id)):
            if row.get("event_type") != EventType.STAGE_STARTED.value:
                continue
            pl = row.get("payload")
            if not isinstance(pl, dict):
                pl = {}
            stage_name = str(pl.get("stage_name") or "")
            candidate = _evaluation_from_stage_metadata(row.get("metadata"))
            if candidate is None:
                continue
            if stage_name == f"agent_eval:{pid}":
                ev = candidate
                break
            if str(candidate.get("persona_id") or "").strip() == pid:
                ev = candidate
                break
        if ev is None:
            continue
        status = str(ev.get("status") or "").strip().lower()
        if status == "invalid":
            invalid += 1
            continue
        score = _score_from_evaluation(ev)
        if score is None:
            continue
        scores.append(score)
        if score < AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD:
            below += 1

    avg = round(sum(scores) / len(scores), 3) if scores else None
    return ProbationReliabilityMetrics(
        persona_id=pid,
        runs_evaluated=len(scores) + invalid,
        avg_score=avg,
        below_threshold_count=below,
        invalid_status_count=invalid,
    )


def reliability_decision(
    metrics: ProbationReliabilityMetrics,
    *,
    min_runs: int,
    min_score: float,
    max_below_ratio: float,
    current_promotion_ready: bool = False,
) -> ProbationReliabilityDecision:
    evaluated = metrics.runs_evaluated
    if evaluated < min_runs:
        if current_promotion_ready:
            return "notify_promote"
        return "insufficient_data"

    if metrics.invalid_status_count > 0:
        return "shelve"

    score_runs = evaluated - metrics.invalid_status_count
    if score_runs > 0:
        below_ratio = metrics.below_threshold_count / score_runs
        if below_ratio >= max_below_ratio:
            return "shelve"
        if metrics.avg_score is not None and metrics.avg_score < min_score:
            return "shelve"

    if current_promotion_ready:
        return "notify_promote"
    return "ok"
