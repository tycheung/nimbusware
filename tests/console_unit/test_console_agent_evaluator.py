from __future__ import annotations

import json

from console.agent_evaluator_display import (
    agent_evaluator_auto_actions_caption,
    agent_evaluator_auto_actions_table_rows,
    agent_evaluator_coverage_gate_caption,
    agent_evaluator_evaluation_branch_caption,
    agent_evaluator_evaluation_caption,
    agent_evaluator_from_timeline,
    agent_evaluator_operator_metrics,
    agent_evaluator_operator_metrics_caption,
    agent_evaluator_operator_metrics_export_filename_slug,
    agent_evaluator_operator_metrics_export_json,
    agent_evaluator_operator_metrics_table_rows,
    agent_evaluator_operator_metrics_table_rows_csv,
    agent_evaluator_session_caption,
    agent_evaluator_summary_rows,
    agent_evaluator_timeline_export_filename_slug,
    agent_evaluator_timeline_export_json,
    agent_evaluator_timeline_table_rows_csv,
)


def test_agent_evaluator_from_timeline_none_when_missing() -> None:
    assert agent_evaluator_from_timeline(None) is None
    assert agent_evaluator_from_timeline({}) is None
    assert agent_evaluator_from_timeline({"agent_evaluator": None}) is None
    assert agent_evaluator_from_timeline({"agent_evaluator": "x"}) is None


def test_agent_evaluator_from_timeline_returns_dict() -> None:
    body = {
        "events": [],
        "agent_evaluator": {
            "persona_id": "default",
            "stage_name": "agent_eval:default",
            "attempt": 1,
        },
    }
    ae = agent_evaluator_from_timeline(body)
    assert ae == {
        "persona_id": "default",
        "stage_name": "agent_eval:default",
        "attempt": 1,
    }


def test_agent_evaluator_summary_rows_empty_for_none() -> None:
    assert agent_evaluator_summary_rows(None) == []


def test_agent_evaluator_session_caption() -> None:
    cap = agent_evaluator_session_caption(
        {
            "persona_id": "backend_engineer",
            "stage_name": "agent_eval:backend_engineer",
            "attempt": 2,
        },
    )
    assert cap is not None
    assert "backend_engineer" in cap
    assert "attempt=2" in cap
    assert agent_evaluator_session_caption(None) is None
    assert agent_evaluator_session_caption({}) is None
    assert agent_evaluator_session_caption({"persona_id": "x"}) is not None


def test_agent_evaluator_evaluation_branch_caption() -> None:
    cap = agent_evaluator_evaluation_branch_caption(
        {
            "evaluation_status": "ok",
            "evaluation_branch": "rules_with_llm_policy",
            "llm_evaluation_status": "needs_work",
            "llm_evaluation_summary": "review persona coverage",
            "llm_evaluation_score": 0.8,
            "llm_evaluation_score_band": "meets_threshold",
        },
    )
    assert cap is not None
    assert "rules status='ok'" in cap
    assert "LLM policy branch" in cap
    assert "needs_work" in cap
    assert "policy_score=0.800" in cap
    assert "policy_score_band='meets_threshold'" in cap
    rules_only = agent_evaluator_evaluation_branch_caption(
        {"evaluation_status": "invalid", "evaluation_branch": "rules"},
    )
    assert rules_only is not None
    assert "branch='rules'" in rules_only


def test_agent_evaluator_coverage_gate_caption() -> None:
    cap = agent_evaluator_coverage_gate_caption({"critique_gate_verdict": "FAIL"})
    assert cap is not None
    assert "FAIL" in cap
    assert agent_evaluator_coverage_gate_caption({}) is None


def test_agent_evaluator_evaluation_caption() -> None:
    cap = agent_evaluator_evaluation_caption(
        {
            "evaluation_status": "ok",
            "evaluation_score": 1.0,
            "coverage_ratio": 1.0,
            "promotion_ready": True,
            "coverage_business_area_id": "commerce",
            "coverage_development_role_id": "backend_engineer",
            "evaluation_gaps": [],
        },
    )
    assert cap is not None
    assert "status='ok'" in cap
    assert "business_area='commerce'" in cap
    assert "development_role='backend_engineer'" in cap
    assert "gap_count=0" in cap
    assert "score=1.000" in cap
    assert "score_band='strong'" in cap
    assert "coverage_ratio=1.000" in cap
    assert "promotion_ready=True" in cap
    assert agent_evaluator_evaluation_caption(None) is None
    assert agent_evaluator_evaluation_caption({"evaluation_status": ""}) is None


