from __future__ import annotations

from pathlib import Path

from env.install_setup_bundles import (
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
    apply_setup_bundle_env,
    bundle_edition,
    bundle_env_vars,
    load_setup_bundle,
)

_REPO = Path(__file__).resolve().parents[2]


def test_load_default_bundle_env() -> None:
    bundle = load_setup_bundle(SETUP_BUNDLE_DEFAULT, repo_root=_REPO)
    env = bundle_env_vars(bundle)
    assert env["NIMBUSWARE_SETUP_BUNDLE"] == "default"
    assert env["NIMBUSWARE_DEFAULT_AUTOPILOT_PROFILE"] == "guided"
    assert env["NIMBUSWARE_COLLAB_ENABLED"] == "0"
    assert bundle_edition(bundle) == "individual"


def test_load_enterprise_bundle_env() -> None:
    bundle = load_setup_bundle(SETUP_BUNDLE_ENTERPRISE, repo_root=_REPO)
    env = bundle_env_vars(bundle)
    assert env["NIMBUSWARE_SETUP_BUNDLE"] == "enterprise"
    assert env["NIMBUSWARE_SLICE_BUDGET_PRESET"] == "tiny"
    assert env["NIMBUSWARE_SLICE_AUTO_COMMIT"] == "1"
    assert bundle_edition(bundle) == "enterprise"


def test_apply_setup_bundle_env_writes_dotenv(tmp_path: Path) -> None:
    (tmp_path / "configs" / "install" / "bundles").mkdir(parents=True)
    src = _REPO / "configs" / "install" / "bundles" / "default.env.yaml"
    (tmp_path / "configs" / "install" / "bundles" / "default.env.yaml").write_text(
        src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    applied = apply_setup_bundle_env(tmp_path, SETUP_BUNDLE_DEFAULT)
    assert applied["NIMBUSWARE_SETUP_BUNDLE"] == "default"
    dotenv = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "NIMBUSWARE_DEFAULT_AUTOPILOT_PROFILE=guided" in dotenv


def test_launcher_install_args_include_setup_bundle() -> None:
    from env.launcher_fetch import (
        SETUP_BUNDLE_ENTERPRISE,
        install_script_args,
    )

    default_args = install_script_args("barebones", setup_bundle="default")
    assert "--setup-bundle" in default_args
    assert default_args[default_args.index("--setup-bundle") + 1] == "default"

    enterprise_args = install_script_args("recommended", setup_bundle=SETUP_BUNDLE_ENTERPRISE)
    assert "--setup-bundle" in enterprise_args
    assert "--edition" in enterprise_args
    assert "enterprise" in enterprise_args


def test_install_module_setup_bundle_constants() -> None:
    import importlib.util

    install_path = _REPO / "scripts" / "install" / "install_nimbusware.py"
    spec = importlib.util.spec_from_file_location("install_nimbusware", install_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SETUP_BUNDLE_DEFAULT == "default"
    assert mod.SETUP_BUNDLE_ENTERPRISE == "enterprise"
