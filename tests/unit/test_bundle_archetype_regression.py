from __future__ import annotations

from pathlib import Path

from nimbusware_env.install_setup_bundles import (
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
    archetype_subchoice_config,
    bundle_edition,
    bundle_env_vars,
    bundle_maker_defaults,
    load_setup_bundle,
)

_REPO = Path(__file__).resolve().parents[2]


def test_default_bundle_safe_coding_subchoice() -> None:
    bundle = load_setup_bundle(SETUP_BUNDLE_DEFAULT, repo_root=_REPO)
    safe = archetype_subchoice_config(bundle, "safe_coding")
    assert safe["workflow_profile"] == "safe_coding"
    assert safe["collab_enabled"] is False
    assert safe["maker_approval"] is True
    assert safe["slice_auto_advance"] is False


def test_default_bundle_engineer_subchoice() -> None:
    bundle = load_setup_bundle(SETUP_BUNDLE_DEFAULT, repo_root=_REPO)
    engineer = archetype_subchoice_config(bundle, "engineer")
    assert engineer["workflow_profile"] == "micro_slice"
    assert engineer["collab_enabled"] is True
    assert engineer["maker_approval"] is False
    assert engineer["slice_auto_advance"] is True


def test_enterprise_bundle_maker_defaults_ssot() -> None:
    bundle = load_setup_bundle(SETUP_BUNDLE_ENTERPRISE, repo_root=_REPO)
    env = bundle_env_vars(bundle)
    defaults = bundle_maker_defaults(bundle)
    assert bundle_edition(bundle) == "enterprise"
    assert env["NIMBUSWARE_SETUP_BUNDLE"] == "enterprise"
    assert env["NIMBUSWARE_DEFAULT_ENFORCEMENT_PROFILE"] == defaults["enforcement_profile_id"]
    assert env["NIMBUSWARE_SLICE_AUTO_COMMIT"] == "1"
    assert env["NIMBUSWARE_COLLAB_ENABLED"] == "1"
    assert defaults["slice_budget_preset"] == "tiny"


def test_default_bundle_env_matches_individual_edition() -> None:
    bundle = load_setup_bundle(SETUP_BUNDLE_DEFAULT, repo_root=_REPO)
    env = bundle_env_vars(bundle)
    assert bundle_edition(bundle) == "individual"
    assert env["NIMBUSWARE_COLLAB_ENABLED"] == "0"
    assert env["NIMBUSWARE_SLICE_AUTO_COMMIT"] == "0"
