from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ConfigDocumentRow:
    namespace: str
    document_key: str
    version: int
    content: dict[str, Any]
    content_sha256_16: str
    updated_at: datetime | None = None


@runtime_checkable
class ConfigStore(Protocol):
    def get(self, namespace: str, document_key: str) -> ConfigDocumentRow | None:
        """Return the document or ``None`` when missing."""

    def upsert(
        self,
        namespace: str,
        document_key: str,
        content: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> ConfigDocumentRow:
        """Insert or replace content; bump row ``version`` on each successful write."""

    def list_keys(self, namespace: str) -> list[str]:
        """Document keys under ``namespace``."""

    def delete(self, namespace: str, document_key: str) -> bool:
        """Remove a document; return whether a row existed."""