def test_agent_evaluator_auto_actions_caption_promote_and_create() -> None:
    cap = agent_evaluator_auto_actions_caption(
        {
            "auto_promote": {"auto_promote_probation_applied": True},
            "auto_create_persona": {
                "auto_create_persona_applied": True,
                "shelf": "business_area",
                "display_name": "Net",
            },
        },
    )
    assert cap is not None
    assert "auto-promote: applied" in cap
    assert "auto-create: applied" in cap
    assert "business_area" in cap


def test_agent_evaluator_auto_actions_caption_none_when_no_nested_metadata() -> None:
    assert agent_evaluator_auto_actions_caption(None) is None
    assert agent_evaluator_auto_actions_caption({"persona_id": "x"}) is None


def test_agent_evaluator_summary_rows_omits_legacy_nested_auto_create_key() -> None:
    ae = {
        "persona_id": "x",
        "stage_name": "agent_eval:x",
        "attempt": 1,
        "auto_create_persona": {"auto_create_persona_applied": True},
    }
    rows = agent_evaluator_summary_rows(ae)
    labels = [r["field"] for r in rows]
    assert "Auto-create missing persona" not in labels


def test_agent_evaluator_auto_actions_table_rows_env_kill_switch() -> None:
    ae = {
        "auto_promote_requested": True,
        "auto_promote_applied": False,
        "auto_promote_reason": "env_kill_switch",
    }
    rows = agent_evaluator_auto_actions_table_rows(ae)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Auto-promote requested"] == "True"
    assert by_field["Auto-promote applied"] == "False"
    assert by_field["Auto-promote reason"] == "env_kill_switch"


def test_agent_evaluator_auto_actions_table_rows_applied_and_create() -> None:
    ae = {
        "auto_promote_applied": True,
        "auto_create_applied": True,
        "auto_create_shelf": "business_area",
        "auto_create_display_name": "Net",
    }
    rows = agent_evaluator_auto_actions_table_rows(ae)
    labels = [r["field"] for r in rows]
    assert "Auto-promote applied" in labels
    assert "Auto-create display name" in labels
    assert agent_evaluator_auto_actions_table_rows(None) == []


def test_agent_evaluator_summary_rows_omits_nested_auto_blocks() -> None:
    ae = {
        "persona_id": "commerce",
        "stage_name": "agent_eval:commerce",
        "attempt": 1,
        "auto_promote": {"auto_promote_probation_applied": True},
        "auto_promote_applied": True,
    }
    rows = agent_evaluator_summary_rows(ae)
    labels = [r["field"] for r in rows]
    assert "Auto-promote (probation)" not in labels
    assert "Persona id" in labels


def test_agent_evaluator_summary_rows_ordered_fields() -> None:
    ae = {
        "persona_id": "backend_engineer",
        "stage_name": "agent_eval:backend_engineer",
        "attempt": 1,
        "event_id": "e1",
        "occurred_at": "2026-01-01T00:00:00Z",
    }
    rows = agent_evaluator_summary_rows(ae)
    labels = [r["field"] for r in rows]
    assert labels[0] == "Persona id"
    assert labels.index("Stage name") < labels.index("Event id")
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Persona id"] == "backend_engineer"
    assert by_field["Stage name"] == "agent_eval:backend_engineer"
    assert by_field["Attempt"] == "1"
    assert by_field["Event id"] == "e1"
    assert by_field["Occurred at"] == "2026-01-01T00:00:00Z"


