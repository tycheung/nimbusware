"""Load Nimbusware repository environment (``.env``), including Hermes agent settings."""

from nimbusware_env.dotenv import find_repo_root, load_dotenv, set_env_var
from nimbusware_env.edition import (
    ENV_EDITION,
    DEFAULT_EDITION,
    ENTERPRISE_EDITION,
    edition,
    edition_manifest,
    enterprise_feature_enabled,
    enterprise_install_hints,
    is_enterprise,
    is_individual,
    normalize_edition,
    require_enterprise_feature,
)

__all__ = [
    "DEFAULT_EDITION",
    "ENTERPRISE_EDITION",
    "ENV_EDITION",
    "edition",
    "edition_manifest",
    "enterprise_feature_enabled",
    "enterprise_install_hints",
    "find_repo_root",
    "is_enterprise",
    "is_individual",
    "load_dotenv",
    "normalize_edition",
    "require_enterprise_feature",
    "set_env_var",
]
