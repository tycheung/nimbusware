from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, validate_event_dict
from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    count_backlog_slices,
    sync_backlog_metadata,
    validate_backlog_dag,
)
from agent_core.models.events_payloads import (
    CampaignCreatedPayload,
    CampaignPolicyPayload,
    DeliveryBacklogGeneratedPayload,
)
from agent_core.models.events_records import (
    CampaignCreatedEvent,
    DeliveryBacklogGeneratedEvent,
)
from store.allowed_types import allowed_event_type_values


def _sample_backlog() -> DeliveryBacklog:
    return DeliveryBacklog(
        campaign_id=str(uuid4()),
        epics=(
            BacklogEpic(
                epic_id="epic-auth",
                title="Authentication",
                status=EpicStatus.PENDING,
                features=(
                    BacklogFeature(
                        feature_id="feat-login",
                        title="Login",
                        acceptance_criteria=("User can log in",),
                        slices=(
                            BacklogSlice(
                                slice_id="slice-001",
                                target_paths=("src/auth.py",),
                                estimated_loc=80,
                            ),
                            BacklogSlice(
                                slice_id="slice-002",
                                depends_on=("slice-001",),
                                target_paths=("src/session.py",),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_sync_backlog_metadata_aligns_slice_count() -> None:
    backlog = sync_backlog_metadata(_sample_backlog())
    assert count_backlog_slices(backlog) == 2
    assert backlog.metadata.total_slices_planned == 2


def test_validate_backlog_dag_acyclic() -> None:
    backlog = _sample_backlog()
    assert validate_backlog_dag(backlog) == []


def test_validate_backlog_dag_detects_cycle() -> None:
    backlog = DeliveryBacklog(
        campaign_id="c1",
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="E",
                features=(
                    BacklogFeature(
                        feature_id="f1",
                        title="F",
                        slices=(
                            BacklogSlice(slice_id="a", depends_on=("b",)),
                            BacklogSlice(slice_id="b", depends_on=("a",)),
                        ),
                    ),
                ),
            ),
        ),
    )
    errors = validate_backlog_dag(backlog)
    assert len(errors) == 1
    assert "cycle" in errors[0]


def test_validate_backlog_dag_unknown_dependency() -> None:
    backlog = DeliveryBacklog(
        campaign_id="c1",
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="E",
                features=(
                    BacklogFeature(
                        feature_id="f1",
                        title="F",
                        slices=(BacklogSlice(slice_id="a", depends_on=("missing",)),),
                    ),
                ),
            ),
        ),
    )
    errors = validate_backlog_dag(backlog)
    assert any("unknown slice" in e for e in errors)


def test_campaign_event_round_trip() -> None:
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    policy = CampaignPolicyPayload(autonomous=True, backlog_generator="stub")
    event = CampaignCreatedEvent(
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=now,
        event_type=EventType.CAMPAIGN_CREATED,
        payload=CampaignCreatedPayload(
            campaign_id=str(run_id),
            workflow_profile="campaign_micro_slice",
            policy=policy,
        ),
    )
    data = event.model_dump(mode="json")
    parsed = validate_event_dict(data)
    assert parsed.event_type == EventType.CAMPAIGN_CREATED
    assert parsed.payload.workflow_profile == "campaign_micro_slice"


def test_delivery_backlog_generated_event_round_trip() -> None:
    run_id = uuid4()
    backlog = _sample_backlog()
    event = DeliveryBacklogGeneratedEvent(
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        event_type=EventType.DELIVERY_BACKLOG_GENERATED,
        payload=DeliveryBacklogGeneratedPayload(
            campaign_id=str(run_id),
            backlog=backlog.model_dump(mode="json"),
            generator_mode="stub",
        ),
    )
    parsed = validate_event_dict(event.model_dump(mode="json"))
    assert parsed.payload.generator_mode == "stub"


def test_campaign_event_types_in_allowlist() -> None:
    for et in (
        "campaign.created",
        "delivery_backlog.generated",
        "slice.queued",
        "completion.evaluated",
    ):
        assert et in allowed_event_type_values()
