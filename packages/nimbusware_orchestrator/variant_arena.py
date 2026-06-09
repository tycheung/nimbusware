"""Competing implementation variant arena — worktrees and promotion."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class VariantCandidate:
    variant_id: str
    label: str
    workspace: Path
    fitness: float = 0.0


@dataclass
class VariantArenaResult:
    candidates: list[VariantCandidate] = field(default_factory=list)
    winner: VariantCandidate | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [
                {"variant_id": c.variant_id, "label": c.label, "fitness": c.fitness}
                for c in self.candidates
            ],
            "winner": (
                {
                    "variant_id": self.winner.variant_id,
                    "label": self.winner.label,
                    "fitness": self.winner.fitness,
                }
                if self.winner
                else None
            ),
        }


def create_variant_worktree(base_workspace: Path, tmp_root: Path, label: str) -> VariantCandidate:
    vid = str(uuid4())[:8]
    dest = tmp_root / f"variant_{vid}"
    shutil.copytree(base_workspace, dest, dirs_exist_ok=True)
    return VariantCandidate(variant_id=vid, label=label, workspace=dest)


def _count_py_lines(workspace: Path) -> int:
    total = 0
    for path in workspace.rglob("*.py"):
        if ".nimbusware" in path.parts or "node_modules" in path.parts:
            continue
        try:
            total += sum(1 for _ in path.open(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return total


def measure_variant_fitness(
    candidate: VariantCandidate,
    base_workspace: Path,
    *,
    timeout_seconds: float = 60.0,
) -> tuple[bool, int]:
    tests_passed = True
    tests_dir = candidate.workspace / "tests"
    if tests_dir.is_dir():
        proc = subprocess.run(
            ["python", "-m", "pytest", "tests", "-q", "--tb=no", "-x"],
            cwd=candidate.workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        tests_passed = proc.returncode == 0
    loc_delta = max(0, _count_py_lines(candidate.workspace) - _count_py_lines(base_workspace))
    return tests_passed, loc_delta


def score_variant(candidate: VariantCandidate, *, tests_passed: bool, loc_delta: int) -> float:
    score = 1.0 if tests_passed else 0.0
    score -= max(0, loc_delta) * 0.001
    candidate.fitness = round(score, 4)
    return candidate.fitness


def promote_winner(candidates: list[VariantCandidate]) -> VariantArenaResult:
    if not candidates:
        return VariantArenaResult()
    winner = max(candidates, key=lambda c: c.fitness)
    return VariantArenaResult(candidates=candidates, winner=winner)


def run_variant_arena(
    workspace: Path,
    tmp_root: Path,
    *,
    max_candidates: int = 1,
) -> VariantArenaResult:
    """Score up to four competing worktrees (operator gate at autopilot ≥6)."""
    count = max(1, min(4, int(max_candidates)))
    tmp_root.mkdir(parents=True, exist_ok=True)
    candidates: list[VariantCandidate] = []
    for index in range(count):
        candidate = create_variant_worktree(workspace, tmp_root, label=f"variant_{index + 1}")
        tests_passed, loc_delta = measure_variant_fitness(candidate, workspace)
        score_variant(candidate, tests_passed=tests_passed, loc_delta=loc_delta)
        candidates.append(candidate)
    return promote_winner(candidates)


def promote_variant_to_workspace(winner: VariantCandidate, target_workspace: Path) -> bool:
    if not winner.workspace.is_dir() or not target_workspace.is_dir():
        return False
    for path in winner.workspace.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(winner.workspace)
        if ".nimbusware" in rel.parts or "node_modules" in rel.parts:
            continue
        dest = target_workspace / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return True
