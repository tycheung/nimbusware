#!/usr/bin/env python3
"""Entry point wrapper — implementation in scripts/install/install_nimbusware.py.

Prefer curling ``scripts/install/install_nimbusware.py`` for remote bootstrap; this
wrapper only works from a real checkout (it cannot be piped via stdin).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "install" / "install_nimbusware.py"

if __name__ == "__main__":
    if not _TARGET.is_file():
        print(
            "ERROR: cannot find scripts/install/install_nimbusware.py.\n"
            "If you curled this wrapper via stdin, use:\n"
            "  https://raw.githubusercontent.com/tycheung/nimbusware/main/"
            "scripts/install/install_nimbusware.py",
            file=sys.stderr,
        )
        raise SystemExit(2)
    raise SystemExit(subprocess.call([sys.executable, str(_TARGET), *sys.argv[1:]]))
