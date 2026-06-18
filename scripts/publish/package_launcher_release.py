#!/usr/bin/env python3
"""Create a distributable launcher archive (zip) for the current platform."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

_PUBLISH_DIR = Path(__file__).resolve().parent
if str(_PUBLISH_DIR) not in sys.path:
    sys.path.insert(0, str(_PUBLISH_DIR))

from launcher_artifact_name import launcher_artifact_basename, launcher_artifact_filename

INSTALL_TEXT = Path(__file__).resolve().parent.joinpath("INSTALL.txt").read_text(encoding="utf-8")


def find_launcher_binary(dist_dir: Path) -> Path:
    named = dist_dir / launcher_artifact_filename()
    if named.is_file():
        return named
    for candidate in (dist_dir / "NimbuswareLauncher.exe", dist_dir / "NimbuswareLauncher"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"launcher binary not found in {dist_dir}")


def package_launcher_zip(dist_dir: Path, *, output_dir: Path | None = None) -> Path:
    dist_dir = dist_dir.resolve()
    binary = find_launcher_binary(dist_dir)
    out_dir = (output_dir or dist_dir / "release").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{launcher_artifact_basename()}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(binary, arcname=binary.name)
        archive.writestr("INSTALL.txt", INSTALL_TEXT)
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Package launcher binary into a release zip")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    path = package_launcher_zip(args.dist_dir, output_dir=args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
