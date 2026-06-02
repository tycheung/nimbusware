from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_PS1 = _REPO / "scripts" / "ci_check.ps1"
_SH = _REPO / "scripts" / "ci_check.sh"
_PRECOMMIT = _REPO / ".pre-commit-config.yaml"


def test_ci_mypy_includes_api_pilot_modules() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "packages/nimbusware_api/routes/ollama.py" in text
    assert "packages/nimbusware_api/schemas/ollama.py" in text
    assert "packages/nimbusware_api/errors.py" in text


def test_ci_check_scripts_include_api_pilot_modules() -> None:
    ps1 = _PS1.read_text(encoding="utf-8")
    sh = _SH.read_text(encoding="utf-8")
    assert "packages/nimbusware_api/routes/ollama.py" in ps1
    assert "packages/nimbusware_api/routes/ollama.py" in sh


def test_precommit_parity_hook_includes_api_pilot_modules() -> None:
    text = _PRECOMMIT.read_text(encoding="utf-8")
    assert "mypy (services + tranche B + API pilot" in text
    assert "packages/nimbusware_api/routes/ollama.py" in text
