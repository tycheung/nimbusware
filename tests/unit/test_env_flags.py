from __future__ import annotations

from nimbusware_env.env_flags import (
    env_bool,
    env_falsy,
    env_force_off,
    env_force_on,
    env_truthy,
    env_truthy_raw,
    hermes_preflight_latency_sample_count,
    hermes_run_bandit_enabled,
    hermes_run_semgrep_enabled,
    hermes_skip_preflight_enabled,
    hermes_slice_auto_advance_enabled,
    hermes_slice_implement_mode,
    hermes_use_llm_explicitly_off,
    nimbusware_api_host,
    nimbusware_config_from_db_enabled,
    nimbusware_workflow_profile,
)


def test_env_truthy_and_falsy() -> None:
    assert env_truthy("HERMES_TEST_FLAG") is False
    assert env_falsy("HERMES_TEST_FLAG") is False


def test_env_truthy_raw_does_not_strip(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_TEST_RAW", "  1  ")
    assert env_truthy_raw("HERMES_TEST_RAW") is False
    monkeypatch.setenv("HERMES_TEST_RAW", "1")
    assert env_truthy_raw("HERMES_TEST_RAW") is True


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


def test_hermes_run_bandit_enabled_raw(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_RUN_BANDIT", raising=False)
    assert hermes_run_bandit_enabled() is False
    monkeypatch.setenv("HERMES_RUN_BANDIT", "  1  ")
    assert hermes_run_bandit_enabled() is False
    monkeypatch.setenv("HERMES_RUN_BANDIT", "1")
    assert hermes_run_bandit_enabled() is True


def test_hermes_run_semgrep_default_on(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_RUN_SEMGREP", raising=False)
    assert hermes_run_semgrep_enabled() is True
    monkeypatch.setenv("HERMES_RUN_SEMGREP", "0")
    assert hermes_run_semgrep_enabled() is False


def test_hermes_slice_implement_mode(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_SLICE_IMPLEMENT", raising=False)
    assert hermes_slice_implement_mode() == "scoped"
    monkeypatch.setenv("HERMES_SLICE_IMPLEMENT", "agent")
    assert hermes_slice_implement_mode() == "agent"


def test_nimbusware_config_from_db_enabled(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_DB", raising=False)
    assert nimbusware_config_from_db_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://localhost/nimbusware")
    assert nimbusware_config_from_db_enabled() is True


def test_hermes_use_llm_explicitly_off(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_USE_LLM", raising=False)
    assert hermes_use_llm_explicitly_off() is False
    monkeypatch.setenv("HERMES_USE_LLM", "0")
    assert hermes_use_llm_explicitly_off() is True


def test_nimbusware_api_host_prefers_platform_env(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_API_HOST", raising=False)
    monkeypatch.delenv("HERMES_API_HOST", raising=False)
    assert nimbusware_api_host() == "0.0.0.0"
    monkeypatch.setenv("NIMBUSWARE_API_HOST", "127.0.0.1")
    assert nimbusware_api_host() == "127.0.0.1"
    monkeypatch.delenv("NIMBUSWARE_API_HOST", raising=False)
    monkeypatch.setenv("HERMES_API_HOST", "10.0.0.1")
    assert nimbusware_api_host() == "10.0.0.1"


def test_nimbusware_workflow_profile(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_WORKFLOW_PROFILE", raising=False)
    monkeypatch.delenv("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", raising=False)
    monkeypatch.delenv("HERMES_WORKFLOW_PROFILE", raising=False)
    assert nimbusware_workflow_profile() == "nimbusware_production"
    monkeypatch.setenv("NIMBUSWARE_WORKFLOW_PROFILE", "micro_slice")
    assert nimbusware_workflow_profile() == "micro_slice"
    monkeypatch.delenv("NIMBUSWARE_WORKFLOW_PROFILE", raising=False)
    monkeypatch.setenv("HERMES_WORKFLOW_PROFILE", "default")
    assert nimbusware_workflow_profile() == "default"
