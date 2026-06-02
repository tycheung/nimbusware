from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from hermes_orchestrator.pipeline import RunOrchestrator
from hermes_store.protocol import EventStore
from nimbusware_iam.store import InMemoryIamStore, PostgresIamStore
from nimbusware_maker.store import InMemoryProjectStore, PostgresProjectStore

IamStore = InMemoryIamStore | PostgresIamStore
ProjectStore = InMemoryProjectStore | PostgresProjectStore


def get_store(request: Request) -> EventStore:
    return cast(EventStore, request.app.state.store)


def get_orchestrator(request: Request) -> RunOrchestrator:
    return cast(RunOrchestrator, request.app.state.orchestrator)


def get_iam_store(request: Request) -> IamStore:
    return cast(IamStore, request.app.state.iam_store)


def get_project_store(request: Request) -> ProjectStore:
    return cast(ProjectStore, request.app.state.project_store)


StoreDep = Annotated[EventStore, Depends(get_store)]
OrchDep = Annotated[RunOrchestrator, Depends(get_orchestrator)]
IamStoreDep = Annotated[IamStore, Depends(get_iam_store)]
ProjectStoreDep = Annotated[ProjectStore, Depends(get_project_store)]
