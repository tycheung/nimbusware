# Collaborative chat (v1.2 Track B)

Multi-human **peanut gallery** for Maker Chat sessions. See [ADR 023](adr/023-collaborative-chat-sessions.md) and the [threat model](collaborative-chat-threat-model.md).

## Enable

Set `NIMBUSWARE_COLLAB_ENABLED=1` in `.env` and restart the API. Non-loopback hosts then require sign-in (`POST /v1/auth/signup|signin`) or `X-Nimbusware-Admin-Token`.

## Roles

| Role | Watch theater | Comment / interject | Invite / admin |
|------|:-------------:|:-------------------:|:--------------:|
| `session_read` | ✓ | ✗ | ✗ |
| `session_write` | ✓ | ✓ | ✗ |
| `session_admin` | ✓ | ✓ | ✓ |

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/auth/signup` | Create local user (first user becomes owner) |
| POST | `/v1/auth/signin` | Session cookie |
| GET | `/v1/chat/sessions/{id}/participants` | List participants |
| POST | `/v1/chat/sessions/{id}/invites` | Create join link |
| POST | `/v1/chat/join` | Redeem invite token |
| GET | `/v1/chat/sessions/{id}/stream` | Session SSE theater fan-out (0.5s poll, capped backlog) |

## Individual deployment

Share the join URL from the Chat **Invite** action. Guests open `#/chat/join/{token}` in Maker — sign in or create an account, then the app redeems the token via `POST /v1/chat/join` and redirects to `#/chat?session_id=…`.

### Maker UI modules

| Module | Responsibility |
|--------|----------------|
| `chat.js` | Session lifecycle, form submit, run start |
| `chat_shell_html.js` | Layout markup |
| `chat_collab_wiring.js` | Collab session stream + host transfer wiring |
| `chat_join.js` | `#/chat/join/{token}` sign-in + redeem |
| `chat_session_ui.js` | Participants strip, session sidebar, compute nodes |
| `chat_branch_ui.js` | Conversation branch tree |

## Enterprise

Use `GET /v1/enterprise/users?q=` for directory search. Tenant policy: `GET/PUT /v1/enterprise/collab-policy` (`allow_external_collaborators`, `max_session_participants`, `host_transfer_consent_hours`).

## Conversation library (B8)

Session `metadata.folder` and `metadata.tags` organize many sessions per project. Full folder CRUD is documented in [conversation-library.md](conversation-library.md).

## Host transfer (shipped)

Request/accept flow with **session freeze**, artifact bundle export/import, and Postgres `nimbusware_host_transfer_request` (in-memory when no DB). See [compute-mesh.md](compute-mesh.md) host-transfer APIs.

## Related

- [Compute mesh](compute-mesh.md) — optional GPU sharing per session
- [Host transfer ADR](adr/026-host-transfer.md)
- [External webhook boundary](integrations-external-chat.md)
