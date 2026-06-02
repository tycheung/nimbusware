from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_PS1 = _REPO / "scripts" / "ci_check.ps1"
_SH = _REPO / "scripts" / "ci_check.sh"
_PRECOMMIT = _REPO / ".pre-commit-config.yaml"


def test_ci_mypy_uses_shared_targets_module() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "scripts/mypy_ci_targets.py" in text


def test_ci_check_scripts_use_shared_targets_module() -> None:
    ps1 = _PS1.read_text(encoding="utf-8")
    sh = _SH.read_text(encoding="utf-8")
    assert "mypy_ci_targets.py" in ps1
    assert "mypy_ci_targets.py" in sh


def test_mypy_ci_targets_include_api_pilot_modules() -> None:
    targets = (_REPO / "scripts" / "mypy_ci_targets.py").read_text(encoding="utf-8")
    assert "packages/nimbusware_api/routes/ollama.py" in targets
    assert "packages/nimbusware_api/schemas/ollama.py" in targets
    assert "packages/nimbusware_api/errors.py" in targets


def test_precommit_parity_hook_uses_shared_targets_module() -> None:
    text = _PRECOMMIT.read_text(encoding="utf-8")
    assert "mypy_ci_targets.py" in text
