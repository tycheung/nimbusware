from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request


def get_store(request: Request) -> Any:
    return request.app.state.store


def get_orchestrator(request: Request) -> Any:
    return request.app.state.orchestrator


def get_iam_store(request: Request) -> Any:
    return request.app.state.iam_store


def get_project_store(request: Request) -> Any:
    return request.app.state.project_store


StoreDep = Annotated[Any, Depends(get_store)]
OrchDep = Annotated[Any, Depends(get_orchestrator)]
IamStoreDep = Annotated[Any, Depends(get_iam_store)]
ProjectStoreDep = Annotated[Any, Depends(get_project_store)]
