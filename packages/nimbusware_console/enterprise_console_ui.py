from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from nimbusware_client.http import HTTPError
from nimbusware_console.enterprise_console import (
    SS_API_KEY,
    SS_EDITION_MANIFEST,
    SS_IAM_ME,
    SS_SELECTED_TENANT,
    SS_TENANT_KEYS,
    enterprise_console_feature_enabled,
    fetch_fleet_memory_status,
    fetch_fleet_preflight_aggregate,
    fetch_fleet_worker_health,
    fetch_iam_me,
    fetch_platform_edition,
    fetch_tenants,
    fleet_dashboard_export_filename_slug,
    fleet_dashboard_export_json,
    fleet_memory_status_table_rows,
    fleet_sli_aggregate_caption,
    fleet_worker_health_caption,
    is_enterprise_edition_manifest,
    register_tenant_api_key,
    resolve_active_api_key,
    tenant_select_options,
)


def _load_edition_manifest() -> dict[str, Any] | None:
    cached = st.session_state.get(SS_EDITION_MANIFEST)
    if isinstance(cached, dict):
        return cached
    try:
        manifest = fetch_platform_edition()
    except HTTPError:
        return None
    st.session_state[SS_EDITION_MANIFEST] = manifest
    return manifest


def render_enterprise_sidebar() -> bool:
    manifest = _load_edition_manifest()
    if not enterprise_console_feature_enabled(manifest):
        if is_enterprise_edition_manifest(manifest):
            st.sidebar.caption(
                "Enterprise edition detected; enterprise console surfaces are not enabled in this build."
            )
        return False

    st.sidebar.divider()
    st.sidebar.subheader("Enterprise")
    if st.sidebar.button("Refresh edition", key="hermes_enterprise_refresh_edition"):
        st.session_state.pop(SS_EDITION_MANIFEST, None)
        st.rerun()

    tenant_keys: dict[str, str] = dict(st.session_state.get(SS_TENANT_KEYS) or {})
    api_key_input = st.sidebar.text_input(
        "API key",
        type="password",
        key="hermes_enterprise_api_key_input",
        help=f"Tenant-scoped key ({SS_API_KEY} session). Required for fleet APIs.",
    )
    if st.sidebar.button("Connect", key="hermes_enterprise_connect"):
        if not api_key_input.strip():
            st.sidebar.warning("Enter an API key first.")
        else:
            try:
                me = fetch_iam_me(api_key=api_key_input.strip())
                st.session_state[SS_API_KEY] = api_key_input.strip()
                st.session_state[SS_IAM_ME] = me
                slug = str(me.get("tenant_slug", "")).strip()
                if slug:
                    st.session_state[SS_SELECTED_TENANT] = slug
                    tenant_keys = register_tenant_api_key(
                        tenant_keys,
                        tenant_slug=slug,
                        api_key=api_key_input.strip(),
                    )
                    st.session_state[SS_TENANT_KEYS] = tenant_keys
                st.sidebar.success(f"Connected as tenant `{slug or '?'}`")
            except HTTPError as exc:
                st.sidebar.error(f"IAM connect failed: {exc}")

    active_key = resolve_active_api_key(
        primary_key=st.session_state.get(SS_API_KEY),
        tenant_keys=tenant_keys,
        selected_tenant_slug=st.session_state.get(SS_SELECTED_TENANT),
    )
    tenant_options: list[tuple[str, str]] = []
    if active_key:
        try:
            tenants_body = fetch_tenants(api_key=active_key)
            tenant_options = tenant_select_options(tenants_body)
        except HTTPError:
            tenant_options = []

    if tenant_options:
        slugs = [s for s, _ in tenant_options]
        labels = {s: label for s, label in tenant_options}
        current = st.session_state.get(SS_SELECTED_TENANT)
        if current not in slugs:
            current = slugs[0]
        picked = st.sidebar.selectbox(
            "Tenant",
            options=slugs,
            index=slugs.index(current) if current in slugs else 0,
            format_func=lambda s: labels.get(s, s),
            key="hermes_enterprise_tenant_select",
        )
        st.session_state[SS_SELECTED_TENANT] = picked
        if picked and picked not in tenant_keys:
            st.sidebar.caption(f"No stored API key for `{picked}`. Save one below.")
        tenant_key_for_picked = st.sidebar.text_input(
            f"API key for `{picked}`",
            type="password",
            key=f"hermes_enterprise_tenant_key_{picked}",
        )
        if st.sidebar.button(
            f"Save key for `{picked}`",
            key=f"hermes_enterprise_save_tenant_key_{picked}",
        ):
            if tenant_key_for_picked.strip():
                tenant_keys = register_tenant_api_key(
                    tenant_keys,
                    tenant_slug=picked,
                    api_key=tenant_key_for_picked.strip(),
                )
                st.session_state[SS_TENANT_KEYS] = tenant_keys
                st.sidebar.success(f"Stored API key for `{picked}`")
            else:
                st.sidebar.warning("Key cannot be empty.")

    me = st.session_state.get(SS_IAM_ME)
    if isinstance(me, dict):
        st.sidebar.caption(
            f"Active tenant: `{me.get('tenant_slug', '?')}` "
            f"(key `{str(me.get('key_id', ''))[:8]}…`)"
        )
    return True


