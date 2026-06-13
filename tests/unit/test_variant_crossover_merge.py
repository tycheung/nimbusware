from __future__ import annotations

import shutil
from pathlib import Path

from nimbusware_orchestrator.variant_arena import (
    VariantCandidate,
    merge_variant_crossover,
    select_promotion_candidate,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_merge_variant_crossover_combines_disjoint_edits(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    _write(base / "shared.py", "base\n")
    _write(base / "only_a.py", "a0\n")

    var_a = tmp_path / "a"
    var_b = tmp_path / "b"
    shutil.copytree(base, var_a, dirs_exist_ok=True)
    shutil.copytree(base, var_b, dirs_exist_ok=True)
    _write(var_a / "only_a.py", "a1\n")
    _write(var_b / "only_b.py", "b1\n")

    candidate_a = VariantCandidate(variant_id="a", label="a", workspace=var_a, fitness=0.9)
    candidate_b = VariantCandidate(variant_id="b", label="b", workspace=var_b, fitness=0.8)
    merged = merge_variant_crossover(base, candidate_a, candidate_b, tmp_path / "out")

    assert (merged / "only_a.py").read_text(encoding="utf-8") == "a1\n"
    assert (merged / "only_b.py").read_text(encoding="utf-8") == "b1\n"
    assert (merged / "shared.py").read_text(encoding="utf-8") == "base\n"


def test_merge_variant_crossover_prefers_higher_fitness_on_conflict(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    _write(base / "conflict.py", "base\n")

    var_a = tmp_path / "a"
    var_b = tmp_path / "b"
    shutil.copytree(base, var_a, dirs_exist_ok=True)
    shutil.copytree(base, var_b, dirs_exist_ok=True)
    _write(var_a / "conflict.py", "from_a\n")
    _write(var_b / "conflict.py", "from_b\n")

    candidate_a = VariantCandidate(variant_id="a", label="a", workspace=var_a, fitness=0.95)
    candidate_b = VariantCandidate(variant_id="b", label="b", workspace=var_b, fitness=0.7)
    merged = merge_variant_crossover(base, candidate_a, candidate_b, tmp_path / "out")

    assert (merged / "conflict.py").read_text(encoding="utf-8") == "from_a\n"


def test_select_promotion_candidate_picks_crossover_when_fitter(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    _write(base / "a.py", "base\n")

    var_a = tmp_path / "a"
    var_b = tmp_path / "b"
    shutil.copytree(base, var_a, dirs_exist_ok=True)
    shutil.copytree(base, var_b, dirs_exist_ok=True)
    _write(var_a / "a.py", "a_only\n")
    _write(var_b / "b.py", "b_only\n")

    candidate_a = VariantCandidate(variant_id="a", label="a", workspace=var_a, fitness=0.91)
    candidate_b = VariantCandidate(variant_id="b", label="b", workspace=var_b, fitness=0.9)
    picked, merged, paths = select_promotion_candidate(
        base,
        [candidate_a, candidate_b],
        tmp_path / "out",
    )
    assert picked is not None
    assert merged is True
    assert paths
    assert picked.label.startswith("crossover_")
