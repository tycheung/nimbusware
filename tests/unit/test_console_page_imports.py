from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", "test-admin-token-for-import-smoke")


_CONSOLE_PAGE_MODULES: tuple[str, ...] = (
    "nimbusware_console.main",
    "nimbusware_console.operator_chat",
    "nimbusware_console.enterprise_console_ui",
    "nimbusware_console.custom_agents_ui",
    "nimbusware_console.pages.config_tooling",
    "nimbusware_console.pages.config_tooling.ollama_models",
    "nimbusware_console.pages.run_list",
    "nimbusware_console.pages.preflight_fleet",
    "nimbusware_console.pages.run_detail",
)

_PAGE_MODULES: tuple[str, ...] = _CONSOLE_PAGE_MODULES + (
    "nimbusware_maker.ui",
    "nimbusware_maker.ui.settings",
    "nimbusware_maker.ui.ollama_models",
)


@pytest.mark.parametrize("module_name", _PAGE_MODULES)
def test_page_module_imports(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_config_tooling_render_callable() -> None:
    from nimbusware_console.pages.config_tooling import render_config_tooling_section

    assert callable(render_config_tooling_section)
