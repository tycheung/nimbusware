from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from orchestrator.factory.completion import FactoryTier, evaluate_factory_gates
from orchestrator.factory.runner import (
    PutE2EResult,
    match_factory_flow_id,
    run_put_e2e_flow,
)


def run_put_e2e_for_factory_run(
    workspace: Path,
    rows: list[dict[str, Any]],
    *,
    tier: FactoryTier,
    repo_root: Path | None,
    store: Any | None = None,
    run_id: UUID | None = None,
    slices_completed: int = 0,
    ui_flow_required: bool = False,
) -> tuple[
    bool | None,
    PutE2EResult | None,
    Any | None,
    float | None,
    dict[str, Any] | None,
    bool | None,
    str | None,
]:
    from env.env_flags import env_str
    from maker.intent.requirements import requirements_from_run_created_metadata
    from maker.stack_manifest import manifest_from_requirements
    from maker.workspace.workspace import run_created_metadata_from_rows
    from orchestrator.factory.runtime import start_put_preview, stop_put_preview
    from orchestrator.interaction_surface_map import discover_surfaces_combined
    from orchestrator.launch_eval_catalog import attach_context_from_run

    if tier in {"T0", "T1"}:
        return None, None, None, None, None, None, None

    attach = attach_context_from_run(rows, repo_root)
    meta = run_created_metadata_from_rows(rows)
    req = requirements_from_run_created_metadata(meta) or {}
    manifest_model = manifest_from_requirements(req)
    stack_manifest = manifest_model.model_dump() if manifest_model is not None else None
    flow_id = match_factory_flow_id(
        str(req.get("business_prompt") or "").strip(),
        prompt_id=attach.get("prompt_id"),
        repo_root=repo_root,
        stack_manifest=stack_manifest,
    )
    if not flow_id:
        skip = PutE2EResult(
            verdict="SKIP",
            flow_id="",
            base_url="",
            detail="no catalog flow match",
        )
        return False, skip, None, None, None, None, None

    port = 19876 + (hash(str(workspace)) % 400)
    preview = start_put_preview(
        workspace,
        port,
        startup_timeout_seconds=12.0,
        stack_manifest=stack_manifest,
    )
    put_preview_ok = preview.ok
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    ism = None
    put_e2e: PutE2EResult | None = None
    coverage: float | None = None
    ism_diff: dict[str, Any] | None = None
    if store is not None and run_id is not None and preview.handle is not None:
        from orchestrator.factory.runtime import emit_put_preview_started

        emit_put_preview_started(store, run_id, preview.handle)
    try:
        exploratory = env_str("NIMBUSWARE_FACTORY_EXPLORATORY_CRAWL").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        ism = discover_surfaces_combined(
            workspace,
            preview_base_url=base_url if put_preview_ok else None,
            runtime_crawl=tier == "T3",
            exploratory=exploratory and tier == "T3",
        )
        from orchestrator.repo_intel.ism_diff import (
            diff_ism_snapshots,
            load_ism_snapshot,
            persist_ism_snapshot,
        )

        prior_path = workspace / ".nimbusware" / "ism" / "_latest.json"
        before = load_ism_snapshot(prior_path) if prior_path.is_file() else None
        persist_ism_snapshot(workspace, f"cadence-{slices_completed}", ism)
        prior_path.write_text(
            __import__("json").dumps(ism.to_dict(), indent=2),
            encoding="utf-8",
        )
        ism_diff = diff_ism_snapshots(before, ism)
        put_e2e = run_put_e2e_flow(
            base_url,
            flow_id,
            repo_root=repo_root,
            workspace=workspace,
            require_playwright=False,
        )
        gates = evaluate_factory_gates(
            tier,
            put_preview_ok=put_preview_ok,
            ism=ism,
            put_e2e=put_e2e,
            repo_root=repo_root,
        )
        coverage_raw = gates.details.get("ism_coverage_pct")
        coverage = float(coverage_raw) if coverage_raw is not None else None

        ui_passed: bool | None = None
        ui_flow_id: str | None = None
        if ui_flow_required and put_preview_ok and put_e2e and put_e2e.verdict == "PASS":
            from orchestrator.browser_controller import run_ui_flow
            from orchestrator.dev_env.events import emit_dev_env_ui_regression
            from orchestrator.launch_flow_resolver import resolve_launch_flows

            resolved = resolve_launch_flows(rows, workspace, repo_root=repo_root)
            if resolved.ui_flow is not None:
                ui_flow_id = resolved.ui_flow.flow_id
                ui_result = run_ui_flow(base_url, resolved.ui_flow)
                ui_passed = ui_result.passed
                if store is not None and run_id is not None:
                    emit_dev_env_ui_regression(
                        store,
                        run_id,
                        passed=ui_result.passed,
                        steps_run=ui_result.steps_run,
                        detail=ui_result.detail,
                        flow_id=ui_flow_id,
                        failed_step=ui_result.failed_step,
                        locator=ui_result.failed_locator,
                    )

        return put_preview_ok, put_e2e, ism, coverage, ism_diff, ui_passed, ui_flow_id
    finally:
        if store is not None and run_id is not None and preview.handle is not None:
            from orchestrator.factory.runtime import emit_put_preview_stopped

            emit_put_preview_stopped(store, run_id, preview.handle)
        stop_put_preview(preview.handle)