def test_agent_evaluator_summary_rows_include_evaluation_fields() -> None:
    rows = agent_evaluator_summary_rows(
        {
            "persona_id": "backend_engineer",
            "stage_name": "agent_eval:backend_engineer",
            "attempt": 1,
            "evaluation_status": "ok",
            "evaluation_score": 0.875,
            "evaluation_score_band": "meets_threshold",
            "coverage_ratio": 1.0,
            "promotion_ready": True,
            "evaluation_gaps": [],
            "coverage_business_area_id": "commerce",
            "coverage_development_role_id": "backend_engineer",
        },
    )
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Evaluation status"] == "ok"
    assert by_field["Evaluation score"] == "0.875"
    assert by_field["Evaluation score band"] == "meets_threshold"
    assert by_field["Coverage ratio"] == "1.0"
    assert by_field["Promotion ready"] == "True"
    assert by_field["Evaluation gaps"] == "[]"
    assert by_field["Coverage business area id"] == "commerce"
    assert by_field["Coverage development role id"] == "backend_engineer"


def test_agent_evaluator_timeline_export_json_empty_for_non_mapping() -> None:
    assert agent_evaluator_timeline_export_json(None) == "{}"
    assert agent_evaluator_timeline_export_json("nope") == "{}"
    assert json.loads(agent_evaluator_timeline_export_json(None)) == {}


def test_agent_evaluator_timeline_table_rows_csv_empty_for_none() -> None:
    assert agent_evaluator_timeline_table_rows_csv(None) == ""


def test_agent_evaluator_timeline_export_roundtrip() -> None:
    ae = {
        "persona_id": "backend_engineer",
        "stage_name": "agent_eval:backend_engineer",
        "attempt": 1,
        "auto_promote_applied": True,
        "auto_promote_reason": "ok",
    }
    csv_text = agent_evaluator_timeline_table_rows_csv(ae)
    assert "summary" in csv_text
    assert "auto_actions" in csv_text
    assert "Persona id" in csv_text
    assert "Auto-promote applied" in csv_text
    body = json.loads(agent_evaluator_timeline_export_json(ae))
    assert body["persona_id"] == "backend_engineer"
    assert body["auto_promote_applied"] is True


def test_agent_evaluator_timeline_export_filename_slug() -> None:
    assert agent_evaluator_timeline_export_filename_slug("AB@cd") == "ab_cd"
    assert agent_evaluator_timeline_export_filename_slug("UUID-1! ") == "uuid-1"


def test_agent_evaluator_operator_metrics_empty() -> None:
    m = agent_evaluator_operator_metrics(None)
    assert m["has_persona_id"] is False
    assert agent_evaluator_operator_metrics_caption(m) is None
    assert agent_evaluator_operator_metrics_table_rows(m) == []


