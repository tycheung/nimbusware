from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request


def get_store(request: Request) -> Any:
    return request.app.state.store


def get_orchestrator(request: Request) -> Any:
    return request.app.state.orchestrator


StoreDep = Annotated[Any, Depends(get_store)]
OrchDep = Annotated[Any, Depends(get_orchestrator)]
