from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    retries = os.environ.get("NIMBUSWARE_E2E_FLAKE_RETRIES", "").strip()
    if retries.isdigit() and int(retries) > 0:
        config.option.reruns = int(retries)
        config.option.reruns_delay = int(os.environ.get("NIMBUSWARE_E2E_FLAKE_DELAY", "2") or "2")
