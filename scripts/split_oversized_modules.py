from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path.relative_to(REPO)} ({len(content.splitlines())} lines)")


def _read(rel: str) -> list[str]:
    return (REPO / rel).read_text(encoding="utf-8").splitlines(keepends=True)


def split_events() -> None:
    lines = _read("packages/agent_core/models/events.py")
    foundation = "".join(lines[:99])
    payloads = "".join(lines[100:455]) + "".join(lines[589:691])
    records = "".join(lines[456:588]) + "".join(lines[691:])

    _write(
        REPO / "packages/agent_core/models/events_foundation.py",
        foundation,
    )
    _write(
        REPO / "packages/agent_core/models/events_payloads.py",
        """from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from agent_core.models.events_foundation import EventType, RoleId, Severity, Verdict

"""
        + payloads,
    )
    _write(
        REPO / "packages/agent_core/models/events_records.py",
        """from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from agent_core.models.events_foundation import EventMetadata, EventType, RoleId
from agent_core.models.events_payloads import (
    DEFAULT_FINDING_FIX_STRICTNESS,
    FINDING_FIX_STRICTNESS_CONTEXT_KEY,
    CriticVerdictEmittedPayload,
    FindingClosedPayload,
    FindingCreatedPayload,
    FindingFixStrictnessSettings,
    FindingRoutedPayload,
    GateDecisionEmittedPayload,
    GateOverriddenPayload,
    MemoryIndexedPayload,
    MemoryRetrievalEmittedPayload,
    ModelPreflightFailedPayload,
    ModelPreflightPassedPayload,
    ModelPreflightStartedPayload,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryPayload,
    PersonaShelfUpdatedPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEscalatedPayload,
    RunFailedPayload,
    RunStartedPayload,
    SelfRefinementLoopSignalledPayload,
    StageBlockedPayload,
    StageFailedPayload,
    StagePassedPayload,
    StageStartedPayload,
)

"""
        + records,
    )
    _write(
        REPO / "packages/agent_core/models/events.py",
        '''"""Event models — re-export facade."""

from agent_core.models.events_foundation import *  # noqa: F403
from agent_core.models.events_payloads import *  # noqa: F403
from agent_core.models.events_records import *  # noqa: F403
''',
    )


def split_scraper_artifacts() -> None:
    lines = _read("packages/nimbusware_orchestrator/scraper_artifacts.py")
    _write(REPO / "packages/nimbusware_orchestrator/scraper_artifacts_retention.py", "".join(lines[:81]))
    _write(
        REPO / "packages/nimbusware_orchestrator/scraper_artifacts_inventory.py",
        """from nimbusware_orchestrator.scraper_artifacts_retention import (
    RetentionAlertLevel,
    RetentionExecutionMode,
    StorageBackend,
    object_store_prune_enabled,
    retention_alert_level,
    retention_execution_mode,
)

"""
        + "".join(lines[81:315]),
    )
    _write(
        REPO / "packages/nimbusware_orchestrator/scraper_artifacts_prune.py",
        """from nimbusware_orchestrator.scraper_artifacts_inventory import (
    object_store_delete_artifact,
    scraper_artifact_storage_backend_signals,
)
from nimbusware_orchestrator.scraper_artifacts_retention import (
    object_store_prune_enabled,
    retention_alert_level,
    retention_execution_mode,
)

"""
        + "".join(lines[315:381])
        + "".join(lines[381:]),
    )
    _write(
        REPO / "packages/nimbusware_orchestrator/scraper_artifacts.py",
        '''"""On-disk scraper response artifact helpers."""

from nimbusware_orchestrator.scraper_artifacts_inventory import (
    object_store_delete_artifact,
    scraper_artifact_inventory,
    scraper_artifact_storage_backend_signals,
)
from nimbusware_orchestrator.scraper_artifacts_prune import (
    persist_scraper_artifact,
    prune_scraper_artifacts,
    prune_scraper_artifacts_local_removed,
    resolve_scraper_artifact_base_dir,
)
from nimbusware_orchestrator.scraper_artifacts_retention import (
    RetentionAlertLevel,
    RetentionExecutionMode,
    StorageBackend,
    object_store_prune_enabled,
    retention_alert_level,
    retention_execution_mode,
)
''',
    )


def split_openapi() -> None:
    lines = _read("packages/nimbusware_api/schemas/openapi.py")
    _write(
        REPO / "packages/nimbusware_api/schemas/openapi_problem.py",
        "".join(lines[:17])
        + "from nimbusware_api.schemas.problem import Problem\n\n"
        + "".join(lines[21:53]),
    )
    _write(
        REPO / "packages/nimbusware_api/schemas/openapi_link_helpers.py",
        "from __future__ import annotations\n\nfrom typing import Any\n\n"
        + "".join(lines[53:237]),
    )
    _write(
        REPO / "packages/nimbusware_api/schemas/openapi_route_docs.py",
        "from __future__ import annotations\n\nfrom typing import Any\n\n"
        + "from nimbusware_api.schemas.openapi_problem import _PROBLEM_JSON_CONTENT\n\n"
        + "".join(lines[237:]),
    )
    _write(
        REPO / "packages/nimbusware_api/schemas/openapi.py",
        '''"""Shared OpenAPI response fragments (facade)."""

from nimbusware_api.schemas.openapi_link_helpers import (
    RUN_DETAIL_LINK_HEADER,
    RUN_FINDINGS_LINK_HEADER,
    RUN_LIST_LINK_HEADER,
    RUN_TIMELINE_LINK_HEADER,
    RUN_TIMELINE_RESPONSE_200,
    format_run_detail_link_header,
    format_run_findings_link_header,
    format_run_timeline_link_header,
)
from nimbusware_api.schemas.openapi_problem import (
    PROBLEM_RESPONSE_401,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    PROBLEM_RESPONSE_503,
)
from nimbusware_api.schemas.openapi_route_docs import (
    BUNDLE_SEARCH_RESPONSE_200,
    CREATE_RUN_RESPONSE_200,
    CREATE_RUN_RESPONSE_422,
    PERSONA_ALREADY_EXISTS_409,
    PERSONA_DELETE_RESPONSE_204,
    PERSONA_UPSERT_RESPONSE_200,
    PERSONA_VERSION_CONFLICT_409,
    PERSONAS_RESPONSE_200,
    PREFLIGHT_HISTORY_RESPONSE_200,
    SCRAPER_ARTIFACT_INVENTORY_RESPONSE_200,
)
''',
    )


def main() -> None:
    split_events()
    split_scraper_artifacts()
    split_openapi()


if __name__ == "__main__":
    main()
