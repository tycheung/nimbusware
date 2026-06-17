#!/usr/bin/env python3
"""Entry point wrapper — implementation in scripts/install/install_nimbusware.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "install" / "install_nimbusware.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(_TARGET), *sys.argv[1:]]))
