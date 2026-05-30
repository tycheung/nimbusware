from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", "test-admin-token")

from agent_core.models import (  # noqa: E402
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    SelfRefinementLoopSignalledEvent,
    SelfRefinementLoopSignalledPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
