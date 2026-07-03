from __future__ import annotations

from pathlib import Path

from orchestrator.integrator.dep_preflight import analyze_integrator_dep_conflicts


def test_analyze_integrator_dep_conflicts_missing(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\ndependencies = ["requests>=2.0"]\n',
        encoding="utf-8",
    )
    conflicts = analyze_integrator_dep_conflicts(
        pyproject_path=pyproject,
        bundle_meta={"required_packages": ["pandas", "requests"]},
    )
    names = {c["package"] for c in conflicts}
    assert "pandas" in names
    assert "requests" not in names
