from __future__ import annotations

from pathlib import Path
from typing import Any

from extensions.self_refinement import (
    SelfRefinementPolicy,
    load_self_refinement_policy,
    self_refinement_policy_from_mapping,
)

_DEFAULT_POLICY = SelfRefinementPolicy(version=1, enabled=False, description="")


def resolve_self_refinement_policy(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> SelfRefinementPolicy:
    mat = config_materializer
    if mat is not None and getattr(mat, "use_db", False):
        try:
            return self_refinement_policy_from_mapping(mat.get_self_refinement_policy())
        except KeyError:
            return _DEFAULT_POLICY
    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    if path.is_file():
        return load_self_refinement_policy(path)
    return _DEFAULT_POLICY
