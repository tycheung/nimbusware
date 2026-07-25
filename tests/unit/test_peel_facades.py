from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Post sak412: tools/runtime/agent_loop inventory paths deleted — assert facades instead.
SHELL_TOOLS_PY = ROOT / "packages" / "agent_tools" / "shell_tools.py"
RUNTIME_FACADE_PY = ROOT / "packages" / "agent_tools" / "runtime_facade.py"
LLM_BROKER_PY = ROOT / "packages" / "agent_tools" / "facades" / "llm_broker.py"
STAGES_PY = ROOT / "packages" / "research" / "stages.py"
STAGE_BUILDER_PY = ROOT / "packages" / "research" / "stage_builder.py"


def _orchestrator_import_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "orchestrator" or alias.name.startswith("orchestrator."):
                    mods.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "orchestrator" or mod.startswith("orchestrator."):
                mods.append(mod)
    return mods


def test_shell_tools_py_has_no_direct_orchestrator_imports() -> None:
    mods = _orchestrator_import_modules(SHELL_TOOLS_PY)
    assert mods == [], f"shell_tools.py still imports orchestrator: {mods}"


def test_runtime_facade_py_has_no_orchestrator_llm_imports() -> None:
    mods = _orchestrator_import_modules(RUNTIME_FACADE_PY)
    hits = [m for m in mods if m.startswith("orchestrator.llm")]
    assert hits == [], f"runtime_facade.py still imports orchestrator.llm: {hits}"


def test_llm_broker_facade_only_uses_llm_facades() -> None:
    mods = _orchestrator_import_modules(LLM_BROKER_PY)
    allowed = {
        "orchestrator.llm.chat_facade",
        "orchestrator.llm.slice_facade",
        "orchestrator.llm.broker_bridge",
    }
    hits = [m for m in mods if m not in allowed]
    assert hits == [], f"llm_broker.py unexpected orchestrator imports: {hits}"


def test_inventory_thin_paths_removed() -> None:
    for rel in (
        "packages/agent_tools/tools.py",
        "packages/agent_tools/runtime.py",
        "packages/agent_tools/agent_loop.py",
        "packages/agent_tools/facades/llm.py",
    ):
        assert not (ROOT / rel).exists(), f"inventory path still present: {rel}"


def test_stages_py_has_no_direct_orchestrator_registry_import() -> None:
    mods = _orchestrator_import_modules(STAGES_PY)
    assert "orchestrator.registry" not in mods


def test_stages_py_has_no_orchestrator_llm_common_import() -> None:
    mods = _orchestrator_import_modules(STAGES_PY)
    hits = [m for m in mods if m.startswith("orchestrator.llm")]
    assert hits == [], f"stages.py still imports orchestrator.llm: {hits}"


def test_stage_builder_py_has_no_orchestrator_repo_intel_import() -> None:
    mods = _orchestrator_import_modules(STAGE_BUILDER_PY)
    hits = [m for m in mods if m.startswith("orchestrator.repo_intel")]
    assert hits == [], f"stage_builder.py still imports orchestrator.repo_intel: {hits}"
