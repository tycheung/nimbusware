from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatLibraryStoreDep, ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.chat_common import require_collab_enabled, session_or_404
from nimbusware_auth.permissions import require_session_participant
from nimbusware_maker.chat_acl import effective_session_role

router = APIRouter(prefix="/chat", tags=["maker"])


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
    session_or_404(chat_store, session_id)
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
    sess = session_or_404(chat_store, session_id)
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
