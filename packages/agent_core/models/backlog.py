from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EpicStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class SliceStatus(str, Enum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEFERRED = "deferred"


class BacklogSlice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slice_id: str = Field(min_length=1, max_length=128)
    status: SliceStatus = SliceStatus.PENDING
    target_paths: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    estimated_loc: int = Field(default=0, ge=0, le=10_000)
    rationale: str = Field(default="", max_length=2000)


class BacklogFeature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    feature_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    acceptance_criteria: tuple[str, ...] = ()
    slices: tuple[BacklogSlice, ...] = ()


class BacklogEpic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    epic_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    status: EpicStatus = EpicStatus.PENDING
    features: tuple[BacklogFeature, ...] = ()


class CompletionCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    require_all_must_have_features: bool = True
    require_project_tests_pass: bool = True
    require_no_high_findings: bool = True
    allow_deferred_epics: bool = True


class BacklogMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_slices_planned: int = Field(default=0, ge=0)
    slices_completed: int = Field(default=0, ge=0)
    last_architecture_pass_at_slice: int = Field(default=0, ge=0)
    last_refactor_pass_at_slice: int = Field(default=0, ge=0)
    generator_mode: Literal["stub", "heuristic", "llm"] = "heuristic"


class DeliveryBacklog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    campaign_id: str = Field(min_length=1, max_length=36)
    source_requirements_id: str | None = Field(default=None, max_length=36)
    epics: tuple[BacklogEpic, ...] = ()
    completion_criteria: CompletionCriteria = Field(default_factory=CompletionCriteria)
    metadata: BacklogMetadata = Field(default_factory=BacklogMetadata)


class CampaignPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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


def count_backlog_slices(backlog: DeliveryBacklog) -> int:
    return sum(len(f.slices) for epic in backlog.epics for f in epic.features)


def sync_backlog_metadata(backlog: DeliveryBacklog) -> DeliveryBacklog:
    total = count_backlog_slices(backlog)
    if backlog.metadata.total_slices_planned == total:
        return backlog
    return backlog.model_copy(
        update={
            "metadata": backlog.metadata.model_copy(
                update={"total_slices_planned": total},
            ),
        },
    )


def backlog_slice_ids(backlog: DeliveryBacklog) -> list[str]:
    ids: list[str] = []
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                ids.append(sl.slice_id)
    return ids


def backlog_dependency_graph(backlog: DeliveryBacklog) -> dict[str, tuple[str, ...]]:
    graph: dict[str, tuple[str, ...]] = {}
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                graph[sl.slice_id] = sl.depends_on
    return graph


def validate_backlog_dag(backlog: DeliveryBacklog) -> list[str]:
    graph = backlog_dependency_graph(backlog)
    known = set(graph.keys())
    errors: list[str] = []

    for sid, deps in graph.items():
        for dep in deps:
            if dep not in known:
                errors.append(f"slice {sid!r} depends on unknown slice {dep!r}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = " -> ".join(stack + [node])
            errors.append(f"dependency cycle: {cycle}")
            return
        visiting.add(node)
        for dep in graph.get(node, ()):
            visit(dep, stack + [node])
        visiting.discard(node)
        visited.add(node)

    for sid in graph:
        visit(sid, [])

    return errors
