from __future__ import annotations

import re
from pathlib import Path

from console.explainer_core.workflow_explainer_registry import (
    EXPORT_INSTALL_MARKER,
    WORKFLOW_EXPLAINER_SPECS,
    codegen_install_line,
)


def _has_install_line(text: str, slug: str) -> bool:
    pattern = (
        rf"install_package_workflow_explainer_exports\s*\(\s*globals\(\)\s*,\s*"
        rf'"{re.escape(slug)}"\s*\)\s*{re.escape(EXPORT_INSTALL_MARKER)}'
    )
    return bool(re.search(pattern, text, re.DOTALL))


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


def test_workflow_explainer_inits_wire_exports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "console"
    for spec in WORKFLOW_EXPLAINER_SPECS:
        text = (root / spec.package / "__init__.py").read_text(encoding="utf-8")
        compact = "".join(text.split())
        has_direct = _has_install_line(text, spec.slug)
        has_bootstrap = f'bootstrap_standard_explainer("{spec.slug}"' in compact
        assert has_direct or has_bootstrap, spec.slug
