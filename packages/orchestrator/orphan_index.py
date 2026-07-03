from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.code_graph import CodeGraphIndex, build_code_graph
from orchestrator.code_intel_entrypoints import (
    discover_entrypoint_modules,
    discover_test_seed_modules,
)


@dataclass
class OrphanReport:
    orphans: list[str] = field(default_factory=list)
    orphan_metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "orphans": self.orphans,
            "count": len(self.orphans),
            "orphan_metadata": dict(self.orphan_metadata),
        }


def _include_tests() -> bool:
    import os

    return os.environ.get("NIMBUSWARE_CODE_INTEL_INCLUDE_TESTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def build_orphan_report(
    workspace: Path,
    *,
    graph: CodeGraphIndex | None = None,
    entry_modules: list[str] | None = None,
) -> OrphanReport:
    graph = graph or build_code_graph(workspace)
    modules = {n.path for n in graph.nodes if n.kind == "module"}
    imported = {tgt for _src, tgt in graph.import_edges if not tgt.startswith("import:")}
    referenced = imported | {e[0] for e in graph.edges}
    entries = set(entry_modules or discover_entrypoint_modules(workspace))
    referenced |= entries
    if _include_tests():
        referenced |= discover_test_seed_modules(workspace)

    orphans: list[str] = []
    metadata: dict[str, str] = {}
    for mod in sorted(modules):
        if mod.endswith("__init__.py"):
            continue
        if mod in referenced:
            continue
        orphans.append(mod)
        metadata[mod] = "not_referenced_from_imports_or_entrypoints"
        if len(orphans) >= 50:
            break
    return OrphanReport(orphans=orphans, orphan_metadata=metadata)
