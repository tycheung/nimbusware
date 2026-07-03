from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SimilarityCluster:
    hash: str
    paths: list[str] = field(default_factory=list)


@dataclass
class SimilarityIndex:
    clusters: list[SimilarityCluster] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clusters": [{"hash": c.hash, "paths": c.paths} for c in self.clusters],
            "duplicate_candidates": [c for c in self.clusters if len(c.paths) > 1],
        }


def _ast_hash(source: str) -> str:
    try:
        tree = ast.parse(source)
        dump = ast.dump(tree, include_attributes=False)
    except SyntaxError:
        dump = source
    return hashlib.sha256(dump.encode()).hexdigest()[:12]


def build_similarity_index(workspace: Path, *, max_files: int = 100) -> SimilarityIndex:
    buckets: dict[str, list[str]] = {}
    count = 0
    for path in sorted(workspace.rglob("*.py")):
        if count >= max_files:
            break
        if any(part.startswith(".") for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        h = _ast_hash(text)
        rel = str(path.relative_to(workspace))
        buckets.setdefault(h, []).append(rel)
        count += 1
    clusters = [SimilarityCluster(hash=h, paths=paths) for h, paths in buckets.items()]
    return SimilarityIndex(clusters=clusters)
