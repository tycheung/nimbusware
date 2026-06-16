from __future__ import annotations

from pathlib import Path

from nimbusware_client.http import api_base as default_api_base
from nimbusware_env.env_flags import nimbusware_repo_root_path

API_BASE = default_api_base()


def repo_root() -> Path:
    return nimbusware_repo_root_path()
