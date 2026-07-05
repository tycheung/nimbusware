from __future__ import annotations

from orchestrator._pipeline.critique_emit_registry import (
    CRITIQUE_EMIT_SPECS,
    security_critique_scan_spec,
)
from orchestrator._pipeline.critique_emit_registry import (
    test_writer_optional_spec as build_test_writer_optional_spec,
)
from orchestrator._pipeline.scan_critique_emit import ScanCritiqueEmitSpec
from orchestrator._pipeline.stage_dispatch import PIPELINE_STAGES
from orchestrator._pipeline.stage_registry import (
    PIPELINE_STAGE_MIXINS,
    PipelineStageRegistration,
    build_run_orchestrator_base,
)
from orchestrator.workflow.universal_critique import EffectiveUniversalCritique
from projections.builders.maker_progress import maker_progress_from_events


def test_pipeline_stages_align_with_stage_mixins() -> None:
    mixins_from_stages = tuple(entry.mixin for entry in PIPELINE_STAGES)
    assert mixins_from_stages == PIPELINE_STAGE_MIXINS
    assert len(PIPELINE_STAGES) == len(PIPELINE_STAGE_MIXINS)
    names = [entry.name for entry in PIPELINE_STAGES]
    assert "create_run" in names
    assert "role_execute" in names


def test_pipeline_stage_registration_names_mixins() -> None:
    entry: PipelineStageRegistration = PIPELINE_STAGES[0]
    assert entry.name == "create_run"
    assert issubclass(entry.mixin, object)


def test_build_run_orchestrator_base_appends_extras() -> None:
    class Extra:
        pass

    bases = build_run_orchestrator_base(Extra)
    assert bases[-1] is Extra
    assert bases[:-1] == PIPELINE_STAGE_MIXINS


def test_critique_emit_specs_document_role_keys() -> None:
    tw = CRITIQUE_EMIT_SPECS["test_writer"]
    assert tw.kind == "role"
    assert tw.enabled_key == "tw_enabled"
    assert tw.llm_key == "tw_llm"
    assert tw.stub_key == "tw_stub"


def test_test_writer_optional_spec_reads_from_critique_emit_specs() -> None:
    spec = build_test_writer_optional_spec()
    keys = CRITIQUE_EMIT_SPECS["test_writer"]
    eff = EffectiveUniversalCritique(
        impl_llm=False,
        impl_stub=False,
        impl_stage_failed_on_gate_fail=False,
        impl_emit_finding_on_gate_fail=False,
        impl_hard_block_on_gate_fail=False,
        tw_enabled=True,
        tw_llm=False,
        tw_stub=True,
        tw_stage_failed_on_gate_fail=False,
        tw_emit_finding_on_gate_fail=False,
        tw_hard_block_on_gate_fail=False,
        pll_enabled=False,
        pll_llm=False,
        pll_stub=False,
        pll_stage_failed_on_gate_fail=False,
        pll_emit_finding_on_gate_fail=False,
        pll_hard_block_on_gate_fail=False,
        fw_enabled=False,
        fw_llm=False,
        fw_stub=False,
        fw_stage_failed_on_gate_fail=False,
        fw_emit_finding_on_gate_fail=False,
        fw_hard_block_on_gate_fail=False,
        mi_enabled=False,
        mi_llm=False,
        mi_stub=False,
        mi_stage_failed_on_gate_fail=False,
        mi_emit_finding_on_gate_fail=False,
        mi_hard_block_on_gate_fail=False,
    )
    assert spec.enabled(eff) is True
    assert spec.stub(eff) is True
    assert spec.execute_llm.__name__ == keys.execute_llm_module.rsplit(".", 1)[-1]


def test_security_critique_scan_spec_reads_stage_id_from_registry() -> None:
    spec = security_critique_scan_spec()
    assert isinstance(spec, ScanCritiqueEmitSpec)
    scan_keys = CRITIQUE_EMIT_SPECS["security_scan"]
    assert scan_keys.kind == "scan"
    assert spec.stage_id == scan_keys.stage_id


def test_maker_progress_display_caption_on_gate_block() -> None:
    events = [
        {"event_type": "run.created", "metadata": {"requirements": {"business_prompt": "Fix"}}},
        {
            "event_type": "stage.started",
            "payload": {"stage_name": "slice.plan"},
            "metadata": {"slice_plan": True, "slice_id": "s1", "target_paths": ["a.py"]},
        },
        {
            "event_type": "stage.failed",
            "payload": {"stage_name": "slice.gate"},
            "metadata": {"slice_id": "s1", "slice_gate_verdict": "FAIL", "tests_passed": False},
        },
    ]
    body = maker_progress_from_events(events)
    assert body.get("display_caption") == body.get("gate_summary")
    assert body["display_caption"]
