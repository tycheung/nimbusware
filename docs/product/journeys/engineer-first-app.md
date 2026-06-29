# Engineer workspace — first full-stack app

Build a todo app with web UI and REST API as a solo operator or with a small collab session. Collab-ready presets, **solo hat** routing when working alone, and `@discipline` mentions when teaming up.

## Prerequisites

1. Install with `--setup-bundle default`.
2. Open Maker and choose **Engineer workspace** in the archetype picker (enables collab in Settings).
3. Confirm project readiness on **Home**.

## Journey steps

### 1. Wear a solo hat (Chat, optional)

When working alone, pick a **Solo hat** chip above the composer (PM, Architect, Frontend, Backend, QA, DevOps). Messages route feedback like `@frontend` without typing mentions. Clear with **Broadcast**.

First visit shows a dismissible coach hint; preference persists in `localStorage` (`maker_solo_discipline`).

Settings → **Solo discipline hat** mirrors the same choice.

### 2. Start discovery (Chat)

1. From Home, choose **Build an app** or open Chat with work type **campaign**.
2. Prompt: *Build a todo app with web UI and API*.
3. Complete scope discovery or **Recommend for me**.
4. **Approve manifest** on the plain-language card.

### 3. Plan and steer (Plan)

- Backlog tree shows **API**, **Web**, **Contract**, and optional **Deploy** surface badges.
- Active slice highlight and maintenance countdown.
- Steer with `@web` / `@api` or `[steer:web]` from Progress when a run is active.

### 4. Collab optional (Chat)

Enable collab in Settings or use the preset. Then:

- Invite teammates — templates from `configs/collab/invite_templates.yaml`.
- Join discipline picker assigns PM/architect/frontend/backend/QA/DevOps.
- `@frontend`, `@qa`, etc. route to the interjection queue on active runs.
- Mesh campaigns parallelize surface slices when ≥2 participants hold role claims.

See [collaborative-chat.md](../../collaborative-chat.md).

### 5. Progress and deploy (Progress / Review)

- Deploy cockpit: validate, approve, apply, smoke, rollback, environment selector.
- Live API/web links when deploy stages publish URLs.
- Review deploy audit timeline when `deploy` surface is in the manifest.

## Solo vs collab routing

| Mode | How feedback routes |
|------|---------------------|
| Solo hat active | `solo_discipline_routes` on requirements — no `@` needed |
| `@mention` in message | Explicit discipline routing (overrides solo hat for that line) |
| Collab session | Participant discipline + role claims on roster |

## Next steps

- [collaborative-chat.md](../../collaborative-chat.md) — disciplines and overlays
- [ide-bridge.md](../../ide-bridge.md) — VS Code `@` parity
- [deploy.md](../deploy.md) — Terraform and smoke gates
