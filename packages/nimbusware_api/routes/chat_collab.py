from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatLibraryStoreDep, ChatStoreDep, CollabStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.chat_common import ChatMessageResponse, require_collab_enabled
from nimbusware_api.routes.chat_common import session_or_404 as _session_or_404
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep, maker_user_id_str
from nimbusware_auth.permissions import require_session_participant
from nimbusware_maker.chat_acl import effective_session_role
from nimbusware_orchestrator.model_binding_audit import (
    RoleClaimConflictError,
    assert_role_claim_available,
)
from nimbusware_orchestrator.model_binding_swap import (
    append_model_binding_override,
    append_role_claim,
    append_role_release,
)

router = APIRouter(prefix="/chat", tags=["maker"])


class SessionModelBindingSwapBody(BaseModel):
    run_id: UUID
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    provider_kind: str = Field(default="local", pattern="^(local|cloud)$")
    model_id: str = Field(min_length=1, max_length=200)


@router.post(
    "/sessions/{session_id}/model-bindings/swap",
    response_model=ChatMessageResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def session_model_binding_swap(
    session_id: UUID,
    body: SessionModelBindingSwapBody,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
) -> ChatMessageResponse:
    _session_or_404(chat_store, session_id)
    if not store.list_run_events(str(body.run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    payload = append_model_binding_override(
        store,
        body.run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        provider_kind=body.provider_kind,
        model_id=body.model_id,
    )
    label = f"{body.agent_role} â†’ {body.model_id} ({body.provider_id})"
    turn = chat_store.append_turn(
        session_id,
        role="system",
        text=f"Model swap: {label}",
        payload={"model_swap": payload},
    )
    message = {
        "role": "system",
        "text": turn.text,
        "turn_id": str(turn.turn_id),
        "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
        "model_swap": payload,
    }
    return ChatMessageResponse(
        message=message,
        classification={"work_type": "system", "rationale": "model_swap"},
        turn=turn.to_dict(),
    )


class SessionRoleClaimBody(BaseModel):
    run_id: UUID
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=200)


@router.post("/sessions/{session_id}/role-claims")
def session_role_claim(
    session_id: UUID,
    body: SessionRoleClaimBody,
    chat_store: ChatStoreDep,
    store: StoreDep,
    request: Request,
    _user: UserDep,
) -> dict[str, Any]:
    _session_or_404(chat_store, session_id)
    if not store.list_run_events(str(body.run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    rows = store.list_run_events(str(body.run_id))
    claimer = maker_user_id_str(request)
    try:
        assert_role_claim_available(
            rows,
            agent_role=body.agent_role,
            claimer_user_id=claimer,
        )
    except RoleClaimConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=problem(
                "role_claim_conflict",
                f"Role {body.agent_role} is already claimed",
                details={"existing_claimer": exc.existing_claimer},
            ),
        ) from exc
    payload = append_role_claim(
        store,
        body.run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        model_id=body.model_id,
        claimer_user_id=claimer,
    )
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Role claimed: {body.agent_role} â†’ {body.model_id}",
        payload={"role_claim": payload},
    )
    return {"ok": True, "event": "workload.role_claimed", "payload": payload}


@router.delete("/sessions/{session_id}/role-claims/{agent_role}")
def session_role_release(
    session_id: UUID,
    agent_role: str,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
    run_id: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any]:
    _session_or_404(chat_store, session_id)
    resolved_run_id = run_id
    if resolved_run_id is None:
        sess = chat_store.get_session(session_id)
        if sess is None:
            raise HTTPException(
                status_code=404,
                detail=problem("session_not_found", "session not found"),
            )
        resolved_run_id = sess.run_id
    if resolved_run_id is None or not store.list_run_events(str(resolved_run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found"),
        )
    payload = append_role_release(store, resolved_run_id, agent_role=agent_role)
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Role released: {agent_role}",
        payload={"role_release": payload},
    )
    return {"ok": True, "event": "workload.role_released", "payload": payload}


class FolderBody(BaseModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=120)
    parent_folder_id: UUID | None = None


class FolderPatchBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_folder_id: UUID | None = None


class GroupBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class GroupMemberBody(BaseModel):
    user_id: UUID


class AccessGrantBody(BaseModel):
    grantee_type: str
    scope_type: str
    participant_role: str = "session_read"
    grantee_user_id: UUID | None = None
    grantee_group_id: UUID | None = None
    folder_id: UUID | None = None
    tag: str | None = None
    session_id: UUID | None = None


class SessionLibraryBody(BaseModel):
    folder_id: UUID | None = None
    tags: list[str] | None = None


@router.get("/folders")
def list_folders(
    project_id: UUID,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    folders = library_store.list_folders(project_id=project_id)
    return {"folders": [f.to_dict() for f in folders]}


@router.post("/folders")
def create_folder(
    body: FolderBody,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    folder = library_store.create_folder(
        project_id=body.project_id,
        name=body.name,
        owner_user_id=user.user_id,
        parent_folder_id=body.parent_folder_id,
    )
    return {"folder": folder.to_dict()}


@router.patch("/folders/{folder_id}")
def patch_folder(
    folder_id: UUID,
    body: FolderPatchBody,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    folder = library_store.get_folder(folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail=problem("not_found", "folder not found"))
    if folder.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail=problem("forbidden", "folder owner required"))
    try:
        updated = library_store.update_folder(
            folder_id,
            name=body.name,
            parent_folder_id=body.parent_folder_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "folder not found"),
        ) from exc
    return {"folder": updated.to_dict()}


@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: UUID,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    folder = library_store.get_folder(folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail=problem("not_found", "folder not found"))
    if folder.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail=problem("forbidden", "folder owner required"))
    library_store.delete_folder(folder_id)
    return {"ok": True}


@router.get("/groups")
def list_groups(
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    groups = library_store.list_groups()
    return {"groups": [g.to_dict() for g in groups]}


@router.post("/groups")
def create_group(
    body: GroupBody,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    group = library_store.create_group(name=body.name, owner_user_id=user.user_id)
    return {"group": group.to_dict()}


@router.post("/groups/{group_id}/members")
def add_group_member(
    group_id: UUID,
    body: GroupMemberBody,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    try:
        library_store.add_group_member(group_id, body.user_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "group not found"),
        ) from exc
    return {"ok": True}


@router.get("/access-grants")
def list_access_grants(
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
    project_id: UUID | None = None,
    folder_id: UUID | None = None,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    require_collab_enabled()
    grants = library_store.list_grants(
        project_id=project_id,
        folder_id=folder_id,
        session_id=session_id,
    )
    return {"grants": [g.to_dict() for g in grants]}


@router.post("/access-grants")
def create_access_grant(
    body: AccessGrantBody,
    library_store: ChatLibraryStoreDep,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    if body.session_id is not None:
        require_session_participant(
            collab_store,
            session_id=body.session_id,
            user_id=user.user_id,
            minimum_role="session_admin",
        )
    try:
        grant = library_store.create_grant(
            grantee_type=body.grantee_type,
            scope_type=body.scope_type,
            participant_role=body.participant_role,
            created_by=user.user_id,
            grantee_user_id=body.grantee_user_id,
            grantee_group_id=body.grantee_group_id,
            folder_id=body.folder_id,
            tag=body.tag,
            session_id=body.session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return {"grant": grant.to_dict()}


@router.delete("/access-grants/{grant_id}")
def delete_access_grant(
    grant_id: UUID,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    if not library_store.delete_grant(grant_id):
        raise HTTPException(status_code=404, detail=problem("not_found", "grant not found"))
    return {"ok": True}


@router.put("/sessions/{session_id}/library")
def update_session_library(
    session_id: UUID,
    body: SessionLibraryBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=user.user_id,
        minimum_role="session_admin",
    )
    _session_or_404(chat_store, session_id)
    kw: dict[str, Any] = {}
    if "folder_id" in body.model_fields_set:
        kw["folder_id"] = body.folder_id
    if body.tags is not None:
        kw["tags"] = body.tags
    updated = chat_store.update_session(session_id, **kw)
    return {"session": updated.to_dict()}


@router.get("/sessions/{session_id}/effective-role")
def get_effective_role(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    library_store: ChatLibraryStoreDep,
    user: AuthUserDep,
    target_user_id: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any]:
    require_collab_enabled()
    sess = _session_or_404(chat_store, session_id)
    uid = target_user_id or user.user_id
    direct = collab_store.get_participant(session_id, uid)
    direct_role = direct.role if direct else None
    session_grants, folder_grants, tag_grants = library_store.grant_roles_for_user(
        user_id=uid,
        session_id=session_id,
        folder_id=sess.folder_id,
        tags=list(sess.tags),
    )
    role = effective_session_role(
        direct_role=direct_role,
        session_grant_roles=session_grants,
        folder_grant_roles=folder_grants,
        tag_grant_roles=tag_grants,
    )
    return {
        "user_id": str(uid),
        "effective_role": role,
        "direct_role": direct_role,
        "grant_roles": {
            "session": session_grants,
            "folder": folder_grants,
            "tag": tag_grants,
        },
    }
