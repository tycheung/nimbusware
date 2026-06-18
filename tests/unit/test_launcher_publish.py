from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_launcher_artifact_name_has_platform_suffix() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish" / "launcher_artifact_name.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    name = proc.stdout.strip()
    assert name.startswith("NimbuswareLauncher-")
    if sys.platform == "win32":
        assert name.endswith(".exe")


def test_package_launcher_zip(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    binary = dist / "NimbuswareLauncher-test.bin"
    binary.write_bytes(b"launcher")
    import sys

    publish_dir = ROOT / "scripts" / "publish"
    sys.path.insert(0, str(publish_dir))
    import launcher_artifact_name as names

    original = names.launcher_artifact_filename
    names.launcher_artifact_filename = lambda: binary.name  # type: ignore[assignment]
    try:
        from package_launcher_release import package_launcher_zip

        out = package_launcher_zip(dist, output_dir=tmp_path / "release")
        assert out.suffix == ".zip"
        assert out.is_file()
    finally:
        names.launcher_artifact_filename = original
