from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

_MAKER_UI_MODULES: tuple[str, ...] = (
    "nimbusware_maker.ui",
    "nimbusware_maker.ui.home",
    "nimbusware_maker.ui.intent",
    "nimbusware_maker.ui.approval",
    "nimbusware_maker.ui.progress",
    "nimbusware_maker.ui.settings",
    "nimbusware_maker.ui.wizard",
    "nimbusware_maker.ui.ollama_models",
)


@pytest.mark.parametrize("module_name", _MAKER_UI_MODULES)
def test_maker_ui_module_imports(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_maker_render_main_callable() -> None:
    from nimbusware_maker.ui import render_main

    assert callable(render_main)
