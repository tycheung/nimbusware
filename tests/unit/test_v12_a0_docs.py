from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def test_adr_022_exists() -> None:
    text = (REPO / "docs/adr/022-per-role-model-routing.md").read_text(encoding="utf-8")
    assert "ModelBindingResolver" in text
    assert "Precedence" in text or "precedence" in text


def test_adr_024_exists() -> None:
    text = (REPO / "docs/adr/024-install-profiles.md").read_text(encoding="utf-8")
    assert "recommended" in text
    assert "barebones" in text


def test_llm_call_sites_audit_exists() -> None:
    path = REPO / "docs/audits/llm-call-sites.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "ollama_chat_json" in text
    assert "ModelBindingResolver" in text
