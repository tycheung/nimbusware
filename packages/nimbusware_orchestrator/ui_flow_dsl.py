"""UI flow step DSL for browser controller regression."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

UiStepKind = Literal[
    "goto",
    "click",
    "fill",
    "press",
    "select",
    "wait_for",
    "expect_text",
    "expect_visible",
]


@dataclass(frozen=True)
class UiFlowStep:
    kind: UiStepKind
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    timeout_ms: int = 5000

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UiFlowStep:
        kind = str(raw.get("kind") or raw.get("action") or "goto")
        return cls(
            kind=kind,  # type: ignore[arg-type]
            selector=raw.get("selector"),
            value=raw.get("value") or raw.get("text"),
            url=raw.get("url") or raw.get("path"),
            timeout_ms=int(raw.get("timeout_ms") or raw.get("timeout") or 5000),
        )


@dataclass
class UiFlowDefinition:
    flow_id: str
    steps: list[UiFlowStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, flow_id: str, raw: dict[str, Any]) -> UiFlowDefinition:
        steps_raw = raw.get("steps") or []
        steps = [UiFlowStep.from_dict(s) for s in steps_raw if isinstance(s, dict)]
        return cls(flow_id=flow_id, steps=steps)


DEFAULT_TINY_WEB_LOGIN_FLOW = UiFlowDefinition(
    flow_id="tiny_web_smoke",
    steps=[
        UiFlowStep(kind="goto", url="/"),
        UiFlowStep(kind="expect_text", selector="body", value="Welcome"),
        UiFlowStep(kind="click", selector='a[href="contact.html"]'),
        UiFlowStep(kind="expect_visible", selector="form"),
    ],
)

DEFAULT_KEYBOARD_NAV_FLOW = UiFlowDefinition(
    flow_id="keyboard_nav_smoke",
    steps=[
        UiFlowStep(kind="goto", url="/"),
        UiFlowStep(kind="press", selector="body", value="Tab"),
        UiFlowStep(kind="press", selector="body", value="Enter"),
    ],
)
