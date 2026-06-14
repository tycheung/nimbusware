from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_IMPLEMENTATION_CRITIQUE_STAGE = "implementation.critique"
_TEST_WRITER_CRITIQUE_STAGE = "test_writer.critique"
_PLANNER_CRITIQUE_STAGE = "planner.critique"
_FRONTEND_WRITER_CRITIQUE_STAGE = "frontend_writer.critique"
_MODULE_INTEGRATOR_CRITIQUE_STAGE = "module_integrator.critique"

KNOWN_STAGE_GRAPH_STAGES: frozenset[str] = frozenset(
    {
        "plan",
        "implementation",
        "test_writer",
        "frontend_writer",
        "implementation.critique",
        _TEST_WRITER_CRITIQUE_STAGE,
        _PLANNER_CRITIQUE_STAGE,
        _FRONTEND_WRITER_CRITIQUE_STAGE,
        _MODULE_INTEGRATOR_CRITIQUE_STAGE,
        "bundle_compatibility",
        "scraper:fetch",
        "self_refinement:policy",
        "agent_evaluator.critique",
        "slice.plan",
        "slice.implement",
        "slice.verify",
        "slice.critique",
        "slice.test",
        "slice.e2e",
        "slice.gate",
        "launch_test.plan",
        "launch_test.write",
        "launch_test.critique",
        "dev_env.human_fidelity",
    },
)

_AGENT_EVALUATOR_CRITIQUE_STAGE = "agent_evaluator.critique"


@dataclass(frozen=True)
class StageNode:
    stage_name: str
    depends_on: tuple[str, ...] = ()
    parallel_group: str | None = None


@dataclass(frozen=True)
class StageGraph:
    nodes: tuple[StageNode, ...]


def default_stage_graph() -> StageGraph:
    """Sequential plan → writers (parallel-ready) → critique hooks → integrator gate."""
    return StageGraph(
        nodes=(
            StageNode("plan"),
            StageNode("implementation", depends_on=("plan",), parallel_group="writers"),
            StageNode("test_writer", depends_on=("plan",), parallel_group="writers"),
            StageNode("frontend_writer", depends_on=("plan",), parallel_group="writers"),
            StageNode(
                _IMPLEMENTATION_CRITIQUE_STAGE,
                depends_on=("implementation", "test_writer", "frontend_writer"),
            ),
            StageNode(_TEST_WRITER_CRITIQUE_STAGE, depends_on=(_IMPLEMENTATION_CRITIQUE_STAGE,)),
            StageNode(_PLANNER_CRITIQUE_STAGE, depends_on=(_TEST_WRITER_CRITIQUE_STAGE,)),
            StageNode(
                _FRONTEND_WRITER_CRITIQUE_STAGE,
                depends_on=(_PLANNER_CRITIQUE_STAGE,),
            ),
            StageNode(
                _MODULE_INTEGRATOR_CRITIQUE_STAGE,
                depends_on=(_FRONTEND_WRITER_CRITIQUE_STAGE,),
            ),
            StageNode("bundle_compatibility", depends_on=(_MODULE_INTEGRATOR_CRITIQUE_STAGE,)),
            StageNode(_AGENT_EVALUATOR_CRITIQUE_STAGE, depends_on=("bundle_compatibility",)),
        ),
    )


def stage_graph_from_workflow_profile(profile: Mapping[str, Any] | dict[str, Any]) -> StageGraph:
    """Parse optional top-level ``stage_graph`` list; absent key → :func:`default_stage_graph`."""
    raw = profile.get("stage_graph")
    if raw is None:
        return default_stage_graph()
    if not isinstance(raw, list):
        msg = "stage_graph must be a list"
        raise ValueError(msg)
    nodes: list[StageNode] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            msg = f"stage_graph[{idx}] must be an object"
            raise ValueError(msg)
        name_raw = item.get("stage_name")
        if not isinstance(name_raw, str) or not name_raw.strip():
            msg = f"stage_graph[{idx}] missing stage_name"
            raise ValueError(msg)
        deps_raw = item.get("depends_on", [])
        if deps_raw is None:
            deps: tuple[str, ...] = ()
        elif isinstance(deps_raw, list):
            deps = tuple(str(d).strip() for d in deps_raw if str(d).strip())
        else:
            msg = f"stage_graph[{idx}].depends_on must be a list"
            raise ValueError(msg)
        pg_raw = item.get("parallel_group")
        parallel_group = (
            str(pg_raw).strip() if isinstance(pg_raw, str) and str(pg_raw).strip() else None
        )
        nodes.append(
            StageNode(
                stage_name=name_raw.strip(),
                depends_on=deps,
                parallel_group=parallel_group,
            ),
        )
    return StageGraph(nodes=tuple(nodes))


def validate_stage_graph(graph: StageGraph, known_stages: frozenset[str]) -> None:
    """Raise ``ValueError`` on cycles, unknown stages, or duplicate stage names."""
    seen: set[str] = set()
    names: set[str] = set()
    for node in graph.nodes:
        if node.stage_name in seen:
            msg = f"duplicate stage_name in stage_graph: {node.stage_name!r}"
            raise ValueError(msg)
        seen.add(node.stage_name)
        names.add(node.stage_name)
    for node in graph.nodes:
        if node.stage_name not in known_stages:
            msg = f"unknown stage_name in stage_graph: {node.stage_name!r}"
            raise ValueError(msg)
        for dep in node.depends_on:
            if dep not in names:
                msg = f"stage_graph dependency {dep!r} not defined for stage {node.stage_name!r}"
                raise ValueError(msg)
            if dep not in known_stages:
                msg = f"unknown stage in depends_on: {dep!r}"
                raise ValueError(msg)
    topological_order(graph)


