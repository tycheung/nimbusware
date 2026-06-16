from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogMetadata,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
    sync_backlog_metadata,
)
from agent_core.models.events_payloads import (
    DeliveryBacklogGeneratedPayload,
    DeliveryBacklogRevisedPayload,
)
from agent_core.models.events_records import (
    DeliveryBacklogGeneratedEvent,
    DeliveryBacklogRevisedEvent,
)
from agent_core.read.campaign import (
    apply_slice_outcomes,
    backlog_from_events,
    has_backlog_event,
)

__all__ = [
    "apply_slice_outcomes",
    "backlog_from_events",
    "has_backlog_event",
    "generate_stub_backlog",
    "ensure_backlog",
    "emit_backlog_generated",
    "emit_backlog_revised",
    "validate_backlog",
    "effective_backlog_generator_mode",
]


def effective_backlog_generator_mode(policy_mode: str) -> tuple[str, str | None]:
    mode = str(policy_mode or "stub").strip().lower()
    if mode not in ("stub", "llm"):
        mode = "stub"
    from nimbusware_env.env_flags import nimbusware_use_llm_enabled
    from nimbusware_env.settings_resolve import resolve_str

    llm_on = nimbusware_use_llm_enabled()
    model = resolve_str("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", default="").strip()
    if mode == "llm":
        if not llm_on:
            return "stub", "NIMBUSWARE_USE_LLM is off"
        if not model:
            return "stub", "NIMBUSWARE_BACKLOG_GENERATOR_MODEL is unset"
        return "llm", None
    if llm_on and model:
        return "llm", None
    if not llm_on:
        return "stub", "Set NIMBUSWARE_USE_LLM=1 for LLM campaign backlog"
    return "stub", "Set NIMBUSWARE_BACKLOG_GENERATOR_MODEL for LLM campaign backlog"


def _requirements_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            req = meta.get("requirements")
            if isinstance(req, dict):
                return req
        break
    return None


def generate_stub_backlog(
    campaign_id: str,
    *,
    requirements: dict[str, Any] | None = None,
    max_slices: int = 10,
) -> DeliveryBacklog:
    prompt = ""
    if isinstance(requirements, dict):
        prompt = str(requirements.get("business_prompt") or requirements.get("prompt") or "")
    title = "Campaign delivery"
    if prompt.strip():
        title = prompt.strip()[:120]
    count = max(1, min(max_slices, 10))
    default_paths = (
        "packages/nimbusware_orchestrator/micro_slice.py",
        "packages/nimbusware_orchestrator/slice_gate.py",
    )
    slices: list[BacklogSlice] = []
    for i in range(1, count + 1):
        sid = f"slice-stub-{i:03d}"
        deps: tuple[str, ...] = ()
        if i > 1:
            deps = (f"slice-stub-{i - 1:03d}",)
        slices.append(
            BacklogSlice(
                slice_id=sid,
                status=SliceStatus.PENDING,
                target_paths=default_paths,
                depends_on=deps,
                estimated_loc=80,
                rationale=f"Stub slice {i} for campaign: {title[:80]}",
            ),
        )
    backlog = DeliveryBacklog(
        campaign_id=campaign_id,
        epics=(
            BacklogEpic(
                epic_id="epic-stub",
                title=title,
                status=EpicStatus.IN_PROGRESS,
                features=(
                    BacklogFeature(
                        feature_id="feat-stub",
                        title="Stub feature scaffold",
                        acceptance_criteria=("All stub slices pass gate",),
                        slices=tuple(slices),
                    ),
                ),
            ),
        ),
        metadata=BacklogMetadata(generator_mode="stub"),
    )
    return sync_backlog_metadata(backlog)


