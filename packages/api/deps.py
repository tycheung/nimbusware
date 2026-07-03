from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from auth.store import CollabStore, UserStore
from iam.store import InMemoryIamStore, PostgresIamStore
from maker.chat_library_store import ChatLibraryStore
from maker.chat_store import InMemoryChatStore, PostgresChatStore
from maker.host_transfer_store import HostTransferStore
from maker.optimizer_weights_store import OptimizerWeightsStore
from maker.store import InMemoryProjectStore, PostgresProjectStore
from orchestrator.pipeline import RunOrchestrator
from store.protocol import EventStore

IamStore = InMemoryIamStore | PostgresIamStore
ProjectStore = InMemoryProjectStore | PostgresProjectStore
ChatStore = InMemoryChatStore | PostgresChatStore


def get_store(request: Request) -> EventStore:
    return cast(EventStore, request.app.state.store)


def get_orchestrator(request: Request) -> RunOrchestrator:
    return cast(RunOrchestrator, request.app.state.orchestrator)


def get_iam_store(request: Request) -> IamStore:
    return cast(IamStore, request.app.state.iam_store)


def get_project_store(request: Request) -> ProjectStore:
    return cast(ProjectStore, request.app.state.project_store)


def get_chat_store(request: Request) -> ChatStore:
    return cast(ChatStore, request.app.state.chat_store)


def get_user_store(request: Request) -> UserStore:
    return cast(UserStore, request.app.state.user_store)


def get_collab_store(request: Request) -> CollabStore:
    return cast(CollabStore, request.app.state.collab_store)


def get_chat_library_store(request: Request) -> ChatLibraryStore:
    return cast(ChatLibraryStore, request.app.state.chat_library_store)


def get_host_transfer_store(request: Request) -> HostTransferStore:
    return cast(HostTransferStore, request.app.state.host_transfer_store)


def get_optimizer_weights_store(request: Request) -> OptimizerWeightsStore:
    return cast(OptimizerWeightsStore, request.app.state.optimizer_weights_store)


StoreDep = Annotated[EventStore, Depends(get_store)]
OrchDep = Annotated[RunOrchestrator, Depends(get_orchestrator)]
IamStoreDep = Annotated[IamStore, Depends(get_iam_store)]
ProjectStoreDep = Annotated[ProjectStore, Depends(get_project_store)]
ChatStoreDep = Annotated[ChatStore, Depends(get_chat_store)]
UserStoreDep = Annotated[UserStore, Depends(get_user_store)]
CollabStoreDep = Annotated[CollabStore, Depends(get_collab_store)]
ChatLibraryStoreDep = Annotated[ChatLibraryStore, Depends(get_chat_library_store)]
HostTransferStoreDep = Annotated[HostTransferStore, Depends(get_host_transfer_store)]
OptimizerWeightsStoreDep = Annotated[OptimizerWeightsStore, Depends(get_optimizer_weights_store)]
