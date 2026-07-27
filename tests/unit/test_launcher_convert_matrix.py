from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from env.launcher_fetch import (
    INSTALL_PROFILE_BAREBONES,
    INSTALL_PROFILE_FULL,
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
    install_script_args,
)
from env.launcher_manage import (
    InstallState,
    convert_label,
    read_install_state,
    run_convert_install,
)

ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPTS = ROOT / "scripts" / "install"
if str(INSTALL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(INSTALL_SCRIPTS))

from ollama_setup import DEFAULT_MODELS, models_from_repo  # noqa: E402


# --- Convert matrix: profile/bundle transitions the launcher offers ---------

CONVERT_CASES: list[dict[str, Any]] = [
    {
        "id": "quick_to_full",
        "from_profile": INSTALL_PROFILE_BAREBONES,
        "from_bundle": SETUP_BUNDLE_DEFAULT,
        "to_profile": INSTALL_PROFILE_FULL,
        "to_bundle": SETUP_BUNDLE_DEFAULT,
        "expect_in_args": ("--postgres-choice", "provided", "--install-profile", "recommended"),
        "forbid_in_args": ("--skip-postgres",),
        "label": "Full / Individual",
    },
    {
        "id": "full_to_quick",
        "from_profile": INSTALL_PROFILE_FULL,
        "from_bundle": SETUP_BUNDLE_DEFAULT,
        "to_profile": INSTALL_PROFILE_BAREBONES,
        "to_bundle": SETUP_BUNDLE_DEFAULT,
        "expect_in_args": ("--skip-postgres", "--install-profile", "barebones"),
        "forbid_in_args": ("--postgres-choice",),
        "label": "Quick / Individual",
    },
    {
        "id": "individual_to_enterprise",
        "from_profile": INSTALL_PROFILE_FULL,
        "from_bundle": SETUP_BUNDLE_DEFAULT,
        "to_profile": INSTALL_PROFILE_FULL,
        "to_bundle": SETUP_BUNDLE_ENTERPRISE,
        "expect_in_args": (
            "--setup-bundle",
            "enterprise",
            "--edition",
            "enterprise",
            "--install-profile",
            "recommended",
        ),
        "forbid_in_args": (),
        "label": "Full / Enterprise",
    },
    {
        "id": "enterprise_to_individual",
        "from_profile": INSTALL_PROFILE_FULL,
        "from_bundle": SETUP_BUNDLE_ENTERPRISE,
        "to_profile": INSTALL_PROFILE_FULL,
        "to_bundle": SETUP_BUNDLE_DEFAULT,
        "expect_in_args": ("--setup-bundle", "default", "--install-profile", "recommended"),
        "forbid_in_args": ("--edition",),
        "label": "Full / Individual",
    },
    {
        "id": "quick_to_enterprise",
        "from_profile": INSTALL_PROFILE_BAREBONES,
        "from_bundle": SETUP_BUNDLE_DEFAULT,
        "to_profile": INSTALL_PROFILE_FULL,
        "to_bundle": SETUP_BUNDLE_ENTERPRISE,
        "expect_in_args": (
            "--setup-bundle",
            "enterprise",
            "--edition",
            "enterprise",
            "--postgres-choice",
            "provided",
        ),
        "forbid_in_args": ("--skip-postgres",),
        "label": "Full / Enterprise",
    },
]


@pytest.mark.parametrize("case", CONVERT_CASES, ids=lambda c: c["id"])
def test_convert_install_script_args_matrix(case: dict[str, Any]) -> None:
    args = install_script_args(case["to_profile"], setup_bundle=case["to_bundle"])
    for token in case["expect_in_args"]:
        assert token in args, f"{case['id']}: missing {token!r} in {args}"
    for token in case["forbid_in_args"]:
        assert token not in args, f"{case['id']}: unexpected {token!r} in {args}"


@pytest.mark.parametrize("case", CONVERT_CASES, ids=lambda c: c["id"])
def test_convert_label_for_target_state(case: dict[str, Any]) -> None:
    state = InstallState(
        install_profile=case["to_profile"],
        setup_bundle=case["to_bundle"],
        edition="enterprise" if case["to_bundle"] == SETUP_BUNDLE_ENTERPRISE else "individual",
        database_url=None,
    )
    assert convert_label(state) == case["label"]


