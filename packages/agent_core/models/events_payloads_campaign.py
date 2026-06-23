from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from agent_core.models.events_payloads_base import BasePayload


class ResearchBriefSourcePayload(BasePayload):
    url: str = Field(min_length=1, max_length=2048)
    license: str = Field(min_length=1, max_length=64)
    trust_tier: Literal["high", "medium", "low"] = "medium"


class ResearchBriefEmittedPayload(BasePayload):
    brief_kind: Literal["domain", "code"]
    domain_tag: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=8000)
    artifact_id: str = Field(min_length=1, max_length=128)
    sources: list[ResearchBriefSourcePayload] = Field(default_factory=list, max_length=20)


class ResearchBriefReviewPayload(BasePayload):
    artifact_id: str = Field(min_length=1, max_length=128)
    brief_kind: Literal["domain", "code"]
    notes: str = Field(default="", max_length=2000)


class ResearchPatternIndexedPayload(BasePayload):
    pattern_id: str = Field(min_length=1, max_length=128)
    repo_url: str = Field(min_length=1, max_length=2048)
    paths: list[str] = Field(default_factory=list, max_length=40)
    license: str = Field(min_length=1, max_length=64)
    embedding_ref: str = Field(min_length=1, max_length=128)


class DomainCriticProposedPayload(BasePayload):
    critic_template: str = Field(min_length=1, max_length=256)
    allowed_domains: list[str] = Field(default_factory=list, max_length=16)
    blocking_authority: Literal["ADVISORY", "BLOCKING"] = "ADVISORY"
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)


class StitchLicenseCheckedPayload(BasePayload):
    detected_licenses: list[str] = Field(default_factory=list, max_length=16)
    allowlist: list[str] = Field(default_factory=list, max_length=16)
    passed: bool
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)


class StitchDependencyCheckedPayload(BasePayload):
    declared_deps: list[str] = Field(default_factory=list, max_length=40)
    new_deps: list[str] = Field(default_factory=list, max_length=20)
    max_allowed: int = Field(ge=0, le=50)
    passed: bool
    reason_code: str | None = Field(default=None, max_length=64)


class StitchPlanEmittedPayload(BasePayload):
    target_paths: list[str] = Field(default_factory=list, max_length=40)
    source_manifest_id: str = Field(min_length=1, max_length=128)
    wiring_delta_summary: str = Field(min_length=1, max_length=4000)


class StitchAppliedPayload(BasePayload):
    snapshot_ref: str = Field(min_length=1, max_length=256)
    files_added: list[str] = Field(default_factory=list, max_length=40)
    deps_added: list[str] = Field(default_factory=list, max_length=20)


class StitchFailedPayload(BasePayload):
    reason_code: str = Field(min_length=1, max_length=64)
    rollback_snapshot_ref: str | None = Field(default=None, max_length=256)


class CampaignPolicyPayload(BasePayload):
    autonomous: bool = True
    max_slices: int = Field(default=500, ge=1, le=5000)
    max_campaign_duration_hours: int = Field(default=72, ge=1, le=720)
    max_consecutive_slice_failures: int = Field(default=5, ge=1, le=50)
    refactor_every_n_slices: int = Field(default=5, ge=1, le=500)
    architecture_every_n_slices: int = Field(default=10, ge=1, le=500)
    deep_eval_every_n_slices: int = Field(default=20, ge=1, le=500)
    tick_idle_seconds: float = Field(default=2.0, ge=0.0, le=300.0)
    backlog_generator: Literal["stub", "heuristic", "llm"] = "heuristic"
    require_backlog_approval: bool = False


class CampaignCreatedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    workflow_profile: str = Field(min_length=1, max_length=128)
    policy: CampaignPolicyPayload


class CampaignCompletedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    slices_completed: int = Field(ge=0)
    epics_completed: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=4000)


class CampaignFailedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    reason_code: str = Field(min_length=1, max_length=64)
    summary: str = Field(default="", max_length=4000)


class CampaignPausedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    reason_code: str = Field(min_length=1, max_length=64)
    operator_initiated: bool = False


class DeliveryBacklogGeneratedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    backlog: dict[str, Any] = Field(description="Serialized DeliveryBacklog JSON")
    generator_mode: Literal["stub", "heuristic", "llm"] = "heuristic"


class DeliveryBacklogRevisedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    revision_reason: str = Field(min_length=1, max_length=512)
    backlog: dict[str, Any] = Field(description="Revised DeliveryBacklog JSON")


class EpicStatusChangedPayload(BasePayload):
    epic_id: str = Field(min_length=1, max_length=128)
    old_status: str = Field(min_length=1, max_length=32)
    new_status: str = Field(min_length=1, max_length=32)


class SliceQueuedPayload(BasePayload):
    slice_id: str = Field(min_length=1, max_length=128)
    backlog_slice_id: str = Field(min_length=1, max_length=128)
    epic_id: str = Field(min_length=1, max_length=128)


class SliceDeferredPayload(BasePayload):
    slice_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class MaintenanceRefactorStartedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    after_slice_count: int = Field(ge=0)


class MaintenanceRefactorPassedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    fix_slices_queued: int = Field(default=0, ge=0)


class MaintenanceArchitectureStartedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    after_slice_count: int = Field(ge=0)


class MaintenanceArchitecturePassedPayload(BasePayload):
    campaign_id: str = Field(min_length=1, max_length=36)
    backlog_revised: bool = False


class CompletionEvaluatedPayload(BasePayload):
    verdict: Literal["PASS", "FAIL", "INCOMPLETE"]
    remaining_epics: list[str] = Field(default_factory=list, max_length=50)
    blocking_findings: list[str] = Field(default_factory=list, max_length=20)
    rationale: str = Field(default="", max_length=4000)
