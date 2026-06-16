from __future__ import annotations

from pathlib import Path

from nimbusware_config import ConfigMaterializer, config_from_db_enabled
from nimbusware_env.env_flags import nimbusware_database_url


def console_config_materializer(repo_root: Path) -> ConfigMaterializer | None:
    if not config_from_db_enabled():
        return None
    if not nimbusware_database_url():
        return None
    return ConfigMaterializer(repo_root)
