from __future__ import annotations

import pytest

from nimbusware_maker.intent_classifier import WorkType, classify_intent

GOLDEN_INTENTS: list[tuple[str, dict, dict, dict, WorkType, str]] = [
    (
        "failing_test_attachment",
        "please fix this",
        [{"failing_test": "tests/test_auth.py::test_login"}],
        {},
        WorkType.PATCH,
        "patch",
    ),
    (
        "stack_trace_attachment",
        "something broke",
        [{"stack_trace": "Traceback (most recent call last):\nAssertionError"}],
        {},
        WorkType.PATCH,
        "patch",
    ),
    (
        "keyword_bug_fix",
        "fix the bug in the login handler for src/auth/login.py",
        [],
        {},
        WorkType.PATCH,
        "patch",
    ),
    (
        "campaign_mvp",
        "Build a CRM MVP with contacts and pipeline for our sales team",
        [],
        {},
        WorkType.CAMPAIGN,
        "campaign_micro_slice",
    ),
    (
        "slice_feature",
        "Add a feature to refactor the billing module endpoint",
        [],
        {"default_workflow_profile": "micro_slice"},
        WorkType.SLICE,
        "micro_slice",
    ),
    (
        "factory_catalog",
        "Run factory catalog prompt",
        [{"prompt_id": "crm_zero_touch"}],
        {},
        WorkType.FACTORY,
        "campaign_factory_zero_touch",
    ),
    (
        "quick_mode_hint",
        "spike this idea locally",
        [],
        {},
        WorkType.QUICK,
        "quick_local",
    ),
]


@pytest.mark.parametrize(
    "fixture_id,message,attachments,project_meta,expected_type,expected_profile",
    GOLDEN_INTENTS,
    ids=[row[0] for row in GOLDEN_INTENTS],
)
def test_classify_intent_golden(
    fixture_id: str,
    message: str,
    attachments: list[dict],
    project_meta: dict,
    expected_type: WorkType,
    expected_profile: str,
) -> None:
    hints = {"quick_mode": fixture_id == "quick_mode_hint"}
    result = classify_intent(
        message,
        attachments=attachments,
        project_metadata=project_meta or None,
        platform_hints=hints,
    )
    assert result.work_type == expected_type, fixture_id
    assert result.suggested_profile == expected_profile, fixture_id
    assert 0.0 <= result.confidence <= 1.0
    assert result.rationale
    assert isinstance(result.signals, list)


def test_classify_intent_many_paths_suggests_slice() -> None:
    paths = [f"src/pkg/module_{i}.py" for i in range(7)]
    message = "fix imports in " + " ".join(paths)
    result = classify_intent(message)
    assert result.work_type in (WorkType.SLICE, WorkType.PATCH)
    assert "patch_many_paths_suggest_slice" in result.signals


def test_classify_intent_short_campaign_warns() -> None:
    result = classify_intent("build CRM MVP now")
    assert result.work_type == WorkType.CAMPAIGN
    assert "forced_campaign_short_message" in result.signals


def test_classify_intent_low_confidence_requires_confirmation() -> None:
    result = classify_intent("maybe do something")
    if result.confidence < 0.5:
        assert "require_confirmation" in result.signals


def test_classify_intent_web_template_slice_profile() -> None:
    result = classify_intent(
        "add a dashboard page",
        project_metadata={"template": "web", "default_workflow_profile": "micro_slice"},
    )
    assert result.work_type == WorkType.SLICE
    assert result.suggested_profile == "micro_slice_web"


def test_classify_intent_llm_overridden_by_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_INTENT_CLASSIFIER_MODEL", "test-model")
    paths = [f"src/pkg/module_{i}.py" for i in range(7)]
    message = "fix imports in " + " ".join(paths)

    def fake_llm(*_args: object, **_kwargs: object) -> object:
        from nimbusware_maker.intent_classifier import ClassificationResult

        return ClassificationResult(
            work_type=WorkType.PATCH,
            confidence=0.9,
            rationale="LLM says patch",
            suggested_profile="patch",
            signals=["llm_classifier"],
        )

    monkeypatch.setattr(
        "nimbusware_maker.intent_classifier._classify_intent_llm",
        fake_llm,
    )
    result = classify_intent(message)
    assert result.work_type == WorkType.SLICE
    assert "llm_overridden_by_rules" in result.signals


def test_classify_intent_use_llm_false_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_INTENT_CLASSIFIER_MODEL", "test-model")
    called = False

    def fake_llm(*_args: object, **_kwargs: object) -> object:
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(
        "nimbusware_maker.intent_classifier._classify_intent_llm",
        fake_llm,
    )
    classify_intent("fix bug in login", use_llm=False)
    assert not called
