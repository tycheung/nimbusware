from __future__ import annotations

from pathlib import Path

from nimbusware_console.explainer_core.workflow_explainer_registry import (
    CODEGEN_BLOCK_END,
    CODEGEN_BLOCK_START,
    WORKFLOW_EXPLAINER_SPECS,
    codegen_install_block,
)


def test_workflow_explainer_registry_has_seven_packages() -> None:
    assert len(WORKFLOW_EXPLAINER_SPECS) == 7
    slugs = {spec.slug for spec in WORKFLOW_EXPLAINER_SPECS}
    assert len(slugs) == 7


def test_workflow_explainer_package_dirs_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        assert (root / spec.package / "__init__.py").is_file()


def test_codegen_install_block_markers() -> None:
    block = codegen_install_block("agent_evaluator")
    assert CODEGEN_BLOCK_START in block
    assert CODEGEN_BLOCK_END in block
    assert 'install_package_workflow_explainer_exports(globals(), "agent_evaluator")' in block


def test_workflow_explainer_inits_include_codegen_block() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        text = (root / spec.package / "__init__.py").read_text(encoding="utf-8")
        assert CODEGEN_BLOCK_START in text
        assert CODEGEN_BLOCK_END in text
        assert codegen_install_block(spec.slug).strip() in text
