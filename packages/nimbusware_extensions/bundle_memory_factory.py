from __future__ import annotations

from nimbusware_env.env_flags import nimbusware_database_url
from nimbusware_extensions.bundle_memory import (
    BundleOutcomeStore,
    InMemoryBundleOutcomeStore,
    PostgresBundleOutcomeStore,
)


def build_bundle_outcome_store(
    conninfo: str | None = None,
    *,
    allow_in_memory: bool = False,
) -> BundleOutcomeStore | None:
    url = (conninfo or nimbusware_database_url() or "").strip()
    if url:
        return PostgresBundleOutcomeStore(url)
    if allow_in_memory:
        return InMemoryBundleOutcomeStore()
    return None
