from __future__ import annotations

import os

import pytest

from e2e.harness.env import DEFAULT_E2E_ENV
from env import find_repo_root

_REPO = find_repo_root()
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))
for _key, _value in DEFAULT_E2E_ENV.items():
    os.environ.setdefault(_key, _value)


def pytest_configure(config: pytest.Config) -> None:
    retries = os.environ.get("NIMBUSWARE_E2E_FLAKE_RETRIES", "").strip()
    if retries.isdigit() and int(retries) > 0:
        config.option.reruns = int(retries)
        config.option.reruns_delay = int(os.environ.get("NIMBUSWARE_E2E_FLAKE_DELAY", "2") or "2")
