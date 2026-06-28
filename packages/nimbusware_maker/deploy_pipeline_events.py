from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StageFailedEvent, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import (
    StageFailedPayload,
    StagePassedPayload,
    StageStartedPayload,
)


def emit_terraform_validate_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    plan_artifact = str(result.get("plan_artifact") or "")
    now = datetime.now(timezone.utc)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={"detail": detail, "deploy": {"kind": "terraform_validate"}},
            payload=StageStartedPayload(stage_name="terraform.validate", attempt=1),
        ),
    )

    meta = {
        "detail": detail,
        "plan_artifact": plan_artifact,
        "files_checked": result.get("files_checked"),
    }
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="terraform.plan", duration_ms=0),
            ),
        )
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="ci.terraform", duration_ms=0),
            ),
        )
    elif status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="terraform.validate", duration_ms=0),
            ),
        )
    else:
        store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "stderr": result.get("stderr", "")},
                payload=StageFailedPayload(
                    stage_name="terraform.validate",
                    reason_code="terraform_validate_failed",
                    message=detail[:500],
                ),
            ),
        )


def live_urls_from_events(rows: list[dict[str, Any]]) -> dict[str, str]:
    api_url = ""
    web_url = ""
    for row in reversed(rows):
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if not api_url and meta.get("api_url"):
            api_url = str(meta["api_url"])
        if not web_url and meta.get("web_url"):
            web_url = str(meta["web_url"])
        urls = meta.get("live_urls")
        if isinstance(urls, dict):
            if not api_url and urls.get("api_url"):
                api_url = str(urls["api_url"])
            if not web_url and urls.get("web_url"):
                web_url = str(urls["web_url"])
            if not api_url and urls.get("api"):
                api_url = str(urls["api"])
            if not web_url and urls.get("web"):
                web_url = str(urls["web"])
        if api_url and web_url:
            break
    out: dict[str, str] = {}
    if api_url:
        out["api_url"] = api_url
    if web_url:
        out["web_url"] = web_url
    return out


def manifest_from_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        req = meta.get("requirements")
        if isinstance(req, dict):
            raw = req.get("stack_manifest")
            if isinstance(raw, dict):
                return raw
    return {}


def deploy_apply_passed_from_events(rows: list[dict[str, Any]]) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("stage_name") == "deploy.apply":
            return True
    return False


def deploy_smoke_passed_from_events(rows: list[dict[str, Any]]) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("stage_name") == "deploy.smoke":
            return True
    return False


def deploy_rollback_passed_from_events(rows: list[dict[str, Any]]) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("stage_name") == "deploy.rollback":
            return True
    return False


def emit_deploy_rollback_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {
        "detail": detail,
        "deploy": {"kind": "terraform_rollback"},
        "rollback_mode": result.get("rollback_mode"),
    }
    if result.get("deploy_environment"):
        meta["deploy_environment"] = result["deploy_environment"]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="deploy.rollback", attempt=1),
        ),
    )
    if status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "detail": detail or "rollback skipped"},
                payload=StagePassedPayload(stage_name="deploy.rollback", duration_ms=0),
            ),
        )
        return
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="deploy.rollback", duration_ms=0),
            ),
        )
        return
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={**meta, "stderr": result.get("stderr", "")},
            payload=StageFailedPayload(
                stage_name="deploy.rollback",
                reason_code="deploy_rollback_failed",
                message=detail[:500],
            ),
        ),
    )


def emit_deploy_smoke_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {"detail": detail, "deploy": {"kind": "smoke"}}
    for key in ("api_url", "web_url", "checks"):
        if result.get(key):
            meta[key] = result[key]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="deploy.smoke", attempt=1),
        ),
    )
    if status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "detail": detail or "smoke skipped"},
                payload=StagePassedPayload(stage_name="deploy.smoke", duration_ms=0),
            ),
        )
        return
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="deploy.smoke", duration_ms=0),
            ),
        )
        return
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageFailedPayload(
                stage_name="deploy.smoke",
                reason_code="deploy_smoke_failed",
                message=detail[:500],
            ),
        ),
    )


def emit_deploy_apply_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {"detail": detail, "deploy": {"kind": "terraform_apply"}}
    for key in ("api_url", "web_url", "live_urls"):
        if result.get(key):
            meta[key] = result[key]
    if result.get("deploy_environment"):
        meta["deploy_environment"] = result["deploy_environment"]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="deploy.started", attempt=1),
        ),
    )
    if status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "detail": detail or "apply skipped"},
                payload=StagePassedPayload(stage_name="deploy.apply", duration_ms=0),
            ),
        )
        return
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="deploy.apply", duration_ms=0),
            ),
        )
        return
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={**meta, "stderr": result.get("stderr", "")},
            payload=StageFailedPayload(
                stage_name="deploy.apply",
                reason_code="terraform_apply_failed",
                message=detail[:500],
            ),
        ),
    )
