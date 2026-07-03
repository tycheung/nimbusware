from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from maker.intent.classifier_rules import (
    BACKEND_ONLY_PHRASES as _BACKEND_ONLY_PHRASES,
)
from maker.intent.classifier_rules import (
    CAMPAIGN_KEYWORDS as _CAMPAIGN_KEYWORDS,
)
from maker.intent.classifier_rules import (
    FACTORY_KEYWORDS as _FACTORY_KEYWORDS,
)
from maker.intent.classifier_rules import (
    FAST_SLICE_KEYWORDS as _FAST_SLICE_KEYWORDS,
)
from maker.intent.classifier_rules import (
    PATCH_KEYWORDS as _PATCH_KEYWORDS,
)
from maker.intent.classifier_rules import (
    PROFILE_BY_WORK_TYPE as _PROFILE_BY_WORK_TYPE,
)
from maker.intent.classifier_rules import (
    SLICE_KEYWORDS as _SLICE_KEYWORDS,
)
from maker.intent.classifier_rules import (
    WorkType,
)

__all__ = ("ClassificationResult", "WorkType", "classify_intent", "scope_narrowed_to_backend_only")

_PATH_RE = re.compile(
    r"(?:[\w.-]+/)+[\w.-]+\.(?:py|js|ts|tsx|vue|html|css|go|rs|java)\b",
    re.IGNORECASE,
)
_TEST_RE = re.compile(r"(?:tests?/[\w./-]+(?:::[\w]+)?)", re.IGNORECASE)


@dataclass
class ClassificationResult:
    work_type: WorkType
    confidence: float
    rationale: str
    suggested_profile: str
    signals: list[str] = field(default_factory=list)
    attachments_extracted: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_type": self.work_type.value,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "suggested_profile": self.suggested_profile,
            "signals": list(self.signals),
            "attachments_extracted": dict(self.attachments_extracted),
        }


def _lower(text: str) -> str:
    return text.strip().lower()


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    low = _lower(text)
    return [kw for kw in keywords if kw in low]


