from __future__ import annotations

import pytest

from nimbusware_env.env_flags import (
    env_bool,
    env_falsy,
    env_force_off,
    env_force_on,
    env_truthy,
    env_truthy_raw,
    nimbusware_api_host,
    nimbusware_config_from_db_enabled,
    nimbusware_preflight_latency_sample_count,
    nimbusware_run_bandit_enabled,
    nimbusware_run_semgrep_enabled,
    nimbusware_skip_preflight_enabled,
    nimbusware_slice_auto_advance_enabled,
    nimbusware_slice_implement_mode,
    nimbusware_use_llm_explicitly_off,
    nimbusware_workflow_profile,
)


def test_env_truthy_and_falsy() -> None:
    assert env_truthy("NIMBUSWARE_TEST_FLAG") is False
    assert env_falsy("NIMBUSWARE_TEST_FLAG") is False


def test_env_truthy_raw_does_not_strip(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_TEST_RAW", "  1  ")
    assert env_truthy_raw("NIMBUSWARE_TEST_RAW") is False
    monkeypatch.setenv("NIMBUSWARE_TEST_RAW", "1")
    assert env_truthy_raw("NIMBUSWARE_TEST_RAW") is True


def test_env_bool_defaults(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_TEST_BOOL", raising=False)
    assert env_bool("NIMBUSWARE_TEST_BOOL", default=True) is True
    monkeypatch.setenv("NIMBUSWARE_TEST_BOOL", "yes")
    assert env_bool("NIMBUSWARE_TEST_BOOL", default=False) is True
    monkeypatch.setenv("NIMBUSWARE_TEST_BOOL", "no")
    assert env_bool("NIMBUSWARE_TEST_BOOL", default=True) is False


def test_env_tri_state_helpers(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_TEST_TRI", "1")
    assert env_force_on("NIMBUSWARE_TEST_TRI") is True
    assert env_force_off("NIMBUSWARE_TEST_TRI") is False
    monkeypatch.setenv("NIMBUSWARE_TEST_TRI", "0")
    assert env_force_off("NIMBUSWARE_TEST_TRI") is True
    assert env_force_on("NIMBUSWARE_TEST_TRI") is False


def test_nimbusware_slice_auto_advance_default_on(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SLICE_AUTO_ADVANCE", raising=False)
    assert nimbusware_slice_auto_advance_enabled() is True
    monkeypatch.setenv("NIMBUSWARE_SLICE_AUTO_ADVANCE", "0")
    assert nimbusware_slice_auto_advance_enabled() is False


def test_nimbusware_skip_preflight(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SKIP_PREFLIGHT", raising=False)
    assert nimbusware_skip_preflight_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", "yes")
    assert nimbusware_skip_preflight_enabled() is True


def test_preflight_latency_sample_count_clamps(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_PREFLIGHT_LATENCY_SAMPLES", "999")
    assert nimbusware_preflight_latency_sample_count() == 20
    monkeypatch.setenv("NIMBUSWARE_PREFLIGHT_LATENCY_SAMPLES", "not-a-number")
    assert nimbusware_preflight_latency_sample_count(default=3) == 3


def test_nimbusware_run_bandit_enabled_raw(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_RUN_BANDIT", raising=False)
    assert nimbusware_run_bandit_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_RUN_BANDIT", "  1  ")
    assert nimbusware_run_bandit_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_RUN_BANDIT", "1")
    assert nimbusware_run_bandit_enabled() is True


def test_nimbusware_run_semgrep_default_on(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_RUN_SEMGREP", raising=False)
    assert nimbusware_run_semgrep_enabled() is True
    monkeypatch.setenv("NIMBUSWARE_RUN_SEMGREP", "0")
    assert nimbusware_run_semgrep_enabled() is False


def test_nimbusware_slice_implement_mode(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SLICE_IMPLEMENT", raising=False)
    assert nimbusware_slice_implement_mode() == "scoped"
    monkeypatch.setenv("NIMBUSWARE_SLICE_IMPLEMENT", "agent")
    assert nimbusware_slice_implement_mode() == "agent"


def test_nimbusware_config_from_db_enabled(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_DB", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_FILES", raising=False)
    assert nimbusware_config_from_db_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://localhost/nimbusware")
    assert nimbusware_config_from_db_enabled() is True
    monkeypatch.setenv("NIMBUSWARE_CONFIG_FROM_FILES", "1")
    assert nimbusware_config_from_db_enabled() is False


def test_nimbusware_config_from_files_enabled(monkeypatch) -> None:
    from nimbusware_env.env_flags import nimbusware_config_from_files_enabled

    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_FILES", raising=False)
    assert nimbusware_config_from_files_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_CONFIG_FROM_FILES", "yes")
    assert nimbusware_config_from_files_enabled() is True


def test_nimbusware_use_llm_explicitly_off(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_USE_LLM", raising=False)
    assert nimbusware_use_llm_explicitly_off() is False
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "0")
    assert nimbusware_use_llm_explicitly_off() is True


def test_nimbusware_api_host(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_API_HOST", raising=False)
    assert nimbusware_api_host() == "0.0.0.0"
    monkeypatch.setenv("NIMBUSWARE_API_HOST", "127.0.0.1")
    assert nimbusware_api_host() == "127.0.0.1"


def test_nimbusware_ollama_base_url(monkeypatch) -> None:
    from nimbusware_env.env_flags import nimbusware_ollama_base_url

    monkeypatch.delenv("NIMBUSWARE_OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert nimbusware_ollama_base_url() == "http://127.0.0.1:11434"
    monkeypatch.setenv("NIMBUSWARE_OLLAMA_BASE_URL", "http://canonical:11434")
    assert nimbusware_ollama_base_url() == "http://canonical:11434"
    monkeypatch.delenv("NIMBUSWARE_OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://legacy:11434")
    with pytest.warns(DeprecationWarning, match="OLLAMA_HOST"):
        assert nimbusware_ollama_base_url() == "http://legacy:11434"


def test_nimbusware_api_base_url(monkeypatch) -> None:
    from nimbusware_env.env_flags import nimbusware_api_base_url

    monkeypatch.delenv("NIMBUSWARE_API_BASE", raising=False)
    monkeypatch.delenv("NIMBUSWARE_API_HOST", raising=False)
    monkeypatch.delenv("NIMBUSWARE_API_PORT", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    assert nimbusware_api_base_url() == "http://127.0.0.1:8000/v1"
    monkeypatch.setenv("NIMBUSWARE_API_BASE", "http://custom:9000/v1")
    assert nimbusware_api_base_url() == "http://custom:9000/v1"
    monkeypatch.delenv("NIMBUSWARE_API_BASE", raising=False)
    monkeypatch.setenv("NIMBUSWARE_API_PORT", "9001")
    assert nimbusware_api_base_url() == "http://127.0.0.1:9001/v1"


def test_nimbusware_api_port(monkeypatch) -> None:
    from nimbusware_env.env_flags import nimbusware_api_port

    monkeypatch.delenv("NIMBUSWARE_API_PORT", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    assert nimbusware_api_port() == 8000
    monkeypatch.setenv("NIMBUSWARE_API_PORT", "9001")
    assert nimbusware_api_port() == 9001
    monkeypatch.delenv("NIMBUSWARE_API_PORT", raising=False)
    monkeypatch.setenv("PORT", "9002")
    with pytest.warns(DeprecationWarning, match="PORT"):
        assert nimbusware_api_port() == 9002


def test_nimbusware_workflow_profile(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_WORKFLOW_PROFILE", raising=False)
    monkeypatch.delenv("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", raising=False)
    assert nimbusware_workflow_profile() == "nimbusware_production"
    monkeypatch.setenv("NIMBUSWARE_WORKFLOW_PROFILE", "micro_slice")
    with pytest.warns(DeprecationWarning, match="NIMBUSWARE_WORKFLOW_PROFILE"):
        assert nimbusware_workflow_profile() == "micro_slice"
    monkeypatch.setenv("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", "patch")
    assert nimbusware_workflow_profile() == "patch"
