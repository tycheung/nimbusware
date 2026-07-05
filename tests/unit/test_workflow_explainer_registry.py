from __future__ import annotations

from pathlib import Path

from console.explainer_core.bootstrap import bootstrap_standard_explainer
from console.explainer_core.workflow_explainer_registry import (
    EXPORT_INSTALL_MARKER,
    WORKFLOW_EXPLAINER_SPECS,
    codegen_install_line,
)


def test_workflow_explainer_registry_has_seven_packages() -> None:
    assert len(WORKFLOW_EXPLAINER_SPECS) == 7
    slugs = {spec.slug for spec in WORKFLOW_EXPLAINER_SPECS}
    assert len(slugs) == 7


def test_workflow_explainer_package_dirs_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        assert (root / spec.package / "__init__.py").is_file()


def test_codegen_install_line_marker() -> None:
    line = codegen_install_line("agent_evaluator")
    assert EXPORT_INSTALL_MARKER in line
    assert 'install_package_workflow_explainer_exports(globals(), "agent_evaluator")' in line


def test_bootstrap_standard_explainer_carries_export_marker() -> None:
    bootstrap_path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "console"
        / "explainer_core"
        / "bootstrap.py"
    )
    assert EXPORT_INSTALL_MARKER in bootstrap_path.read_text(encoding="utf-8")


def test_workflow_explainer_inits_wire_exports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        text = (root / spec.package / "__init__.py").read_text(encoding="utf-8")
        compact = "".join(text.split())
        has_direct = (
            f'install_package_workflow_explainer_exports(globals(),"{spec.slug}")' in compact
        )
        has_bootstrap = f'bootstrap_standard_explainer("{spec.slug}",globals())' in compact
        assert has_direct or has_bootstrap, spec.slug
