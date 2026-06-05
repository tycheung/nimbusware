"""Factory for bundle outcome persistence."""

from __future__ import annotations

import os

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
    url = (conninfo or os.environ.get("NIMBUSWARE_DATABASE_URL", "")).strip()
    if url:
        return PostgresBundleOutcomeStore(url)
    if allow_in_memory:
        return InMemoryBundleOutcomeStore()
    return None