def topological_order(graph: StageGraph) -> list[str]:
    """Return stage names in dependency order; raise on cycle."""
    indegree: dict[str, int] = {n.stage_name: 0 for n in graph.nodes}
    adj: dict[str, list[str]] = {n.stage_name: [] for n in graph.nodes}
    for node in graph.nodes:
        for dep in node.depends_on:
            adj[dep].append(node.stage_name)
            indegree[node.stage_name] += 1
    queue: deque[str] = deque(name for name, deg in indegree.items() if deg == 0)
    ordered: list[str] = []
    while queue:
        cur = queue.popleft()
        ordered.append(cur)
        for nxt in adj[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(ordered) != len(graph.nodes):
        msg = "stage_graph contains a cycle"
        raise ValueError(msg)
    return ordered


def stage_graph_metadata_snapshot(graph: StageGraph) -> dict[str, Any]:
    """Freeze-safe ``run.created`` metadata payload for ``metadata.stage_graph``."""
    ordered = topological_order(graph)
    order_index = {name: idx for idx, name in enumerate(ordered)}
    parallel_groups: dict[str, list[str]] = {}
    nodes_out: list[dict[str, Any]] = []
    for node in graph.nodes:
        entry: dict[str, Any] = {
            "stage_name": node.stage_name,
            "depends_on": list(node.depends_on),
            "order_index": order_index[node.stage_name],
        }
        if node.parallel_group:
            entry["parallel_group"] = node.parallel_group
            parallel_groups.setdefault(node.parallel_group, []).append(node.stage_name)
        nodes_out.append(entry)
    return {
        "nodes": nodes_out,
        "ordered_stage_names": ordered,
        "parallel_groups": parallel_groups,
    }


def stage_graph_from_run_created_metadata(
    metadata: Mapping[str, Any] | dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(metadata, Mapping):
        return None
    raw = metadata.get("stage_graph")
    return raw if isinstance(raw, dict) else None


def stage_graph_node_lookup(snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    nodes = snapshot.get("nodes")
    if not isinstance(nodes, list):
        return lookup
    for item in nodes:
        if isinstance(item, dict):
            name = item.get("stage_name")
            if isinstance(name, str) and name.strip():
                lookup[name.strip()] = dict(item)
    return lookup


def event_metadata_for_stage(
    snapshot: Mapping[str, Any] | None,
    stage_name: str,
) -> dict[str, Any]:
    """Optional ``parallel_group`` / ``stage_graph_order_index`` for orchestration events."""
    if snapshot is None:
        return {}
    node = stage_graph_node_lookup(snapshot).get(stage_name)
    if not node:
        return {}
    meta: dict[str, Any] = {}
    pg = node.get("parallel_group")
    if isinstance(pg, str) and pg.strip():
        meta["parallel_group"] = pg.strip()
    oi = node.get("order_index")
    if isinstance(oi, int):
        meta["stage_graph_order_index"] = oi
    return meta


def parallel_group_members(
    snapshot: Mapping[str, Any],
    group_id: str,
) -> list[str]:
    """Stage names belonging to ``parallel_groups[group_id]`` (stable order)."""
    pg = snapshot.get("parallel_groups")
    if not isinstance(pg, dict):
        return []
    raw = pg.get(group_id)
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if isinstance(x, str) and str(x).strip()]


def stages_ready_for_parallel_group(
    snapshot: Mapping[str, Any],
    completed_stages: set[str] | frozenset[str],
    group_id: str,
) -> bool:
    """True when every stage in the group has all ``depends_on`` satisfied."""
    lookup = stage_graph_node_lookup(snapshot)
    for stage_name in parallel_group_members(snapshot, group_id):
        node = lookup.get(stage_name)
        if not node:
            continue
        deps = node.get("depends_on")
        if not isinstance(deps, list):
            continue
        for dep in deps:
            dep_key = str(dep).strip()
            if dep_key and dep_key not in completed_stages:
                return False
    return bool(parallel_group_members(snapshot, group_id))


def stage_graph_timeline_summary_from_metadata(
    metadata: Mapping[str, Any] | dict[str, Any],
) -> dict[str, Any] | None:
    """Compact timeline rollup from frozen ``run.created`` ``metadata.stage_graph``."""
    sg = stage_graph_from_run_created_metadata(metadata)
    if sg is None:
        return None
    ordered = sg.get("ordered_stage_names")
    if not isinstance(ordered, list):
        ordered = []
    ordered_names = [str(x) for x in ordered if isinstance(x, str) and str(x).strip()]
    parallel_groups = sg.get("parallel_groups")
    pg_count = len(parallel_groups) if isinstance(parallel_groups, dict) else 0
    return {
        "stage_count": len(ordered_names),
        "parallel_group_count": pg_count,
        "ordered_stage_names": ordered_names,
    }
