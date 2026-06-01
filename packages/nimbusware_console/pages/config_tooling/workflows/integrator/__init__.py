from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.workflows._shared_integrator import ALLOW_WORKFLOW_YAML_WRITE_ENV, list_workflow_profile_keys

from .agent_evaluator import render_agent_evaluator_section
from .apply_agent_evaluator import render_apply_agent_evaluator_section
from .apply_full_profile import render_apply_full_profile_section
from .apply_integrator_gate import render_apply_integrator_gate_section
from .escalation_suppress import render_escalation_suppress_section
from .preview import render_integrator_preview_section
from .security_scan import render_security_scan_section
from .self_refinement import render_self_refinement_section
from .thresholds import render_thresholds_section
from .universal_critique import render_universal_critique_section


def render_workflows_integrator_section() -> None:
    with st.expander("Module Integrator gate (workflow preview)", expanded=False):
        st.caption(
            "**fo131** read-only preview + **fo132** / **fo140** optional subtree disk apply + "
            "**§14 #13** optional **full-profile** shallow merge + **fo133** "
            "threshold source "
            "breakdown + **fo134** universal critique + **fo135** self-refinement + **fo136** "
            "security-scan-metadata + **fo137** escalation-suppress + **fo139** "
            "agent-evaluator workflow explainer "
            "(nested expanders): preview "
            "``ModuleIntegrator.score_fit`` against ``configs/bundles/catalog.yaml`` using the same "
            "``integrator_gate`` knobs as the orchestrator (workflow YAML + "
            "``configs/integrator/thresholds.yaml``; "
            "``HERMES_INTEGRATOR_MIN_SCORE_TO_PASS`` still wins "
            "when set). Paste an ``integrator_gate:`` fragment to override **min_score** / "
            "**enabled** / "
            "**project_tags** for preview; **Apply** (fo132 / fo140) merges only that subtree when "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}`` is enabled and you confirm the profile stem.",
        )
        repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{repo_root}`")
        wf_keys = list_workflow_profile_keys(repo_root)
        if not wf_keys:
            st.warning("No workflow profiles found under ``configs/workflows/``.")
            workflow_profile: str | None = None
        else:
            workflow_profile = st.selectbox(
                "Workflow profile (YAML stem)",
                options=wf_keys,
                index=wf_keys.index("default") if "default" in wf_keys else 0,
                key="hermes_integrator_wf_profile",
            )

        render_universal_critique_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_self_refinement_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_security_scan_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_escalation_suppress_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_agent_evaluator_section(repo_root=repo_root, workflow_profile=workflow_profile)
        st.text_area(
            "Optional pasted ``integrator_gate`` YAML (full workflow with key, or flat mapping)",
            height=120,
            placeholder="integrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n",
            key="hermes_integrator_paste_yaml",
        )
        render_thresholds_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_integrator_preview_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_apply_integrator_gate_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_apply_agent_evaluator_section(repo_root=repo_root, workflow_profile=workflow_profile)
        render_apply_full_profile_section(repo_root=repo_root, workflow_profile=workflow_profile)
