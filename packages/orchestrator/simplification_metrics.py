from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComplexityIndex:
    file_count: int
    loc: int
    avg_loc_per_file: float

    @classmethod
    def from_workspace(cls, workspace: Path, *, suffix: str = ".py") -> ComplexityIndex:
        ws = workspace.resolve()
        loc = 0
        files = 0
        for path in ws.rglob(f"*{suffix}"):
            if any(part.startswith(".") for part in path.parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            files += 1
            loc += len(lines)
        avg = (loc / files) if files else 0.0
        return cls(file_count=files, loc=loc, avg_loc_per_file=round(avg, 2))


def simplicity_score(index: ComplexityIndex) -> float:
    if index.loc == 0:
        return 10.0
    penalty = min(9.0, index.avg_loc_per_file / 50.0)
    return round(max(1.0, 10.0 - penalty), 2)
