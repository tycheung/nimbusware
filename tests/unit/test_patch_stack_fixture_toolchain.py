from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "tests" / "fixtures" / "repos"


@pytest.mark.parametrize("fixture_name", ["tiny_go_app"])
def test_patch_fixture_tests_fail_with_intentional_bug(fixture_name: str) -> None:
    if shutil.which("go") is None:
        pytest.skip("go toolchain not installed")
    root = _FIXTURES / fixture_name
    proc = subprocess.run(
        ["go", "test", "./..."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_tiny_jvm_fixture_tests_fail_with_intentional_bug() -> None:
    if shutil.which("mvn") is None or shutil.which("java") is None:
        pytest.skip("maven/java toolchain not installed")
    root = _FIXTURES / "tiny_jvm_app"
    assert (root / "pom.xml").is_file()
    proc = subprocess.run(
        ["mvn", "-q", "test"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, proc.stdout + proc.stderr
