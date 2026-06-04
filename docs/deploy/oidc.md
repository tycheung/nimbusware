# OIDC for Admin Console (Lane V5 design)

## Scope

Enterprise operators may want SSO for the **Admin Console** and **Maker** web apps. The Nimbusware **API** continues to authenticate via:

- Individual: open user routes on loopback; `X-Nimbusware-Admin-Token` for admin routes.
- Enterprise: `X-Nimbusware-Api-Key` with `maker_user` / `maker_admin` scopes.

OIDC is a **console login** concern, not a replacement for API keys in v1.

## Proposed flow

1. Operator opens Admin Console → redirect to IdP (OIDC authorization code + PKCE).
2. Console callback validates JWT (`iss`, `aud`, `exp`, groups claim).
3. Console maps IdP groups → local role (`maker_admin` vs read-only).
4. Console stores a short-lived session cookie; backend calls still use server-side API key or token vault — **never** embed IdP tokens in browser-local storage for API calls.

## Implementation checklist (fo500)

- [x] Register OIDC client with redirect URI for Admin Console (`NIMBUSWARE_OIDC_REDIRECT_URI` or `{NIMBUSWARE_ADMIN_CONSOLE_URL}/oauth/callback`).
- [x] Configure `NIMBUSWARE_OIDC_ENABLED`, `NIMBUSWARE_OIDC_ISSUER`, `NIMBUSWARE_OIDC_CLIENT_ID`, optional `NIMBUSWARE_OIDC_CLIENT_SECRET`.
- [x] Admin Console PKCE authorize flow in `nimbusware_console.admin_gate` (enterprise edition only).
- [ ] Map IdP groups claim → `maker_admin` vs read-only console session (future).
- [x] Keep API calls on server-side `X-Nimbusware-Api-Key` / admin token — OIDC does not replace API keys.
- [ ] Document session TTL and logout in runbook (future).

Code: [`packages/nimbusware_env/oidc_config.py`](../../packages/nimbusware_env/oidc_config.py), [`packages/nimbusware_console/services/oauth_pkce.py`](../../packages/nimbusware_console/services/oauth_pkce.py).

## Non-goals (V5)

- Full OIDC middleware inside FastAPI (defer until product prioritizes).
- Replacing `nimbusware_iam` Postgres API keys for machine clients.

## Implementation hooks

- `nimbusware_env.admin_token` — keep loopback guard for dev token.
- Enterprise IAM — tenant-scoped API keys remain authoritative for `/v1`.
- Future: `NIMBUSWARE_OIDC_*` env vars documented here when implemented.
