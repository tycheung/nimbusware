from __future__ import annotations

from pathlib import Path

from orchestrator.repo_intel.graph_tools import list_module_deps, run_graph_tool


def test_list_module_deps(tmp_path: Path) -> None:
    mod = tmp_path / "pkg" / "app.py"
    mod.parent.mkdir()
    mod.write_text(
        "import os\nfrom pathlib import Path\nimport httpx\n",
        encoding="utf-8",
    )
    result = list_module_deps(tmp_path, "pkg/app.py")
    assert result.ok
    assert "os" in result.data["dependencies"]
    assert "pathlib" in result.data["dependencies"]
    assert "httpx" in result.data["dependencies"]


def test_run_graph_tool_list_module_deps(tmp_path: Path) -> None:
    mod = tmp_path / "m.py"
    mod.write_text("import json\n", encoding="utf-8")
    result = run_graph_tool(tmp_path, "list_module_deps", path="m.py")
    assert result.ok
    assert result.tool == "list_module_deps"
