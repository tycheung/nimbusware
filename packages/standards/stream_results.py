from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from standards.verdict import VerdictMode


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    passed: bool
    verdict: VerdictMode
    detail: str = ""
    exit_code: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "verdict": self.verdict,
            "detail": self.detail,
            "exit_code": self.exit_code,
        }


@dataclass
class StreamResult:
    stream_id: str
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
        }