@pytest.mark.parametrize("case", CONVERT_CASES, ids=lambda c: c["id"])
def test_run_convert_install_invokes_matching_args(
    tmp_path: Path,
    case: dict[str, Any],
) -> None:
    """Each upgrade/downgrade path must invoke install_nimbusware with the right flags."""
    script = tmp_path / "install_nimbusware.py"
    script.write_text("# stub\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname="nimbusware"\n', encoding="utf-8")
    (tmp_path / "packages" / "store" / "schema").mkdir(parents=True)
    (tmp_path / "packages" / "store" / "schema" / "postgres.sql").write_text(
        "-- schema\n",
        encoding="utf-8",
    )

    extra = ["--database-url", "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware"]
    captured: dict[str, Any] = {}

    def _fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
        captured["cmd"] = list(cmd)
        captured["cwd"] = kwargs.get("cwd")
        result = MagicMock()
        result.returncode = 0
        return result

    with (
        patch("env.launcher_manage.resolve_install_script", return_value=script),
        patch("env.launcher_manage.resolve_bootstrap_python", return_value=[sys.executable]),
        patch("env.launcher_manage.subprocess.run", side_effect=_fake_run),
    ):
        code = run_convert_install(
            tmp_path,
            profile=case["to_profile"],
            setup_bundle=case["to_bundle"],
            extra_args=extra if case["to_profile"] == INSTALL_PROFILE_FULL else None,
        )

    assert code == 0
    cmd = captured["cmd"]
    assert str(script) in cmd
    for token in case["expect_in_args"]:
        assert token in cmd
    for token in case["forbid_in_args"]:
        assert token not in cmd
    if case["to_profile"] == INSTALL_PROFILE_FULL:
        assert "--database-url" in cmd


def test_read_install_state_roundtrip_after_profile_change(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "NIMBUSWARE_INSTALL_PROFILE=barebones\n"
        "NIMBUSWARE_SETUP_BUNDLE=default\n"
        "NIMBUSWARE_EDITION=individual\n",
        encoding="utf-8",
    )
    before = read_install_state(tmp_path)
    assert before.install_profile == INSTALL_PROFILE_BAREBONES

    (tmp_path / ".env").write_text(
        "NIMBUSWARE_INSTALL_PROFILE=recommended\n"
        "NIMBUSWARE_SETUP_BUNDLE=default\n"
        "NIMBUSWARE_EDITION=individual\n"
        "NIMBUSWARE_DATABASE_URL=postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware\n",
        encoding="utf-8",
    )
    after = read_install_state(tmp_path)
    assert after.install_profile == INSTALL_PROFILE_FULL
    assert after.database_url is not None
    assert convert_label(after) == "Full / Individual"


def test_models_from_repo_ignores_provider_ids(tmp_path: Path) -> None:
    """Regression: providers.id: ollama must not become an ollama pull target."""
    cfg = tmp_path / "configs"
    cfg.mkdir()
    (cfg / "model-routing.yaml").write_text(
        "version: 1\n"
        "models:\n"
        "  primary:\n"
        "    id: llama3.1:8b\n"
        "  fallbacks:\n"
        "  - id: qwen2.5-coder:14b\n"
        "providers:\n"
        "- id: ollama\n"
        "  kind: local\n"
        "- id: openai\n"
        "  kind: cloud\n",
        encoding="utf-8",
    )
    models = models_from_repo(tmp_path)
    assert models == ["llama3.1:8b", "qwen2.5-coder:14b"]
    assert "ollama" not in models
    assert "openai" not in models


def test_models_from_repo_real_checkout() -> None:
    models = models_from_repo(ROOT)
    assert "llama3.1:8b" in models
    assert "qwen2.5-coder:14b" in models
    assert "ollama" not in models
    assert "openai" not in models
    assert "anthropic" not in models
    assert "google" not in models


def test_models_from_repo_defaults_when_missing(tmp_path: Path) -> None:
    assert models_from_repo(tmp_path) == list(DEFAULT_MODELS)
