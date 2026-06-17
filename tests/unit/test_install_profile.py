from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_INSTALL = _REPO / "scripts" / "install" / "install_nimbusware.py"


def _load_install_module():
    spec = importlib.util.spec_from_file_location("install_nimbusware", _INSTALL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_barebones_profile_sets_skip_ollama() -> None:
    mod = _load_install_module()
    args = argparse.Namespace(
        install_profile=mod.INSTALL_PROFILE_BAREBONES,
        skip_ollama=False,
        ollama_choice=None,
        install_ollama=False,
        non_interactive=True,
        ollama_pull_only=False,
    )
    mod._apply_install_profile_to_args(args, mod.INSTALL_PROFILE_BAREBONES)
    assert args.skip_ollama is True
    assert args.ollama_choice == "skip"


def test_skip_ollama_resolves_to_barebones_profile() -> None:
    mod = _load_install_module()
    args = argparse.Namespace(
        install_profile=mod.INSTALL_PROFILE_RECOMMENDED,
        skip_ollama=True,
        non_interactive=True,
        check_only=False,
    )
    profile = mod._resolve_install_profile(args, ["--skip-ollama"])
    assert profile == mod.INSTALL_PROFILE_BAREBONES


def test_enterprise_recommended_enables_seed_config() -> None:
    mod = _load_install_module()
    args = argparse.Namespace(
        install_profile=mod.INSTALL_PROFILE_RECOMMENDED,
        seed_config=False,
        non_interactive=True,
        skip_postgres=False,
        postgres_choice=None,
    )
    mod._apply_edition_profile_defaults(args, "enterprise")
    assert args.seed_config is True
