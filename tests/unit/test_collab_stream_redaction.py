from __future__ import annotations

from orchestrator.collab.stream_redaction import redact_theater_lines


def test_redact_theater_lines_strips_api_key_patterns() -> None:
    lines = [
        {"role": "theater", "text": "used api_key=sk-secret123 for call"},
        {"role": "user", "body": "hello"},
    ]
    out = redact_theater_lines(lines)
    assert "[redacted]" in out[0]["text"]
    assert "sk-secret" not in out[0]["text"]
    assert out[1]["body"] == "hello"
