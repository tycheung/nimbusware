from __future__ import annotations

from pathlib import Path

from orchestrator.repo_intel.store import (
    build_code_intel_bundle,
    code_intel_path,
    load_code_intel,
    load_or_build_code_intel,
    persist_code_intel,
)


def test_code_intel_persist_and_load(tmp_path: Path) -> None:
    ws = tmp_path / "repo"
    pkg = ws / "packages" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "main.py").write_text("import demo.util\n", encoding="utf-8")
    (pkg / "util.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "orphan.py").write_text("UNUSED = 2\n", encoding="utf-8")

    path = persist_code_intel(ws, ws)
    assert path.is_file()
    assert path == code_intel_path(ws, ws)

    loaded = load_code_intel(ws, ws)
    assert loaded is not None
    assert loaded.get("version") == 2
    orphans = loaded.get("orphans")
    assert isinstance(orphans, dict)
    assert "orphan.py" in str(orphans.get("orphans"))

    cached = load_or_build_code_intel(ws, ws)
    assert cached.get("workspace") == str(ws.resolve())


def test_build_code_intel_route_reachability(tmp_path: Path) -> None:
    ws = tmp_path / "app"
    ws.mkdir()
    (ws / "main.py").write_text("import leaf\n", encoding="utf-8")
    (ws / "leaf.py").write_text("X = 1\n", encoding="utf-8")
    (ws / "isolated.py").write_text("Y = 2\n", encoding="utf-8")

    bundle = build_code_intel_bundle(ws)
    reach = bundle.get("route_reachability")
    assert isinstance(reach, dict)
    assert reach.get("reachable_module_count", 0) >= 1
    assert isinstance(reach.get("unreachable_count"), int)


def test_orphan_trap_fixture_detects_orphan(tmp_path: Path) -> None:
    import shutil

    src = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / "orphan_trap"
    ws = tmp_path / "orphan_trap"
    shutil.copytree(src, ws)
    bundle = build_code_intel_bundle(ws)
    orphans = bundle.get("orphans")
    assert isinstance(orphans, dict)
    orphan_list = orphans.get("orphans")
    assert isinstance(orphan_list, list)
    assert "orphan_trap.py" in orphan_list
    assert "used.py" not in orphan_list
    assert "main.py" not in orphan_list


def test_fastapi_routes_fixture_reachability(tmp_path: Path) -> None:
    import shutil

    src = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / "fastapi_routes"
    ws = tmp_path / "fastapi_routes"
    shutil.copytree(src, ws)
    bundle = build_code_intel_bundle(ws)
    reach = bundle.get("route_reachability")
    assert isinstance(reach, dict)
    reachable = reach.get("reachable_module_count", 0)
    assert reachable >= 2
    unreachable = reach.get("unreachable_modules") or []
    assert "isolated.py" in unreachable
    assert "routes/items.py" not in unreachable
    assert "app.py" in (reach.get("entry_modules") or [])
