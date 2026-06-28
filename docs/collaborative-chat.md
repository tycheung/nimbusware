# Collaborative chat (v1.2 Track B)

Multi-human **peanut gallery** for Maker Chat sessions. See [ADR 023](adr/023-collaborative-chat-sessions.md) and the [threat model](collaborative-chat-threat-model.md).

## Enable

Enable collaborative chat on Individual installs without editing `.env`:

- **Engineer workspace** archetype preset calls `PUT /v1/platform/collab-settings` with `collab_enabled: true`
- **Settings → Collaborative chat** toggle (`GET/PUT /v1/platform/collab-settings`) flips runtime collab in-process

Legacy: set `NIMBUSWARE_COLLAB_ENABLED=1` in `.env` and restart the API. Non-loopback hosts then require sign-in (`POST /v1/auth/signup|signin`) or `X-Nimbusware-Admin-Token`.

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
| POST | `/v1/chat/sessions/{id}/invites` | Create join link (optional `recommended_discipline`) |
| GET | `/v1/chat/join-preview?token=` | Preview invite role + suggested discipline |
| POST | `/v1/chat/join` | Redeem invite token (optional `user_discipline`) |
| PUT | `/v1/chat/sessions/{id}/participants/me/discipline` | Update your discipline in this session |
| GET | `/v1/platform/collab-disciplines` | Discipline catalog (`configs/collab/disciplines.yaml`) |
| GET/PUT | `/v1/users/me/discipline-profile` | Default discipline when joining sessions |
| GET/PUT | `/v1/users/me/participant-context` | Expertise bullets (fo2186) shown on roster |
| GET/PUT | `/v1/users/me/agent-overlays/{discipline}` | Per-discipline prompt extensions merged when roles are claimed |
| GET | `/v1/chat/sessions/{id}/stream` | Session SSE theater fan-out (0.5s poll, capped backlog) |

## Disciplines (A2 team collab)

Each participant can wear a **discipline** (PM, architect, frontend, backend, QA, DevOps) mapped to agent taxonomy keys. The join flow shows a discipline picker; invites can suggest a discipline via template or `recommended_discipline`. Chat `@` mentions route targeted feedback to the run interjection queue when a session has an active run, and append **routed feedback** lines in the thread (`Alice → frontend_writer: …`). Per-user expertise bullets: `GET/PUT /v1/users/me/participant-context`. Per-discipline **agent overlays** (prompt extensions) save via Settings **My agent overlays** or `GET/PUT /v1/users/me/agent-overlays/{discipline}` and merge into slice prompts when that user claims the matching role; each save bumps a per-discipline **version** and appends `collab.agent_overlay.updated` to `.nimbusware/platform/collab_audit.jsonl`. Only one active claim per role per run — a second claim returns **409** and Chat shows **Taken** on the role chip.

Catalog: `configs/collab/disciplines.yaml`. Per-user default discipline: `configs/collab/users/{user_id}.yaml`. Agent overlays: `configs/collab/users/{user_id}_agent_overlays.yaml`. Remote mesh workers receive overlay text in work-unit payloads (`agent_overlay_prompt`) when the claimer holds a role. IDE clients can set discipline and overlays via MCP `nimbusware_set_discipline` and `nimbusware_update_agent_overlay` — see [ide-bridge.md](ide-bridge.md).

## Individual deployment

Share the join URL from the Chat **Invite** action. Guests open `#/chat/join/{token}` in Maker — sign in or create an account, then the app redeems the token via `POST /v1/chat/join` and redirects to `#/chat?session_id=…`.

### Maker UI modules

| Module | Responsibility |
|--------|----------------|
| `chat.js` | Session lifecycle, form submit, run start |
| `chat_session_lifecycle.js` | Load/ensure session, sidebar and library refresh |
| `chat_shell_html.js` | Layout markup |
| `chat_run_card_ui.js` | Run card DOM, theater lines in thread |
| `chat_collab_wiring.js` | Collab session stream + host transfer wiring |
| `chat_model_drawer_ui.js` | In-session role model swap drawer |
| `chat_invite_modal_ui.js` | Invite link / directory / group modal |
| `chat_join.js` | `#/chat/join/{token}` sign-in, discipline picker, redeem |
| `chat_mention_ui.js` | `@` discipline autocomplete in composer |
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