def _extract_attachments(attachments: list[dict[str, Any]] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    paths: list[str] = []
    for raw in attachments or []:
        if not isinstance(raw, dict):
            continue
        for key in ("failing_test", "stack_trace", "error_snippet", "prompt_id"):
            val = str(raw.get(key) or "").strip()
            if val and key not in out:
                out[key] = val
        raw_paths = raw.get("target_paths")
        if isinstance(raw_paths, list):
            paths.extend(str(p).strip() for p in raw_paths if str(p).strip())
    if paths:
        out["target_paths"] = paths[:8]
    return out


def _infer_paths(message: str, extracted: dict[str, Any]) -> list[str]:
    paths = list(extracted.get("target_paths") or [])
    for match in _PATH_RE.findall(message):
        if match not in paths:
            paths.append(match)
    for match in _TEST_RE.findall(message):
        if match not in paths:
            paths.append(match)
    return paths[:12]


def _resolve_slice_profile(
    message: str,
    project_metadata: dict[str, Any] | None,
    platform_hints: dict[str, Any] | None,
) -> str:
    meta = project_metadata or {}
    hints = platform_hints or {}
    default_profile = str(meta.get("default_workflow_profile") or "micro_slice").strip()
    template = str(meta.get("template") or "").strip().lower()
    low = _lower(message)

    if "fullstack" in low or "full-stack" in low:
        if hints.get("dev_env_enabled"):
            return "micro_slice_fullstack"
    if template in ("web", "fullstack") or "frontend" in low or "ui " in low:
        return "micro_slice_web"
    if any(kw in low for kw in _FAST_SLICE_KEYWORDS):
        return "fast_slice"
    if default_profile in {
        "micro_slice",
        "fast_slice",
        "micro_slice_web",
        "micro_slice_fullstack",
    }:
        return default_profile
    return "micro_slice"


def scope_narrowed_to_backend_only(message: str) -> bool:
    low = _lower(message)
    return any(phrase in low for phrase in _BACKEND_ONLY_PHRASES)


def _resolve_campaign_profile(
    message: str,
    project_metadata: dict[str, Any] | None,
) -> str:
    meta = project_metadata or {}
    template = str(meta.get("template") or "").strip().lower()
    default_profile = str(meta.get("default_workflow_profile") or "").strip()
    if scope_narrowed_to_backend_only(message):
        return "campaign_micro_slice"
    if template == "api" or default_profile == "campaign_micro_slice":
        return "campaign_micro_slice"
    if template in {"fullstack", "web"} or default_profile == "campaign_fullstack":
        return "campaign_fullstack"
    return "campaign_fullstack"


def _resolve_factory_profile(extracted: dict[str, Any], message: str) -> str:
    prompt_id = str(extracted.get("prompt_id") or "").strip().lower()
    if prompt_id in {"t3", "tier3", "campaign_factory_t3"}:
        return "campaign_factory_t3"
    if prompt_id in {"todo_api", "contacts_api"} or scope_narrowed_to_backend_only(message):
        return "campaign_factory_zero_touch"
    if prompt_id:
        return "campaign_factory_zero_touch"
    return "campaign_fullstack"


def _score_work_types(
    message: str,
    extracted: dict[str, Any],
    project_metadata: dict[str, Any] | None,
    platform_hints: dict[str, Any] | None,
) -> tuple[dict[WorkType, float], list[str], list[str]]:
    scores: dict[WorkType, float] = {wt: 0.0 for wt in WorkType}
    signals: list[str] = []
    warnings: list[str] = []
    hints = platform_hints or {}

    if hints.get("quick_mode"):
        scores[WorkType.QUICK] += 4.0
        signals.append("platform_quick_mode")

    if extracted.get("failing_test"):
        scores[WorkType.PATCH] += 5.0
        signals.append("attachment_failing_test")
    if extracted.get("stack_trace"):
        scores[WorkType.PATCH] += 5.0
        signals.append("attachment_stack_trace")
    if extracted.get("error_snippet"):
        scores[WorkType.PATCH] += 2.5
        signals.append("attachment_error_snippet")

    patch_hits = _keyword_hits(message, _PATCH_KEYWORDS)
    if patch_hits:
        scores[WorkType.PATCH] += 2.0 + 0.5 * len(patch_hits)
        signals.append("keyword_patch")

    campaign_hits = _keyword_hits(message, _CAMPAIGN_KEYWORDS)
    if campaign_hits:
        scores[WorkType.CAMPAIGN] += 2.5 + 0.5 * len(campaign_hits)
        signals.append("keyword_campaign")

    slice_hits = _keyword_hits(message, _SLICE_KEYWORDS)
    if slice_hits:
        scores[WorkType.SLICE] += 2.0 + 0.5 * len(slice_hits)
        signals.append("keyword_slice")

    factory_hits = _keyword_hits(message, _FACTORY_KEYWORDS)
    if factory_hits:
        scores[WorkType.FACTORY] += 2.5 + 0.5 * len(factory_hits)
        signals.append("keyword_factory")
    if extracted.get("prompt_id"):
        scores[WorkType.FACTORY] += 4.0
        signals.append("attachment_prompt_id")

    inferred_paths = _infer_paths(message, extracted)
    if inferred_paths:
        if len(inferred_paths) <= 2:
            scores[WorkType.PATCH] += 1.5
            signals.append("inferred_target_paths")
        elif len(inferred_paths) <= 5:
            scores[WorkType.SLICE] += 1.0
            signals.append("inferred_multi_paths")
        else:
            scores[WorkType.SLICE] += 2.5
            signals.append("inferred_many_paths")
            warnings.append("patch_many_paths_suggest_slice")

    meta = project_metadata or {}
    default_wt = str(meta.get("default_work_type") or "").strip().lower()
    if default_wt in {wt.value for wt in WorkType}:
        scores[WorkType(default_wt)] += 0.75
        signals.append("project_default_work_type")

    if max(scores.values()) <= 0.0:
        scores[WorkType.SLICE] = 1.0
        signals.append("default_slice_fallback")

    if len(message.strip()) < 40 and scores[WorkType.CAMPAIGN] >= max(
        scores[WorkType.PATCH],
        scores[WorkType.SLICE],
        scores[WorkType.FACTORY],
        scores[WorkType.QUICK],
    ):
        warnings.append("forced_campaign_short_message")

    return scores, signals, warnings


def _confidence_from_scores(scores: dict[WorkType, float]) -> float:
    ordered = sorted(scores.values(), reverse=True)
    top = ordered[0]
    second = ordered[1] if len(ordered) > 1 else 0.0
    if top <= 0:
        return 0.35
    margin = (top - second) / top
    raw = 0.45 + margin * 0.5
    return max(0.2, min(0.98, raw))


def _rationale_for(work_type: WorkType, signals: list[str]) -> str:
    rationales = {
        WorkType.QUICK: "Quick local mode is active — use in-memory spike workflow.",
        WorkType.PATCH: "Looks like a hotfix: failing test, error, or small targeted edit.",
        WorkType.SLICE: "Bounded feature work — one micro-slice pass fits best.",
        WorkType.CAMPAIGN: "Full product delivery — autonomous campaign backlog.",
        WorkType.FACTORY: "Factory catalog or zero-touch factory profile.",
    }
    base = rationales[work_type]
    if "attachment_failing_test" in signals or "attachment_stack_trace" in signals:
        return "Error context detected — patch lane with targeted test."
    if "keyword_campaign" in signals:
        return "Product-scale intent — full-stack campaign recommended."
    if "attachment_prompt_id" in signals:
        return "Catalog prompt_id present — factory campaign profile."
    return base


def _rules_classification_result(
    text: str,
    extracted: dict[str, Any],
    *,
    project_metadata: dict[str, Any] | None,
    platform_hints: dict[str, Any] | None,
) -> ClassificationResult:
    scores, signals, warnings = _score_work_types(
        text,
        extracted,
        project_metadata,
        platform_hints,
    )
    work_type = max(scores, key=lambda wt: scores[wt])
    confidence = _confidence_from_scores(scores)

    if work_type == WorkType.SLICE:
        profile = _resolve_slice_profile(text, project_metadata, platform_hints)
    elif work_type == WorkType.FACTORY:
        profile = _resolve_factory_profile(extracted, text)
    elif work_type == WorkType.CAMPAIGN:
        profile = _resolve_campaign_profile(text, project_metadata)
    else:
        profile = _PROFILE_BY_WORK_TYPE[work_type]

    all_signals = list(signals) + list(warnings)
    if confidence < 0.5:
        all_signals.append("require_confirmation")

    return ClassificationResult(
        work_type=work_type,
        confidence=confidence,
        rationale=_rationale_for(work_type, signals),
        suggested_profile=profile,
        signals=all_signals,
        attachments_extracted=extracted,
    )


def _llm_classifier_enabled() -> bool:
    from env.settings_resolve import resolve_str

    return bool(resolve_str("NIMBUSWARE_INTENT_CLASSIFIER_MODEL", default="").strip())


def _classify_intent_llm(
    message: str,
    *,
    base_url: str,
    model_id: str,
    timeout_seconds: float = 60.0,
) -> ClassificationResult | None:
    from orchestrator.llm.common import ollama_chat_json_via_plan_patch

    schema = (
        '{"work_type":"patch|slice|campaign|factory|quick",'
        '"confidence":0.0,"rationale":"...","signals":["..."]}'
    )
    data = ollama_chat_json_via_plan_patch(
        base_url=base_url,
        model=model_id,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Classify operator software intent. Reply JSON only. Schema: {schema}"
                ),
            },
            {"role": "user", "content": message[:4000]},
        ],
        timeout_seconds=timeout_seconds,
        agent_role="planner",
    )
    if not isinstance(data, dict):
        return None
    raw_wt = str(data.get("work_type") or "").strip().lower()
    try:
        work_type = WorkType(raw_wt)
    except ValueError:
        return None
    confidence_raw = data.get("confidence")
    if isinstance(confidence_raw, (int, float, str)):
        try:
            confidence = float(confidence_raw)
        except ValueError:
            confidence = 0.6
    else:
        confidence = 0.6
    confidence = max(0.0, min(0.98, confidence))
    signals_raw = data.get("signals")
    signals = [str(s) for s in signals_raw[:8]] if isinstance(signals_raw, list) else []
    signals.append("llm_classifier")
    profile = _PROFILE_BY_WORK_TYPE[work_type]
    if work_type == WorkType.SLICE:
        profile = "micro_slice"
    return ClassificationResult(
        work_type=work_type,
        confidence=confidence,
        rationale=str(data.get("rationale") or _rationale_for(work_type, signals))[:500],
        suggested_profile=profile,
        signals=signals,
        attachments_extracted={},
    )


