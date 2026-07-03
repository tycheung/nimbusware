from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", "test-admin-token-for-import-smoke")

_CONSOLE_MODULES: tuple[str, ...] = (
    "console",
    "console.operator_chat",
    "console.operator_chat_core",
    "console.services.operator_chat",
)


@pytest.mark.parametrize("module_name", _CONSOLE_MODULES)
def test_console_module_imports(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None