def render_enterprise_fleet_dashboard() -> None:
    manifest = st.session_state.get(SS_EDITION_MANIFEST)
    if not enterprise_console_feature_enabled(manifest):
        return

    tenant_keys: dict[str, str] = dict(st.session_state.get(SS_TENANT_KEYS) or {})
    api_key = resolve_active_api_key(
        primary_key=st.session_state.get(SS_API_KEY),
        tenant_keys=tenant_keys,
        selected_tenant_slug=st.session_state.get(SS_SELECTED_TENANT),
    )
    with st.expander("Enterprise fleet dashboard", expanded=False):
        st.caption(
            "Tenant-scoped fleet memory, Ollama SLI preflight aggregate, and Redis worker "
            "health. Requires Enterprise IAM API key in the sidebar."
        )
        if not api_key:
            st.info("Connect an Enterprise API key in the sidebar to load fleet dashboards.")
            return

        limit = st.number_input(
            "Preflight aggregate limit",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            key="hermes_enterprise_preflight_agg_limit",
        )
        if st.button("Load fleet dashboard", key="hermes_enterprise_load_dashboard"):
            errors: list[str] = []
            memory_body: dict[str, Any] | None = None
            aggregate_body: dict[str, Any] | None = None
            worker_body: dict[str, Any] | None = None
            try:
                memory_body = fetch_fleet_memory_status(api_key=api_key)
            except HTTPError as exc:
                errors.append(f"fleet-memory/status: {exc}")
            try:
                aggregate_body = fetch_fleet_preflight_aggregate(
                    api_key=api_key,
                    limit=int(limit),
                )
            except HTTPError as exc:
                errors.append(f"fleet-ollama-sli/preflight-aggregate: {exc}")
            try:
                worker_body = fetch_fleet_worker_health(api_key=api_key)
            except HTTPError as exc:
                errors.append(f"fleet-worker/health: {exc}")
            st.session_state["hermes_enterprise_dashboard_memory"] = memory_body
            st.session_state["hermes_enterprise_dashboard_aggregate"] = aggregate_body
            st.session_state["hermes_enterprise_dashboard_worker"] = worker_body
            st.session_state["hermes_enterprise_dashboard_errors"] = errors

        for err in st.session_state.get("hermes_enterprise_dashboard_errors") or []:
            st.warning(str(err))

        memory = st.session_state.get("hermes_enterprise_dashboard_memory")
        if isinstance(memory, dict):
            st.subheader("Fleet memory")
            rows = fleet_memory_status_table_rows(memory)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)

        aggregate = st.session_state.get("hermes_enterprise_dashboard_aggregate")
        if isinstance(aggregate, dict):
            st.subheader("Fleet preflight + Ollama SLI")
            cap = fleet_sli_aggregate_caption(aggregate)
            if cap:
                st.caption(cap)
            history = aggregate.get("preflight_history")
            if isinstance(history, dict):
                entries = history.get("entries")
                if isinstance(entries, list) and entries:
                    st.dataframe(entries[:25], use_container_width=True)

        worker = st.session_state.get("hermes_enterprise_dashboard_worker")
        if isinstance(worker, dict):
            st.subheader("Fleet worker")
            wcap = fleet_worker_health_caption(worker)
            if wcap:
                st.caption(wcap)

        if any(
            isinstance(st.session_state.get(k), dict)
            for k in (
                "hermes_enterprise_dashboard_memory",
                "hermes_enterprise_dashboard_aggregate",
                "hermes_enterprise_dashboard_worker",
            )
        ):
            export_json = fleet_dashboard_export_json(
                memory=memory if isinstance(memory, dict) else None,
                preflight_aggregate=aggregate if isinstance(aggregate, dict) else None,
                worker=worker if isinstance(worker, dict) else None,
            )
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            st.download_button(
                label="Download fleet dashboard JSON",
                data=export_json.encode("utf-8"),
                file_name=f"hermes_{fleet_dashboard_export_filename_slug()}_{ts}.json",
                mime="application/json",
                key="hermes_dl_enterprise_fleet_dashboard",
            )


def enterprise_preflight_headers_for_cross_run() -> dict[str, str]:
    from nimbusware_console.enterprise_console import (
        build_enterprise_headers,
        resolve_active_api_key,
    )

    manifest = st.session_state.get(SS_EDITION_MANIFEST)
    if not enterprise_console_feature_enabled(manifest):
        return {}
    tenant_keys: dict[str, str] = dict(st.session_state.get(SS_TENANT_KEYS) or {})
    api_key = resolve_active_api_key(
        primary_key=st.session_state.get(SS_API_KEY),
        tenant_keys=tenant_keys,
        selected_tenant_slug=st.session_state.get(SS_SELECTED_TENANT),
    )
    return build_enterprise_headers(api_key)