def test_agent_evaluator_operator_metrics_score_band() -> None:
    ae = {
        "evaluation_score": 0.95,
        "evaluation_score_band": "strong",
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["evaluation_score_band"] == "strong"
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "score_band='strong'" in cap
    rows = agent_evaluator_operator_metrics_table_rows(m)
    assert any(r["field"] == "Evaluation score band" for r in rows)


def test_agent_evaluator_operator_metrics_branch_and_llm_status() -> None:
    ae = {
        "evaluation_branch": "rules_with_llm_policy",
        "llm_evaluation_status": "needs_work",
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["evaluation_branch"] == "rules_with_llm_policy"
    assert m["llm_evaluation_status"] == "needs_work"
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "branch='rules_with_llm_policy'" in cap
    assert "llm_status='needs_work'" in cap
    rows = agent_evaluator_operator_metrics_table_rows(m)
    assert any(r["field"] == "Evaluation branch" for r in rows)
    assert any(r["field"] == "LLM evaluation status" for r in rows)


def test_agent_evaluator_operator_metrics_llm_policy_score_band() -> None:
    ae = {
        "evaluation_score": 0.8,
        "evaluation_score_band": "meets_threshold",
        "llm_evaluation_score_band": "meets_threshold",
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["llm_evaluation_score_band"] == "meets_threshold"
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "llm_policy_score_band='meets_threshold'" in cap
    rows = agent_evaluator_operator_metrics_table_rows(m)
    assert any(r["field"] == "LLM policy score band" for r in rows)


def test_agent_evaluator_operator_metrics_rules_score_scalar() -> None:
    ae = {"evaluation_score": 0.875, "evaluation_score_band": "meets_threshold"}
    m = agent_evaluator_operator_metrics(ae)
    assert m["evaluation_score"] == 0.875
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "rules_score=0.875" in cap
    rows = agent_evaluator_operator_metrics_table_rows(m)
    assert any(r["field"] == "Rules evaluation score" for r in rows)


def test_agent_evaluator_operator_metrics_llm_policy_score_scalar() -> None:
    ae = {"llm_evaluation_score": 0.75, "llm_evaluation_score_band": "meets_threshold"}
    m = agent_evaluator_operator_metrics(ae)
    assert m["llm_evaluation_score"] == 0.75
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "llm_policy_score=0.750" in cap
    rows = agent_evaluator_operator_metrics_table_rows(m)
    assert any(r["field"] == "LLM policy score" and "0.750" in r["value"] for r in rows)


def test_agent_evaluator_operator_metrics_auto_promote_applied() -> None:
    ae = {
        "persona_id": "backend_engineer",
        "attempt": 1,
        "auto_promote_applied": True,
        "auto_create_applied": False,
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["has_persona_id"] is True
    assert m["auto_promote_applied"] is True
    assert m["auto_create_applied"] is False
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "auto-promote applied" in cap
    assert "auto-create skipped" in cap


def test_agent_evaluator_operator_metrics_auto_create_with_shelf() -> None:
    ae = {
        "auto_create_applied": True,
        "auto_create_shelf": "business_area",
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["has_auto_create_shelf"] is True
    rows = agent_evaluator_operator_metrics_table_rows(m)
    assert any(r["field"] == "Has auto-create shelf" for r in rows)


def test_agent_evaluator_operator_metrics_coverage_and_gate() -> None:
    ae = {
        "coverage_ratio": 0.85,
        "promotion_ready": True,
        "critique_gate_verdict": "pass",
        "evaluation_gaps": ["gap-a"],
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["coverage_ratio"] == 0.85
    assert m["promotion_ready"] is True
    assert m["critique_gate_verdict"] == "PASS"
    assert m["evaluation_gaps_count"] == 1
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "coverage_ratio=0.850" in cap
    assert "coverage_gate='PASS'" in cap
    rows = agent_evaluator_operator_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Coverage ratio"] == "0.850"
    assert by["Persona coverage gate"] == "PASS"


def test_agent_evaluator_operator_metrics_persona_coverage_branch() -> None:
    ae = {"persona_coverage_critique_branch": "llm_with_rules_fallback"}
    m = agent_evaluator_operator_metrics(ae)
    assert m["persona_coverage_critique_branch"] == "llm_with_rules_fallback"
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "pcc_branch='llm_with_rules_fallback'" in cap


def test_agent_evaluator_operator_metrics_export() -> None:
    ae = {"auto_promote_applied": True}
    m = agent_evaluator_operator_metrics(ae)
    parsed = json.loads(agent_evaluator_operator_metrics_export_json(m))
    assert parsed["auto_promote_applied"] is True
    assert json.loads(agent_evaluator_operator_metrics_export_json(None)) == {}
    rows = agent_evaluator_operator_metrics_table_rows(m)
    csv_text = agent_evaluator_operator_metrics_table_rows_csv(rows)
    assert csv_text.startswith("field,value")
    assert agent_evaluator_operator_metrics_table_rows_csv([]) == ""
    assert agent_evaluator_operator_metrics_export_filename_slug("AB@cd") == "ab_cd"


def test_agent_evaluator_operator_metrics_rules_vs_llm_delta() -> None:
    ae = {
        "evaluation_score": 0.8,
        "evaluation_score_band": "meets_threshold",
        "llm_evaluation_score": 0.9,
        "llm_evaluation_score_band": "strong",
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["rules_vs_llm_score_delta"] == 0.1
    assert m["llm_rules_score_agreement"] is False
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "llm_minus_rules=+0.100" in cap
    assert "bands_differ" in cap


def test_agent_evaluator_operator_metrics_llm_rules_band_agreement() -> None:
    ae = {
        "evaluation_score": 0.85,
        "evaluation_score_band": "meets_threshold",
        "llm_evaluation_score": 0.8,
        "llm_evaluation_score_band": "meets_threshold",
    }
    m = agent_evaluator_operator_metrics(ae)
    assert m["llm_rules_score_agreement"] is True
    cap = agent_evaluator_operator_metrics_caption(m)
    assert cap is not None
    assert "bands_agree" in cap
