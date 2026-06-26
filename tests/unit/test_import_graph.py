from __future__ import annotations

import ast
from pathlib import Path


def _module_level_orchestrator_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("nimbusware_orchestrator"):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("nimbusware_orchestrator"):
                hits.append(mod)
    return hits


def test_extensions_has_no_module_level_orchestrator_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_extensions"
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        hits = _module_level_orchestrator_imports(path)
        if hits:
            offenders.append(f"{path.name}: {hits}")
    assert not offenders, "\n".join(offenders)


def _module_level_imports_matching(path: Path, prefix: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(prefix):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith(prefix):
                hits.append(mod)
    return hits


def test_orchestrator_has_no_module_level_api_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_orchestrator"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        hits = _module_level_imports_matching(path, "nimbusware_api")
        if hits:
            rel = path.relative_to(root)
            offenders.append(f"{rel}: {hits}")
    assert not offenders, "\n".join(offenders)


_LEGACY_SHIM_PREFIXES = (
    "hermes_api",
    "hermes_console",
    "hermes_config",
    "hermes_env",
)


def test_production_packages_do_not_import_legacy_hermes_shims() -> None:
    packages = Path(__file__).resolve().parents[2] / "packages"
    offenders: list[str] = []
    for path in sorted(packages.rglob("*.py")):
        rel_parts = path.relative_to(packages).parts
        if rel_parts[0] in _LEGACY_SHIM_PREFIXES:
            continue
        for prefix in _LEGACY_SHIM_PREFIXES:
            hits = _module_level_imports_matching(path, prefix)
            if hits:
                offenders.append(f"{path.relative_to(packages)}: {hits}")
    assert not offenders, "\n".join(offenders)


def test_legacy_hermes_shim_packages_removed() -> None:
    packages = Path(__file__).resolve().parents[2] / "packages"
    for name in _LEGACY_SHIM_PREFIXES:
        assert not (packages / name).is_dir(), f"remove legacy package: {name}"


def test_enterprise_console_uses_shared_http_client() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    service_path = root / "services" / "enterprise.py"
    text = service_path.read_text(encoding="utf-8")
    assert "import httpx" not in text
    assert "nimbusware_client.http" in text


def test_console_does_not_import_httpx_directly() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "import httpx" in text:
            rel = path.relative_to(root)
            offenders.append(str(rel))
    assert not offenders, "\n".join(offenders)


def test_run_detail_sections_do_not_star_import() -> None:
    root = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "nimbusware_console"
        / "pages"
        / "run_detail"
    )
    skip = {
        "_imports.py",
        "_imports_common.py",
        "_imports_display_a.py",
        "_imports_display_b.py",
    }
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8")
        if "from nimbusware_console.pages.run_detail._imports import *" in text:
            offenders.append(path.name)
    assert not offenders, "\n".join(offenders)


_MAKER_HTTPX_ALLOWLIST = frozenset({"readiness.py"})


def test_maker_slice_workflow_uses_slice_engine_boundary() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_maker"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel == "slice_engine.py":
            continue
        hits = _module_level_imports_matching(path, "nimbusware_orchestrator")
        if hits:
            offenders.append(f"{rel}: {hits}")
    assert not offenders, "\n".join(offenders)


def test_maker_does_not_import_httpx_directly() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_maker"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in _MAKER_HTTPX_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        if "import httpx" in text:
            offenders.append(rel)
    assert not offenders, "\n".join(offenders)


def test_api_runs_use_projections_run_summary() -> None:
    api_runs = (
        Path(__file__).resolve().parents[2] / "packages" / "nimbusware_api" / "routes" / "runs"
    )
    offenders: list[str] = []
    for path in sorted(api_runs.glob("*.py")):
        hits = _module_level_imports_matching(path, "nimbusware_orchestrator.read_models")
        if hits:
            offenders.append(f"{path.name}: {hits}")
    assert not offenders, "\n".join(offenders)


_WORKFLOW_EXPLAINER_ORCHESTRATOR_ALLOWLIST = frozenset(
    {
        "integrator_threshold_explainer.py",  # integrator gate emission helpers
    },
)


_PROJECTIONS_ORCHESTRATOR_ALLOWLIST = frozenset()


def test_projections_has_no_module_level_orchestrator_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_projections"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in _PROJECTIONS_ORCHESTRATOR_ALLOWLIST:
            continue
        hits = _module_level_imports_matching(path, "nimbusware_orchestrator")
        if hits:
            offenders.append(f"{rel}: {hits}")
    assert not offenders, "\n".join(offenders)


def test_workflow_explainers_use_config_workflow_read_facade() -> None:
    root = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "nimbusware_console"
        / "workflow_explainers"
    )
    offenders: list[str] = []
    for path in sorted(root.glob("*/payload.py")):
        hits = [
            mod
            for mod in _module_level_imports_matching(path, "nimbusware_orchestrator")
            if mod
            not in {
                "nimbusware_orchestrator.integrator_gate",
                "nimbusware_orchestrator.integration_adapter_writer_stage",
                "nimbusware_orchestrator.workflow_integration_adapter_writer",
            }
        ]
        if hits:
            offenders.append(f"{path.name}: {hits}")
    assert not offenders, "\n".join(offenders)
