"""Unit tests for Streamlit theme / white-label captions (PLAN_GAP §14 #11)."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.console_theme import (
    streamlit_theme_defaults_caption,
    streamlit_white_label_deferred_caption,
)


def test_streamlit_theme_defaults_caption_mentions_config_toml(tmp_path: Path) -> None:
    cap = streamlit_theme_defaults_caption(repo_root=tmp_path)
    assert ".streamlit/config.toml" in cap
    assert "missing" in cap


def test_streamlit_theme_defaults_caption_present_when_config_exists(
    tmp_path: Path,
) -> None:
    cfg_dir = tmp_path / ".streamlit"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text("[theme]\nbase = \"light\"\n", encoding="utf-8")
    cap = streamlit_theme_defaults_caption(repo_root=tmp_path)
    assert "present" in cap
    assert "primaryColor" in cap


def test_streamlit_white_label_deferred_caption() -> None:
    cap = streamlit_white_label_deferred_caption()
    assert "deferred" in cap.lower()
    assert ".streamlit/config.toml" in cap
    assert "#11" in cap or "§14" in cap


def test_repo_streamlit_config_documents_white_label_deferral() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "white-label" in text.lower()
    assert "deferred" in text.lower()
