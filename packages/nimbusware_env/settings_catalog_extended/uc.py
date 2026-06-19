from __future__ import annotations

from nimbusware_env.settings_catalog import SettingDef
from nimbusware_env.settings_catalog_extended._factories import _uc


def uc_defs() -> tuple[SettingDef, ...]:
    uc_keys: tuple[tuple[str, str], ...] = (
        ("NIMBUSWARE_IMPLEMENTATION_CRITIQUE_LLM", "Implementation critique LLM"),
        ("NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE", "Enable test writer critique"),
        ("NIMBUSWARE_TEST_WRITER_CRITIQUE_LLM", "Test writer critique LLM"),
        ("NIMBUSWARE_STUB_TEST_WRITER_CRITICS", "Stub test writer critics"),
        ("NIMBUSWARE_ENABLE_PLANNER_CRITIQUE", "Enable planner critique"),
        ("NIMBUSWARE_PLANNER_CRITIQUE_LLM", "Planner critique LLM"),
        ("NIMBUSWARE_STUB_PLANNER_CRITICS", "Stub planner critics"),
        ("NIMBUSWARE_ENABLE_FRONTEND_WRITER_CRITIQUE", "Enable frontend writer critique"),
        ("NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_LLM", "Frontend writer critique LLM"),
        ("NIMBUSWARE_STUB_FRONTEND_WRITER_CRITICS", "Stub frontend writer critics"),
        ("NIMBUSWARE_ENABLE_MODULE_INTEGRATOR_CRITIQUE", "Enable module integrator critique"),
        ("NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_LLM", "Module integrator critique LLM"),
        ("NIMBUSWARE_STUB_MODULE_INTEGRATOR_CRITICS", "Stub module integrator critics"),
        (
            "NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
            "UC stage failed on gate fail (all panels)",
        ),
        (
            "NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
            "UC emit finding on gate fail (all panels)",
        ),
        (
            "NIMBUSWARE_UNIVERSAL_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
            "UC hard block on gate fail (all panels)",
        ),
    )
    return tuple(_uc(k, label) for k, label in uc_keys)
