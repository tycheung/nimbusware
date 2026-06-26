from __future__ import annotations

from pathlib import Path

from nimbusware_console.explainer_core.workflow_explainer_registry import (
    EXPORT_INSTALL_MARKER,
    WORKFLOW_EXPLAINER_SPECS,
    codegen_install_line,
)


def test_workflow_explainer_registry_has_seven_packages() -> None:
    assert len(WORKFLOW_EXPLAINER_SPECS) == 7
    slugs = {spec.slug for spec in WORKFLOW_EXPLAINER_SPECS}
    assert len(slugs) == 7


def test_workflow_explainer_package_dirs_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        assert (root / spec.package / "__init__.py").is_file()


def test_codegen_install_line_marker() -> None:
    line = codegen_install_line("agent_evaluator")
    assert EXPORT_INSTALL_MARKER in line
    assert 'install_package_workflow_explainer_exports(globals(), "agent_evaluator")' in line


def test_workflow_explainer_inits_include_export_install_line() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        text = (root / spec.package / "__init__.py").read_text(encoding="utf-8")
        assert EXPORT_INSTALL_MARKER in text
        compact = "".join(text.split())
        assert f'install_package_workflow_explainer_exports(globals(),"{spec.slug}")' in compact
