from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


class StandardsConnector(ABC):
    connector_id: str

    @abstractmethod
    def scan(self, *, workspace: Path, params: dict[str, Any]) -> CheckResult:
        raise NotImplementedError

    def poll_quality_gate(self, *, workspace: Path, params: dict[str, Any]) -> CheckResult | None:
        return None
