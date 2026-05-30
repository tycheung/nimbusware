from __future__ import annotations

import os
from pathlib import Path

from nimbusware_client.http import api_base as default_api_base

API_BASE = default_api_base()


def repo_root() -> Path:
    return Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
