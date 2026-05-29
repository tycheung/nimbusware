"""Extract and persist integrator bundle gate outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from agent_core.models import EventType, Verdict
from hermes_extensions.bundle_memory_models import BundleOutcomeRecord, BundleSuccessStats


def build_bundle_outcome_from_gate(
    *,
    run_id: UUID,
    bundle_id: str,
    workflow_profile: str | None,
    project_tags: list[str],
    integrator_score: float,
    verdict: Verdict,
    source_store_seq: int | None = None,
) -> BundleOutcomeRecord:
    return BundleOutcomeRecord(
        outcome_id=uuid4(),
        run_id=run_id,
        bundle_id=str(bundle_id).strip(),
        workflow_profile=workflow_profile,
        project_tags=tuple(str(t).strip() for t in project_tags if str(t).strip()),
        integrator_score=float(integrator_score),
        verdict=str(verdict.value),
        source_store_seq=source_store_seq,
        recorded_at=datetime.now(timezone.utc),
    )


def bundle_outcome_metadata(record: BundleOutcomeRecord) -> dict[str, Any]:
    return {
        "bundle_id": record.bundle_id,
        "workflow_profile": record.workflow_profile,
        "project_tags": list(record.project_tags),
        "integrator_score": record.integrator_score,
        "verdict": record.verdict,
        "outcome_id": str(record.outcome_id),
    }


def extract_bundle_outcomes_from_event_rows(rows: list[dict[str, Any]]) -> list[BundleOutcomeRecord]:
    """Rebuild outcome records from integrator ``gate.decision.emitted`` rows."""
    wf_by_run: dict[UUID, str | None] = {}
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        rid = UUID(str(row["run_id"]))
        pl = row.get("payload") or {}
        wf = pl.get("workflow_profile") if isinstance(pl, dict) else None
        wf_by_run[rid] = str(wf) if wf is not None else None

    out: list[BundleOutcomeRecord] = []
    for row in rows:
        if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        pl = row.get("payload") or {}
        if not isinstance(pl, dict):
            continue
        if str(pl.get("stage_name", "")) != "bundle_compatibility":
            continue
        meta = row.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        if not meta.get("integrator_gate") and not meta.get("bundle_id"):
            continue
        bo = meta.get("bundle_outcome")
        if isinstance(bo, dict) and bo.get("bundle_id"):
            bundle_id = str(bo["bundle_id"])
            project_tags = bo.get("project_tags") or meta.get("integrator_project_tags") or []
            score_raw = bo.get("integrator_score", meta.get("integrator_score"))
        else:
            bundle_id = str(meta.get("bundle_id", "")).strip()
            project_tags = meta.get("integrator_project_tags") or []
            score_raw = meta.get("integrator_score")
        if not bundle_id:
            continue
        rid = UUID(str(row["run_id"]))
        verdict = str(pl.get("verdict", "")).upper() or Verdict.FAIL.value
        score = float(score_raw) if score_raw is not None else None
        tags = [str(t) for t in project_tags if str(t).strip()] if isinstance(project_tags, list) else []
        out.append(
            BundleOutcomeRecord(
                outcome_id=uuid4(),
                run_id=rid,
                bundle_id=bundle_id,
                workflow_profile=wf_by_run.get(rid),
                project_tags=tuple(tags),
                integrator_score=score,
                verdict=verdict,
                source_store_seq=int(row["store_seq"]) if row.get("store_seq") is not None else None,
            ),
        )
    return out


def aggregate_bundle_success_stats(
    records: list[BundleOutcomeRecord],
) -> dict[str, BundleSuccessStats]:
    buckets: dict[str, dict[str, Any]] = {}
    for rec in records:
        bid = rec.bundle_id
        bucket = buckets.setdefault(
            bid,
            {"pass": 0, "fail": 0, "last_verdict": rec.verdict},
        )
        if rec.verdict == Verdict.PASS.value:
            bucket["pass"] = int(bucket["pass"]) + 1
        else:
            bucket["fail"] = int(bucket["fail"]) + 1
        bucket["last_verdict"] = rec.verdict
    stats: dict[str, BundleSuccessStats] = {}
    for bid, bucket in buckets.items():
        passed = int(bucket["pass"])
        failed = int(bucket["fail"])
        total = passed + failed
        rate = (passed / total) if total else 0.0
        stats[bid] = BundleSuccessStats(
            bundle_id=bid,
            pass_count=passed,
            fail_count=failed,
            sample_count=total,
            success_rate=rate,
            last_verdict=str(bucket.get("last_verdict")),
        )
    return stats


def bundle_memory_rank_weight() -> float:
    import os

    raw = os.environ.get("HERMES_BUNDLE_MEMORY_RANK_WEIGHT", "0.2").strip()
    try:
        w = float(raw)
    except ValueError:
        return 0.2
    return max(0.0, min(1.0, w))


def blend_bundle_rank_score(
    base_score: float,
    *,
    bundle_id: str,
    stats: dict[str, BundleSuccessStats],
    weight: float | None = None,
) -> float:
    w = bundle_memory_rank_weight() if weight is None else max(0.0, min(1.0, weight))
    if w <= 0.0:
        return base_score
    stat = stats.get(bundle_id)
    memory_score = stat.success_rate if stat is not None else 0.5
    return (base_score * (1.0 - w)) + (memory_score * w)


@runtime_checkable
class BundleOutcomeStore(Protocol):
    def append(self, record: BundleOutcomeRecord) -> None: ...

    def list_all(self) -> list[BundleOutcomeRecord]: ...

    def success_stats(self) -> dict[str, BundleSuccessStats]: ...


class InMemoryBundleOutcomeStore:
    def __init__(self) -> None:
        self.records: list[BundleOutcomeRecord] = []

    def append(self, record: BundleOutcomeRecord) -> None:
        self.records.append(record)

    def list_all(self) -> list[BundleOutcomeRecord]:
        return list(self.records)

    def success_stats(self) -> dict[str, BundleSuccessStats]:
        return aggregate_bundle_success_stats(self.records)


class PostgresBundleOutcomeStore:
    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def append(self, record: BundleOutcomeRecord) -> None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO hermes_bundle_outcome (
                      outcome_id, run_id, bundle_id, workflow_profile,
                      project_tags, integrator_score, verdict, source_store_seq
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.outcome_id,
                        record.run_id,
                        record.bundle_id,
                        record.workflow_profile,
                        Jsonb(list(record.project_tags)),
                        record.integrator_score,
                        record.verdict,
                        record.source_store_seq,
                    ),
                )
            conn.commit()

    def list_all(self) -> list[BundleOutcomeRecord]:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT outcome_id, run_id, bundle_id, workflow_profile,
                           project_tags, integrator_score, verdict,
                           source_store_seq, created_at
                    FROM hermes_bundle_outcome
                    ORDER BY created_at ASC
                    """,
                )
                rows = cur.fetchall()
        return [_record_from_row(r) for r in rows]

    def success_stats(self) -> dict[str, BundleSuccessStats]:
        return aggregate_bundle_success_stats(self.list_all())


def _record_from_row(row: dict[str, Any]) -> BundleOutcomeRecord:
    tags = row.get("project_tags")
    if not isinstance(tags, list):
        tags = []
    return BundleOutcomeRecord(
        outcome_id=UUID(str(row["outcome_id"])),
        run_id=UUID(str(row["run_id"])),
        bundle_id=str(row["bundle_id"]),
        workflow_profile=row.get("workflow_profile"),
        project_tags=tuple(str(t) for t in tags),
        integrator_score=float(row["integrator_score"]) if row.get("integrator_score") is not None else None,
        verdict=str(row["verdict"]),
        source_store_seq=int(row["source_store_seq"]) if row.get("source_store_seq") is not None else None,
        recorded_at=row.get("created_at"),
    )
