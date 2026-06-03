from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    RequiredFixArtifact,
    RunCreatedEvent,
    RunCreatedPayload,
    Severity,
    Verdict,
)
from hermes_orchestrator.fleet_critic_reliability import tenant_critic_reliability_metrics
from hermes_store.memory import InMemoryEventStore
from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_iam.context import reset_auth_context, set_auth_context
from nimbusware_iam.models import AuthContext


def _auth(tenant_id) -> AuthContext:
    return AuthContext(
        tenant_id=tenant_id,
        tenant_slug="t",
        key_id=uuid4(),
        role_taxonomy_keys=(),
        api_scopes=("maker_admin",),
    )


def _seed_critic_run(store: InMemoryEventStore, *, verdict: str) -> None:
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"tenant_id": str(DEFAULT_TENANT_ID)},
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    role_id = uuid4()
    store.append(
        CriticVerdictEmittedEvent(
            event_type=EventType.CRITIC_VERDICT_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=CriticVerdictEmittedPayload(
                critic_role=role_id,
                verdict=Verdict.FAIL if verdict == "FAIL" else Verdict.PASS,
                severity=Severity.HIGH,
                owner_role=role_id,
                is_in_domain=True,
                required_fixes=(
                    [
                        RequiredFixArtifact(
                            format="json_patch",
                            target_files=["src/a.py"],
                            patch_artifact="[]",
                            validation_steps=["pytest"],
                            acceptance_criteria="tests pass",
                        ),
                    ]
                    if verdict == "FAIL"
                    else []
                ),
            ),
        ),
    )


@pytest.fixture(autouse=True)
def _reset_tenant_ctx() -> None:
    yield
    reset_auth_context()


def test_tenant_critic_reliability_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    store = InMemoryEventStore()
    _seed_critic_run(store, verdict="FAIL")
    metrics = tenant_critic_reliability_metrics(
        store,
        tenant_id=DEFAULT_TENANT_ID,
        run_limit=10,
    )
    assert metrics["critic_verdict_count"] >= 1
    assert metrics["critic_fail_count"] >= 1
    assert metrics["critic_fail_rate"] > 0
