from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "packages" / "nimbusware_bootstrap"


def _ensure_wheel() -> Path:
    dist = _PKG / "dist"
    wheels = list(dist.glob("*.whl")) if dist.is_dir() else []
    if wheels:
        return sorted(wheels)[-1]
    build_tool = subprocess.run(
        [sys.executable, "-m", "pip", "install", "build", "-q"],
        capture_output=True,
        check=False,
    )
    if build_tool.returncode != 0:
        raise RuntimeError("pip install build failed")
    if dist.is_dir():
        shutil.rmtree(dist, ignore_errors=True)
    proc = subprocess.run(
        [sys.executable, "-m", "build", str(_PKG)],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    wheels = list(dist.glob("*.whl"))
    assert wheels, "expected wheel in dist/"
    return sorted(wheels)[-1]


def test_bootstrap_wheel_install_smoke(tmp_path: Path) -> None:
    wheel = _ensure_wheel()
    site = tmp_path / "site"
    site.mkdir()
    install = subprocess.run(
        [sys.executable, "-m", "pip", "install", str(wheel), "--target", str(site), "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PYTHONPATH"] = str(site)
    proc = subprocess.run(
        [sys.executable, "-m", "nimbusware_bootstrap", "--print-only"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Nimbusware consumer bootstrap" in proc.stdout
    assert "curl -fsSL" in proc.stdout
    assert "nimbusware-bootstrap" in proc.stdout


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def test_bootstrap_wheel_venv_install_subprocess(tmp_path: Path) -> None:
    wheel = _ensure_wheel()
    venv_dir = tmp_path / "venv"
    create = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0:
        pytest.skip(f"venv unavailable: {create.stderr}")
    py = _venv_python(venv_dir)
    install = subprocess.run(
        [str(py), "-m", "pip", "install", str(wheel), "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    proc = subprocess.run(
        [str(py), "-m", "nimbusware_bootstrap", "--print-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Nimbusware consumer bootstrap" in proc.stdout
