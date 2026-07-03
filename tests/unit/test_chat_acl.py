from maker.chat.acl import effective_session_role, max_participant_role


def test_max_participant_role_picks_highest() -> None:
    assert max_participant_role("session_read", "session_write") == "session_write"
    assert max_participant_role("session_admin", "session_write") == "session_admin"
    assert max_participant_role(None, "session_read") == "session_read"


def test_effective_session_role_merges_scopes() -> None:
    role = effective_session_role(
        direct_role="session_read",
        session_grant_roles=[],
        folder_grant_roles=["session_write"],
        tag_grant_roles=[],
    )
    assert role == "session_write"
