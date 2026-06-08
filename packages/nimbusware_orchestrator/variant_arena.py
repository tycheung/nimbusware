"""Competing implementation variant arena — worktrees and promotion."""

from __future__ import annotations

import shutil
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