def _merge_llm_with_rules(
    llm: ClassificationResult,
    rules: ClassificationResult,
) -> ClassificationResult:
    unsafe_llm_campaign = (
        llm.work_type == WorkType.CAMPAIGN and "forced_campaign_short_message" in rules.signals
    )
    unsafe_llm_patch = (
        llm.work_type == WorkType.PATCH and "patch_many_paths_suggest_slice" in rules.signals
    )
    if unsafe_llm_campaign or unsafe_llm_patch:
        merged = rules
        merged.signals = list(merged.signals) + ["llm_overridden_by_rules"]
        return merged
    if rules.work_type == WorkType.PATCH and (
        "attachment_failing_test" in rules.signals or "attachment_stack_trace" in rules.signals
    ):
        merged = rules
        merged.signals = list(merged.signals) + ["llm_confirmed_patch_context"]
        return merged
    return llm


def classify_intent(
    message: str,
    attachments: list[dict[str, Any]] | None = None,
    project_metadata: dict[str, Any] | None = None,
    platform_hints: dict[str, Any] | None = None,
    *,
    use_llm: bool | None = None,
) -> ClassificationResult:
    text = str(message or "").strip()
    extracted = _extract_attachments(attachments)
    inferred_paths = _infer_paths(text, extracted)
    if inferred_paths and "target_paths" not in extracted:
        extracted["target_paths"] = inferred_paths[:8]

    rules_result = _rules_classification_result(
        text,
        extracted,
        project_metadata=project_metadata,
        platform_hints=platform_hints,
    )

    if use_llm is False or not _llm_classifier_enabled():
        return rules_result

    from env.settings_resolve import resolve_str
    from orchestrator.routing.manage import ollama_base_url

    model_id = resolve_str("NIMBUSWARE_INTENT_CLASSIFIER_MODEL", default="").strip()
    base_url = ollama_base_url()
    try:
        llm_result = _classify_intent_llm(
            text,
            base_url=base_url,
            model_id=model_id,
        )
        if llm_result is not None:
            llm_result.attachments_extracted = dict(extracted)
            return _merge_llm_with_rules(llm_result, rules_result)
    except Exception:
        pass
    return rules_result
