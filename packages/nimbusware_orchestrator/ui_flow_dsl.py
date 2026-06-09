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

LocatorStrategy = Literal["css", "role", "testid", "label", "text"]


@dataclass(frozen=True)
class UiLocator:
    strategy: LocatorStrategy = "css"
    value: str | None = None
    role: str | None = None
    name: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | str | None) -> UiLocator | None:
        if raw is None:
            return None
        if isinstance(raw, str):
            return cls(strategy="css", value=raw)
        strategy = str(raw.get("strategy") or "css")
        return cls(
            strategy=strategy,  # type: ignore[arg-type]
            value=raw.get("value"),
            role=raw.get("role"),
            name=raw.get("name"),
        )

    def css_selector(self) -> str | None:
        if self.strategy == "css":
            return self.value
        return None


@dataclass(frozen=True)
class UiFlowStep:
    kind: UiStepKind
    selector: str | None = None
    locator: UiLocator | None = None
    value: str | None = None
    url: str | None = None
    timeout_ms: int = 5000

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UiFlowStep:
        kind = str(raw.get("kind") or raw.get("action") or "goto")
        locator_raw = raw.get("locator")
        locator = UiLocator.from_dict(locator_raw) if locator_raw else None
        selector = raw.get("selector")
        if selector and locator is None:
            locator = UiLocator(strategy="css", value=str(selector))
        return cls(
            kind=kind,  # type: ignore[arg-type]
            selector=str(selector) if selector else None,
            locator=locator,
            value=raw.get("value") or raw.get("text"),
            url=raw.get("url") or raw.get("path"),
            timeout_ms=int(raw.get("timeout_ms") or raw.get("timeout") or 5000),
        )

    def effective_locator(self) -> UiLocator:
        if self.locator is not None:
            return self.locator
        if self.selector:
            return UiLocator(strategy="css", value=self.selector)
        return UiLocator(strategy="css", value="body")


@dataclass
class UiFlowDefinition:
    flow_id: str
    steps: list[UiFlowStep] = field(default_factory=list)
    label: str = ""
    prompt_id: str | None = None
    base: str = "frontend"

    @classmethod
    def from_dict(cls, flow_id: str, raw: dict[str, Any]) -> UiFlowDefinition:
        steps_raw = raw.get("steps") or []
        steps = [UiFlowStep.from_dict(s) for s in steps_raw if isinstance(s, dict)]
        return cls(
            flow_id=str(raw.get("id") or flow_id),
            steps=steps,
            label=str(raw.get("label") or ""),
            prompt_id=raw.get("prompt_id"),
            base=str(raw.get("base") or "frontend"),
        )


def load_ui_flow(flow_id: str, raw: dict[str, Any]) -> UiFlowDefinition:
    return UiFlowDefinition.from_dict(flow_id, raw)


DEFAULT_TINY_WEB_LOGIN_FLOW = UiFlowDefinition(
    flow_id="tiny_web_smoke",
    steps=[
        UiFlowStep(kind="goto", url="/"),
        UiFlowStep(
            kind="expect_text", locator=UiLocator(strategy="css", value="body"), value="Welcome"
        ),
        UiFlowStep(kind="click", locator=UiLocator(strategy="css", value='a[href="contact.html"]')),
        UiFlowStep(kind="expect_visible", locator=UiLocator(strategy="css", value="form")),
    ],
)

DEFAULT_KEYBOARD_NAV_FLOW = UiFlowDefinition(
    flow_id="keyboard_nav_smoke",
    steps=[
        UiFlowStep(kind="goto", url="/"),
        UiFlowStep(kind="press", locator=UiLocator(strategy="css", value="body"), value="Tab"),
        UiFlowStep(kind="press", locator=UiLocator(strategy="css", value="body"), value="Enter"),
    ],
)
