from __future__ import annotations

import os
from pathlib import Path

_iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
