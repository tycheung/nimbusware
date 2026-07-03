#!/usr/bin/env python3
"""Rename nimbusware_* Python packages to short names (agent_core unchanged)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Longest names first so nimbusware_maker_web replaces before nimbusware_maker.
PACKAGE_RENAMES: tuple[tuple[str, str], ...] = (
    ("nimbusware_agent_tools", "agent_tools"),
    ("nimbusware_orchestrator", "orchestrator"),
    ("nimbusware_projections", "projections"),
    ("nimbusware_extensions", "extensions"),
    ("nimbusware_admin_ui", "admin_ui"),
    ("nimbusware_maker_web", "maker_web"),
    ("nimbusware_ui_shared", "ui_shared"),
    ("nimbusware_bootstrap", "bootstrap"),
    ("nimbusware_compute", "compute"),
    ("nimbusware_executor", "executor"),
    ("nimbusware_research", "research"),
    ("nimbusware_console", "console"),
    ("nimbusware_config", "config"),
    ("nimbusware_client", "client"),
    ("nimbusware_memory", "memory"),
    ("nimbusware_maker", "maker"),
    ("nimbusware_store", "store"),
    ("nimbusware_auth", "auth"),
    ("nimbusware_api", "api"),
    ("nimbusware_env", "env"),
    ("nimbusware_hw", "hw"),
    ("nimbusware_iam", "iam"),
    ("nimbusware_mcp", "mcp"),
)

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

SKIP_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".gz",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pdf",
}

TEXT_SUFFIXES = {
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".json",
    ".ps1",
    ".sh",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".html",
    ".css",
    ".txt",
    ".ini",
    ".cfg",
    ".env",
    ".service",
    ".Dockerfile",
    "",
}


def _should_skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in SKIP_FILE_SUFFIXES:
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    if path.name in {"Dockerfile", "Makefile", "LICENSE", "launcher.py"}:
        return True
    return False


def git_mv(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT, check=True)
    except subprocess.CalledProcessError:
        shutil.move(str(src), str(dst))
        subprocess.run(["git", "add", "-A", str(dst)], cwd=ROOT, check=True)
        if src.exists():
            shutil.rmtree(src, ignore_errors=True)
        subprocess.run(["git", "add", "-A", str(src.parent)], cwd=ROOT, check=True)


def rename_directories() -> None:
    packages = ROOT / "packages"
    for old, new in PACKAGE_RENAMES:
        src = packages / old
        if src.is_dir():
            git_mv(src, packages / new)
    inner = packages / "bootstrap" / "nimbusware_bootstrap"
    if inner.is_dir():
        git_mv(inner, packages / "bootstrap" / "bootstrap")


def replace_in_text(text: str) -> tuple[str, bool]:
    changed = False
    for old, new in PACKAGE_RENAMES:
        if old in text:
            text = text.replace(old, new)
            changed = True
    return text, changed


def rewrite_files() -> int:
    updated = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or _should_skip_dir(path):
            continue
        if not _is_text_file(path):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new_text, changed = replace_in_text(original)
        if changed:
            path.write_text(new_text, encoding="utf-8")
            updated += 1
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirs-only", action="store_true")
    parser.add_argument("--text-only", action="store_true")
    args = parser.parse_args()

    if not args.text_only:
        rename_directories()
        print("renamed package directories")
    if not args.dirs_only:
        count = rewrite_files()
        print(f"updated {count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
