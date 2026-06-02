# OIDC for Admin Console (Lane V5 design)

## Scope

Enterprise operators may want SSO for the **Admin Console** and **Maker** Streamlit apps. The Nimbusware **API** continues to authenticate via:

- Individual: open user routes on loopback; `X-Nimbusware-Admin-Token` for admin routes.
- Enterprise: `X-Nimbusware-Api-Key` with `maker_user` / `maker_admin` scopes.

OIDC is a **console login** concern, not a replacement for API keys in v1.

## Proposed flow

1. Operator opens Admin Console → redirect to IdP (OIDC authorization code + PKCE).
2. Console callback validates JWT (`iss`, `aud`, `exp`, groups claim).
3. Console maps IdP groups → local role (`maker_admin` vs read-only).
4. Console stores a short-lived session cookie; backend calls still use server-side API key or token vault — **never** embed IdP tokens in Streamlit state sent to browsers for API calls.

## Implementation checklist (Lane W5 fo746)

- [ ] Register OIDC client with redirect URI for Admin Console (`NIMBUSWARE_ADMIN_CONSOLE_URL/oauth/callback`).
- [ ] Configure `NIMBUSWARE_OIDC_ISSUER`, `NIMBUSWARE_OIDC_CLIENT_ID`, `NIMBUSWARE_OIDC_CLIENT_SECRET` (or PKCE public client).
- [ ] Map IdP groups claim → `maker_admin` vs read-only console session.
- [ ] Keep API calls on server-side `X-Nimbusware-Api-Key` / admin token — do not forward IdP access tokens to `/v1`.
- [ ] Document session TTL and logout in runbook.

**Definition of done (Lane X3):** checklist items are implemented in code/config and linked from deploy runbooks; this doc remains design guidance until those links are populated.

## Non-goals (V5)

- Full OIDC middleware inside FastAPI (defer until product prioritizes).
- Replacing `nimbusware_iam` Postgres API keys for machine clients.

## Implementation hooks

- `nimbusware_env.admin_token` — keep loopback guard for dev token.
- Enterprise IAM — tenant-scoped API keys remain authoritative for `/v1`.
- Future: `NIMBUSWARE_OIDC_*` env vars documented here when implemented.
