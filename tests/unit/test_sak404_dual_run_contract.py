from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agent_tools.sandbox_bridge import try_broker_sandbox_exec
from agent_tools.shell_tools import tool_run_shell
from broker_client import (
    BrokerDisabled,
    bind_sandbox_exec,
    bind_tools_shell,
    broker_sandbox_enabled,
    broker_tools_enabled,
    select_backend,
)
from broker_client.stage_bind.tools import try_broker_shell_exec


def test_sak404_e_sandbox_tools_dual_run_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.delenv("NIMBUSWARE_BROKER_TOOLS", raising=False)

    assert broker_sandbox_enabled() is False
    assert broker_tools_enabled() is False
    assert select_backend("sandbox") == "python"
    assert select_backend("tools") == "python"
    assert try_broker_sandbox_exec(["echo", "hi"]) is None
    assert try_broker_shell_exec(["echo", "hi"]) is None

    with pytest.raises(BrokerDisabled):
        bind_sandbox_exec()
    with pytest.raises(BrokerDisabled):
        bind_tools_shell()

    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")

    assert broker_sandbox_enabled() is True
    assert broker_tools_enabled() is True
    assert select_backend("sandbox") == "broker"
    assert select_backend("tools") == "broker"


def test_sak404_e_tool_run_shell_broker_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda argv, cwd=".": {"exit_code": 0, "stdout": "sandbox broker ok"},
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
        lambda *_a, **_k: None,
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        result = tool_run_shell(tmp_path, "pytest", ["-q"])

    assert result.ok is True
    assert "sandbox broker ok" in result.llm_output
