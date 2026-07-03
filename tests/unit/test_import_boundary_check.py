from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "ci" / "import_boundary_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("import_boundary_check", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["import_boundary_check"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def boundary_mod():
    return _load_module()


def test_module_level_import_prefixes_detects_orchestrator(boundary_mod, tmp_path: Path) -> None:
    path = tmp_path / "routes.py"
    path.write_text(
        "from orchestrator.pipeline import RunOrchestrator\n\n"
        "def handler():\n"
        "    from orchestrator.other import x\n",
        encoding="utf-8",
    )
    hits = boundary_mod.module_level_import_prefixes(path, "orchestrator")
    assert hits == ["orchestrator.pipeline"]


def test_module_level_import_prefixes_detects_api(boundary_mod, tmp_path: Path) -> None:
    path = tmp_path / "stage.py"
    path.write_text("import api.routes.runs\n", encoding="utf-8")
    hits = boundary_mod.module_level_import_prefixes(path, "api")
    assert hits == ["api.routes.runs"]


def test_collect_violations_clean_tree(boundary_mod, tmp_path: Path) -> None:
    orch_root = tmp_path / "orchestrator"
    orch_root.mkdir()
    (orch_root / "pipeline.py").write_text(
        "from agent_core.events import Event\n", encoding="utf-8"
    )
    assert boundary_mod.collect_violations(orchestrator_root=orch_root) == []


def test_collect_violations_api_imports_orchestrator_allowed(boundary_mod, tmp_path: Path) -> None:
    api_root = tmp_path / "api"
    orch_root = tmp_path / "orchestrator"
    api_root.mkdir(parents=True)
    orch_root.mkdir()
    (api_root / "deps.py").write_text("from orchestrator.pipeline import X\n", encoding="utf-8")
    assert boundary_mod.collect_violations(orchestrator_root=orch_root) == []


def test_collect_violations_orchestrator_imports_api(boundary_mod, tmp_path: Path) -> None:
    orch_root = tmp_path / "orchestrator"
    orch_root.mkdir(parents=True)
    (orch_root / "helper.py").write_text("from api.deps import get_db\n", encoding="utf-8")
    violations = boundary_mod.collect_violations(orchestrator_root=orch_root)
    assert len(violations) == 1
    assert "orchestrator/helper.py" in violations[0]
    assert "api.deps" in violations[0]


def test_main_exits_zero_when_clean(
    boundary_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orch_root = tmp_path / "packages" / "orchestrator"
    orch_root.mkdir(parents=True)
    (orch_root / "ok.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(boundary_mod, "ORCHESTRATOR_ROOT", orch_root)
    assert boundary_mod.main() == 0


def test_main_exits_one_on_violation(
    boundary_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orch_root = tmp_path / "packages" / "orchestrator"
    orch_root.mkdir(parents=True)
    (orch_root / "bad.py").write_text("from api.deps import get_db\n", encoding="utf-8")
    monkeypatch.setattr(boundary_mod, "ORCHESTRATOR_ROOT", orch_root)
    assert boundary_mod.main() == 1
