"""PostgreSQL configuration authority + materialization (plan §19.5)."""

from nimbusware_config.flags import config_from_db_enabled
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo, seed_t2_policy_documents_from_repo
from nimbusware_config.store import InMemoryConfigStore, PostgresConfigStore

__all__ = [
    "ConfigMaterializer",
    "InMemoryConfigStore",
    "PostgresConfigStore",
    "config_from_db_enabled",
    "seed_config_from_repo",
    "seed_t2_policy_documents_from_repo",
]
