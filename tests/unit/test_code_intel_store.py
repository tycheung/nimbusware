from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.code_intel_store import (
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
    assert loaded.get("version") == 1
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
