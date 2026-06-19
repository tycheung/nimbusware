#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_PUBLISH_DIR = Path(__file__).resolve().parent
if str(_PUBLISH_DIR) not in sys.path:
    sys.path.insert(0, str(_PUBLISH_DIR))

from launcher_artifact_name import launcher_artifact_filename


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rename dist launcher binary for release upload")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
        help="PyInstaller dist directory",
    )
    args = parser.parse_args(argv)
    dist = args.dist_dir.resolve()
    candidates = [dist / "NimbuswareLauncher.exe", dist / "NimbuswareLauncher"]
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        raise SystemExit(f"launcher binary not found under {dist}")
    target = dist / launcher_artifact_filename()
    if target != source:
        if target.exists():
            target.unlink()
        shutil.move(str(source), str(target))
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
