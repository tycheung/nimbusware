from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.code_graph import build_code_graph


@dataclass
class OrphanReport:
    orphans: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"orphans": self.orphans, "count": len(self.orphans)}


def build_orphan_report(workspace: Path) -> OrphanReport:
    graph = build_code_graph(workspace)
    modules = {n.path for n in graph.nodes if n.kind == "module"}
    imported = {tgt for _src, tgt in graph.import_edges if not tgt.startswith("import:")}
    referenced = imported | {e[0] for e in graph.edges}
    orphans = sorted(m for m in modules if m not in referenced and not m.endswith("__init__.py"))
    return OrphanReport(orphans=orphans[:50])
