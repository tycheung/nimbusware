from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PutE2EVerdict = Literal["PASS", "FAIL", "SKIP"]


@dataclass(frozen=True)
class PutE2EFinding:
    kind: str
    message: str
    surface_path: str | None = None
    severity: str = "operational"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "message": self.message,
            "severity": self.severity,
        }
        if self.surface_path:
            payload["surface_path"] = self.surface_path
        return payload


@dataclass
class PutE2EResult:
    verdict: PutE2EVerdict
    flow_id: str
    base_url: str
    detail: str = ""
    exit_code: int | None = None
    exercised_paths: set[str] = field(default_factory=set)
    findings: list[PutE2EFinding] = field(default_factory=list)
    capture: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool | None:
        if self.verdict == "PASS":
            return True
        if self.verdict == "FAIL":
            return False
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "flow_id": self.flow_id,
            "base_url": self.base_url,
            "detail": self.detail,
            "exit_code": self.exit_code,
            "exercised_paths": sorted(self.exercised_paths),
            "findings": [f.to_dict() for f in self.findings],
            "capture": self.capture,
            "passed": self.passed,
        }