def emit_backlog_generated(
    store: Any,
    run_id: UUID,
    backlog: DeliveryBacklog,
    *,
    generator_mode: str = "stub",
) -> None:
    store.append(
        DeliveryBacklogGeneratedEvent(
            event_type=EventType.DELIVERY_BACKLOG_GENERATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=DeliveryBacklogGeneratedPayload(
                campaign_id=backlog.campaign_id,
                backlog=backlog.model_dump(mode="json"),
                generator_mode=generator_mode,  # type: ignore[arg-type]
            ),
        ),
    )


def validate_backlog_limits(backlog: DeliveryBacklog, *, max_slices: int) -> list[str]:
    errors: list[str] = []
    total = backlog.metadata.total_slices_planned
    if total > max_slices:
        errors.append(f"backlog has {total} slices; max is {max_slices}")
    return errors


def validate_backlog(backlog: DeliveryBacklog, *, max_slices: int) -> list[str]:
    from agent_core.models.backlog import validate_backlog_dag

    errors = list(validate_backlog_dag(backlog))
    errors.extend(validate_backlog_limits(backlog, max_slices=max_slices))
    return errors


def _generate_backlog_for_run(
    run_id: UUID,
    rows: list[dict[str, Any]],
    *,
    generator_mode: str,
    max_slices: int,
    repo_root: Any | None = None,
) -> DeliveryBacklog:
    requirements = _requirements_from_rows(rows)
    if generator_mode == "llm":
        from nimbusware_env.env_flags import nimbusware_use_llm_enabled

        if nimbusware_use_llm_enabled():
            from nimbusware_env.env_flags import nimbusware_ollama_base_url
            from nimbusware_env.settings_resolve import resolve_str

            model = resolve_str("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", default="")
            base_url = nimbusware_ollama_base_url()
            if model.strip():
                from nimbusware_orchestrator.llm.backlog_generator import generate_llm_backlog

                repo_context = ""
                if repo_root is not None:
                    try:
                        from nimbusware_orchestrator.slice_repo_map import build_repo_map_excerpt

                        repo_context = build_repo_map_excerpt(
                            repo_root,
                            ("packages/",),
                            max_chars=4000,
                        )
                    except (ImportError, OSError, TypeError, ValueError):
                        repo_context = ""
                llm_backlog = generate_llm_backlog(
                    campaign_id=str(run_id),
                    requirements=requirements,
                    base_url=base_url,
                    model_id=model.strip(),
                    max_slices=max_slices,
                    repo_context=repo_context,
                )
                if llm_backlog is not None:
                    errors = validate_backlog(llm_backlog, max_slices=max_slices)
                    if not errors:
                        return sync_backlog_metadata(llm_backlog)
    return generate_stub_backlog(
        str(run_id),
        requirements=requirements,
        max_slices=max_slices,
    )


def ensure_backlog(
    store: Any,
    run_id: UUID,
    rows: list[dict[str, Any]],
    *,
    generator_mode: str = "stub",
    max_slices: int = 10,
    repo_root: Any | None = None,
) -> DeliveryBacklog:
    existing = backlog_from_events(rows)
    if existing is not None:
        return apply_slice_outcomes(existing, rows)
    backlog = _generate_backlog_for_run(
        run_id,
        rows,
        generator_mode=generator_mode,
        max_slices=max_slices,
        repo_root=repo_root,
    )
    actual_mode = str(backlog.metadata.generator_mode or generator_mode)
    emit_backlog_generated(store, run_id, backlog, generator_mode=actual_mode)
    return backlog


def emit_backlog_revised(
    store: Any,
    run_id: UUID | str,
    backlog: DeliveryBacklog,
    *,
    revision_reason: str,
) -> None:
    resolved_run_id = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
    store.append(
        DeliveryBacklogRevisedEvent(
            event_type=EventType.DELIVERY_BACKLOG_REVISED,
            event_id=uuid4(),
            run_id=resolved_run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=DeliveryBacklogRevisedPayload(
                campaign_id=backlog.campaign_id,
                revision_reason=revision_reason,
                backlog=backlog.model_dump(mode="json"),
            ),
        ),
    )
