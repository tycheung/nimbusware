from __future__ import annotations

import pytest

from nimbusware_env.env_flags import (
    env_bool,
    env_force_off,
    env_force_on,
    env_falsy,
    env_truthy,
    hermes_preflight_latency_sample_count,
    hermes_slice_auto_advance_enabled,
    hermes_skip_preflight_enabled,
)


def test_env_truthy_and_falsy() -> None:
    assert env_truthy("HERMES_TEST_FLAG") is False
    assert env_falsy("HERMES_TEST_FLAG") is False


def test_env_bool_defaults(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_TEST_BOOL", raising=False)
    assert env_bool("HERMES_TEST_BOOL", default=True) is True
    monkeypatch.setenv("HERMES_TEST_BOOL", "yes")
    assert env_bool("HERMES_TEST_BOOL", default=False) is True
    monkeypatch.setenv("HERMES_TEST_BOOL", "no")
    assert env_bool("HERMES_TEST_BOOL", default=True) is False


def test_env_tri_state_helpers(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_TEST_TRI", "1")
    assert env_force_on("HERMES_TEST_TRI") is True
    assert env_force_off("HERMES_TEST_TRI") is False
    monkeypatch.setenv("HERMES_TEST_TRI", "0")
    assert env_force_off("HERMES_TEST_TRI") is True
    assert env_force_on("HERMES_TEST_TRI") is False


def test_hermes_slice_auto_advance_default_on(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_SLICE_AUTO_ADVANCE", raising=False)
    assert hermes_slice_auto_advance_enabled() is True
    monkeypatch.setenv("HERMES_SLICE_AUTO_ADVANCE", "0")
    assert hermes_slice_auto_advance_enabled() is False


def test_hermes_skip_preflight(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_SKIP_PREFLIGHT", raising=False)
    assert hermes_skip_preflight_enabled() is False
    monkeypatch.setenv("HERMES_SKIP_PREFLIGHT", "yes")
    assert hermes_skip_preflight_enabled() is True


def test_preflight_latency_sample_count_clamps(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_PREFLIGHT_LATENCY_SAMPLES", "999")
    assert hermes_preflight_latency_sample_count() == 20
    monkeypatch.setenv("HERMES_PREFLIGHT_LATENCY_SAMPLES", "not-a-number")
    assert hermes_preflight_latency_sample_count(default=3) == 3
