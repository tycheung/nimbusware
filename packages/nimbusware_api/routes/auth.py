from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, UserStoreDep
from nimbusware_api.errors import problem
from nimbusware_auth.crypto import verify_password
from nimbusware_auth.models import UserRecord
from nimbusware_auth.session_cookie import (
    clear_auth_session_cookie,
    set_auth_session_cookie,
    user_id_from_request,
)
from nimbusware_env.env_flags import nimbusware_collab_enabled

router = APIRouter(prefix="/auth", tags=["maker"])


class SignupBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(default="", max_length=120)


class SigninBody(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    is_owner: bool = False
    created_at: str


def _user_response(user: UserRecord) -> UserResponse:
    pub = user.to_public_dict()
    return UserResponse(
        user_id=str(pub["user_id"]),
        username=str(pub["username"]),
        display_name=str(pub["display_name"]),
        is_owner=bool(pub.get("is_owner")),
        created_at=str(pub["created_at"]),
    )


def get_optional_user(
    request: Request,
    user_store: UserStoreDep,
) -> UserRecord | None:
    uid = user_id_from_request(request)
    if uid is None:
        return None
    return user_store.get_user(uid)


OptionalUserDep = Annotated[UserRecord | None, Depends(get_optional_user)]


def get_required_user(
    user: OptionalUserDep,
) -> UserRecord:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "sign in required"),
        )
    return user


AuthUserDep = Annotated[UserRecord, Depends(get_required_user)]


def _bootstrap_migrate_sessions(
    user_store: UserStoreDep,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    owner: UserRecord,
) -> None:
    if user_store.count_users() != 1:
        return
    for session in getattr(chat_store, "_sessions", {}).values():
        if session.host_user_id is None:
            chat_store.update_session(session.session_id, host_user_id=owner.user_id)
            collab_store.add_participant(
                session_id=session.session_id,
                user_id=owner.user_id,
                role="session_admin",
            )


@router.post("/signup", response_model=UserResponse)
def auth_signup(
    body: SignupBody,
    response: Response,
    user_store: UserStoreDep,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
) -> UserResponse:
    if not nimbusware_collab_enabled():
        raise HTTPException(
            status_code=403,
            detail=problem(
                "collab_disabled",
                "collaborative chat is disabled (set NIMBUSWARE_COLLAB_ENABLED=1)",
            ),
        )
    try:
        user = user_store.create_user(
            username=body.username,
            password=body.password,
            display_name=body.display_name,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "username_taken":
            raise HTTPException(
                status_code=409,
                detail=problem("username_taken", "username already exists"),
            ) from exc
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", code),
        ) from exc
    _bootstrap_migrate_sessions(user_store, chat_store, collab_store, user)
    set_auth_session_cookie(response, user_id=user.user_id)
    return _user_response(user)


@router.post("/signin", response_model=UserResponse)
def auth_signin(
    body: SigninBody,
    response: Response,
    user_store: UserStoreDep,
) -> UserResponse:
    if not nimbusware_collab_enabled():
        raise HTTPException(
            status_code=403,
            detail=problem(
                "collab_disabled",
                "collaborative chat is disabled (set NIMBUSWARE_COLLAB_ENABLED=1)",
            ),
        )
    user = user_store.get_user_by_username(body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "invalid username or password"),
        )
    set_auth_session_cookie(response, user_id=user.user_id)
    return _user_response(user)


@router.post("/signout")
def auth_signout(response: Response) -> dict[str, bool]:
    clear_auth_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def auth_me(user: AuthUserDep) -> UserResponse:
    return _user_response(user)
