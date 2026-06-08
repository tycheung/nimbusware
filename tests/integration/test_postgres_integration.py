from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors as pg_errors

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    RunStartedEvent,
    RunStartedPayload,
    Severity,
)
from nimbusware_store.postgres import PostgresEventStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


@pytest.fixture
def store() -> PostgresEventStore:
    return PostgresEventStore(_url())


def test_append_monotonic_store_seq(store: PostgresEventStore) -> None:
    run_id = uuid4()
    s1 = store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    s2 = store.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="test"),
        ),
    )
    assert s2 > s1


def test_find_run_id_by_correlation(store: PostgresEventStore) -> None:
    run_id = uuid4()
    corr = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            correlation_id=corr,
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    assert store.find_run_id_for_run_created_correlation(corr) == run_id


def test_db_rejects_unknown_event_type(store: PostgresEventStore) -> None:
    run_id = uuid4()
    with pytest.raises(pg_errors.CheckViolation):
        with psycopg.connect(_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO event_store (
                      event_id, run_id, event_type, event_version, occurred_at,
                      payload, metadata
                    ) VALUES (
                      %s, %s, %s, 1, NOW(),
                      '{}'::jsonb, '{}'::jsonb
                    )
                    """,
                    (uuid4(), run_id, "not.a.real.event.type"),
                )
            conn.commit()


def test_count_recent_runs_matches_filtered_list(store: PostgresEventStore) -> None:
    wf = "default"
    total = store.count_recent_runs(workflow_profile=wf)
    listed = store.list_recent_run_ids(
        limit=max(total + 50, 100),
        offset=0,
        workflow_profile=wf,
    )
    assert len(listed) == total


def test_list_recent_run_ids(store: PostgresEventStore) -> None:
    ids = store.list_recent_run_ids(limit=5)
    assert isinstance(ids, list)


def test_run_list_status_view_created_only(store: PostgresEventStore) -> None:
    rid = uuid4()
    now = datetime.now(timezone.utc)
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            payload=RunCreatedPayload(
                workflow_profile=f"list-status-{uuid4()}",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT list_status FROM run_list_status WHERE run_id = %s",
                (rid,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "created"


def test_list_recent_run_rows_cursor_matches_offset_page(store: PostgresEventStore) -> None:
    wf = f"cursor-parity-{uuid4()}"
    r0 = uuid4()
    r1 = uuid4()
    now = datetime.now(timezone.utc)
    for rid in (r0, r1):
        store.append(
            RunCreatedEvent(
                event_type=EventType.RUN_CREATED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                payload=RunCreatedPayload(
                    workflow_profile=wf,
                    policy_version="1",
                    config_snapshot_id=str(uuid4()),
                ),
            ),
        )
    first = store.list_recent_run_ids(
        limit=1,
        offset=0,
        workflow_profile=wf,
        order="newest_first",
    )
    second_off = store.list_recent_run_ids(
        limit=1,
        offset=1,
        workflow_profile=wf,
        order="newest_first",
    )
    assert len(first) == 1 and len(second_off) == 1
    mx0 = store.max_store_seq_for_run(str(first[0]))
    assert mx0 is not None
    rows_c, has_more = store.list_recent_run_rows_cursor(
        limit=1,
        cursor_after_seq=mx0,
        cursor_after_run_id=first[0],
        workflow_profile=wf,
        order="newest_first",
    )
    assert [t[0] for t in rows_c] == second_off
    assert has_more is False


def test_run_projection_view_exists_and_counts(store: PostgresEventStore) -> None:
    writer = UUID("44444444-4444-4444-8444-444444444404")
    run_id = uuid4()
    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.views
                WHERE table_schema = 'public' AND table_name = 'run_projection'
                """,
            )
            assert cur.fetchone()[0] == 1

    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=FindingCreatedPayload(
                finding_id=uuid4(),
                category="test",
                owner_role=writer,
                severity=Severity.LOW,
                source_artifact="integration",
                repro_steps=["line1"],
                required_fixes=[],
            ),
        ),
    )
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="test:integration",
                reason_code="test_escalation",
            ),
        ),
    )
    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_count, findings_count, has_escalation
                FROM run_projection
                WHERE run_id = %s
                """,
                (run_id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert int(row[0]) == 3
            assert int(row[1]) == 1
            assert row[2] is True


def test_list_recent_run_ids_workflow_filter(store: PostgresEventStore) -> None:
    r_a = uuid4()
    r_b = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=r_a,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=r_b,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="other-profile-xyz",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    ids = store.list_recent_run_ids(limit=10, workflow_profile="default")
    assert r_a in ids
    assert r_b not in ids


def test_list_recent_run_ids_has_escalation_filter(store: PostgresEventStore) -> None:
    r_plain = uuid4()
    r_esc = uuid4()
    for rid in (r_plain, r_esc):
        store.append(
            RunCreatedEvent(
                event_type=EventType.RUN_CREATED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=RunCreatedPayload(
                    workflow_profile="default",
                    policy_version="1",
                    config_snapshot_id=str(uuid4()),
                ),
            ),
        )
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=r_esc,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="test:integration",
                reason_code="test_filter",
            ),
        ),
    )
    yes = store.list_recent_run_ids(
        limit=50,
        workflow_profile="default",
        has_escalation=True,
    )
    assert r_esc in yes
    assert r_plain not in yes
    no = store.list_recent_run_ids(
        limit=50,
        workflow_profile="default",
        has_escalation=False,
    )
    assert r_plain in no
    assert r_esc not in no
    assert store.count_recent_runs(workflow_profile="default", has_escalation=True) >= 1
    assert store.count_recent_runs(workflow_profile="default", has_escalation=False) >= 1


def test_nimbusware_roles_registry_seeded(store: PostgresEventStore) -> None:
    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM nimbusware_roles_registry")
            assert int(cur.fetchone()[0]) >= 5


def test_load_registry_from_postgres_roundtrip(store: PostgresEventStore) -> None:
    from nimbusware_orchestrator.registry_db import load_registry_from_postgres

    reg = load_registry_from_postgres(_url())
    assert reg.resolve("backend_writer") == UUID("44444444-4444-4444-8444-444444444404")
