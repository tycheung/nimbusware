from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.repo_inventory import RepoInventory, build_repo_inventory


@dataclass(frozen=True)
class FeatureGapMatrix:
    backlog_ready: int
    modules_built: int
    tests_present: int
    ism_surfaces: int
    gaps: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backlog_ready": self.backlog_ready,
            "modules_built": self.modules_built,
            "tests_present": self.tests_present,
            "ism_surfaces": self.ism_surfaces,
            "gaps": list(self.gaps),
        }

    @property
    def has_implement_gap(self) -> bool:
        return "backlog_ready" in self.gaps or "breadth_lag" in self.gaps


def _count_py_tests(workspace: Path) -> tuple[int, int]:
    py_files = [p for p in workspace.rglob("*.py") if ".venv" not in p.parts]
    tests = [
        p
        for p in py_files
        if p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts
    ]
    return len(py_files), len(tests)


def _backlog_ready_count(workspace: Path) -> int:
    backlog = workspace / ".nimbusware" / "campaign" / "backlog.json"
    if not backlog.is_file():
        return 0
    try:
        import json

        raw = json.loads(backlog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    slices = raw.get("slices") if isinstance(raw, dict) else raw
    if not isinstance(slices, list):
        return 0
    return sum(
        1
        for row in slices
        if isinstance(row, dict) and str(row.get("status", "ready")).lower() in ("ready", "queued")
    )


def build_feature_gap_matrix(
    workspace: Path, *, inventory: RepoInventory | None = None
) -> FeatureGapMatrix:
    ws = workspace.resolve()
    inv = inventory or build_repo_inventory(ws)
    py_count, test_count = _count_py_tests(ws)
    backlog_ready = _backlog_ready_count(ws)
    ism_path = ws / ".nimbusware" / "ism" / "surfaces.json"
    ism_surfaces = 0
    if ism_path.is_file():
        try:
            import json

            loaded = json.loads(ism_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                ism_surfaces = len(loaded)
            elif isinstance(loaded, dict):
                ism_surfaces = len(loaded.get("surfaces") or [])
        except (OSError, json.JSONDecodeError):
            ism_surfaces = 0
    gaps: list[str] = []
    if backlog_ready > 0:
        gaps.append("backlog_ready")
    if inv.feature_breadth > 0 and ism_surfaces < max(1, inv.feature_breadth // 4):
        gaps.append("breadth_lag")
    if py_count > 4 and test_count < max(1, py_count // 5):
        gaps.append("coverage_gap")
    if inv.orphan_count > 2:
        gaps.append("orphan_modules")
    return FeatureGapMatrix(
        backlog_ready=backlog_ready,
        modules_built=inv.feature_breadth,
        tests_present=test_count,
        ism_surfaces=ism_surfaces,
        gaps=tuple(gaps),
    )
