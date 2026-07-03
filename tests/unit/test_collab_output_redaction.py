from __future__ import annotations

from orchestrator.collab.output_redaction import redact_collab_output


def test_redact_collab_output_strips_api_key() -> None:
    raw = "failed: Authorization: Bearer sk-secret-key-12345"
    out = redact_collab_output(raw)
    assert "sk-secret" not in out
    assert "[redacted]" in out


def test_redact_collab_output_env_path() -> None:
    out = redact_collab_output("read /.env.local for config")
    assert ".env.local" not in out
    assert "[env-path]" in out
