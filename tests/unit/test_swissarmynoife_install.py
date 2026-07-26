from __future__ import annotations

from pathlib import Path

from env.swissarmynoife_install import (
    DEFAULT_BROKER_HTTP,
    default_swissarmynoife_target,
    is_swissarmynoife_checkout,
    swissarmynoife_clone_url,
)


def test_is_swissarmynoife_checkout_requires_cargo_and_mcp(tmp_path: Path) -> None:
    assert not is_swissarmynoife_checkout(tmp_path)
    (tmp_path / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
    assert not is_swissarmynoife_checkout(tmp_path)
    (tmp_path / "crates" / "mcp").mkdir(parents=True)
    assert is_swissarmynoife_checkout(tmp_path)


def test_default_swissarmynoife_target_is_sibling(tmp_path: Path) -> None:
    nimbus = tmp_path / "Nimbusware"
    nimbus.mkdir()
    assert default_swissarmynoife_target(nimbus) == (tmp_path / "SwissArmyNoife").resolve()


def test_default_swissarmynoife_target_env_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    nimbus = tmp_path / "Nimbusware"
    nimbus.mkdir()
    custom = tmp_path / "custom-sak"
    monkeypatch.setenv("NIMBUSWARE_SWISSARMYNOIFE_DIR", str(custom))
    assert default_swissarmynoife_target(nimbus) == custom.resolve()


def test_swissarmynoife_clone_url_defaults_and_override(monkeypatch) -> None:
    monkeypatch.delenv("SWISSARMYNOIFE_CLONE_URL", raising=False)
    monkeypatch.delenv("NIMBUSWARE_SAK_CLONE_URL", raising=False)
    assert "SwissArmyNoife" in swissarmynoife_clone_url()
    monkeypatch.setenv("SWISSARMYNOIFE_CLONE_URL", "https://example.com/sak.git")
    assert swissarmynoife_clone_url() == "https://example.com/sak.git"


def test_write_broker_env_sets_default(tmp_path: Path, monkeypatch) -> None:
    from env.swissarmynoife_install import write_broker_env

    monkeypatch.delenv("NIMBUSWARE_BROKER_HTTP", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    write_broker_env(tmp_path)
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert f"NIMBUSWARE_BROKER_HTTP={DEFAULT_BROKER_HTTP}" in text.replace(" ", "")
