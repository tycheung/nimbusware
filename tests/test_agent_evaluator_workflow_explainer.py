"""§14 #15."""

from __future__ import annotations

import json
from pathlib import Path

from nimbusware_console.agent_evaluator_workflow_explainer import (
    agent_evaluator_auto_create_env_gate_caption,
    agent_evaluator_auto_promote_env_gate_caption,
    agent_evaluator_env_gate_caption,
    agent_evaluator_explainer_export_json,
    agent_evaluator_explainer_table_rows,
    agent_evaluator_explainer_table_rows_csv,
    agent_evaluator_export_filename_slug,
    agent_evaluator_llm_evaluation_enabled_caption,
    agent_evaluator_persona_id_caption,
    agent_evaluator_workflow_explainer_operator_metrics,
    agent_evaluator_workflow_explainer_operator_metrics_caption,
    agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug,
    agent_evaluator_workflow_explainer_operator_metrics_export_json,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows,
    agent_evaluator_workflow_explainer_payload,
    agent_evaluator_workflow_yaml_version_caption,
    agent_evaluator_would_emit_caption,
    agent_evaluator_yaml_key_present_caption,
    agent_evaluator_yaml_parsed_enabled_caption,
    agent_evaluator_yaml_raw_type_caption,
    agent_evaluator_yaml_true_bool_count_caption,
)


def _write_profile(tmp_path: Path, name: str, body: str) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_agent_evaluator_env_gate_caption() -> None:
    cap_off = agent_evaluator_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR": {
                "forces_off": True,
                "raw": "0",
            },
        },
    )
    assert cap_off is not None
    assert "kill-switch" in cap_off
    cap_on = agent_evaluator_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR": {
                "forces_on": True,
                "raw": "1",
            },
        },
    )
    assert cap_on is not None
    assert "force-on" in cap_on
    cap_unset = agent_evaluator_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR": {
                "unset": True,
            },
        },
    )
    assert cap_unset is not None
    assert "unset" in cap_unset
    assert agent_evaluator_env_gate_caption(None) is None
    assert agent_evaluator_env_gate_caption({"load_error": "bad"}) is None


def test_agent_evaluator_auto_promote_env_gate_caption() -> None:
    cap_off = agent_evaluator_auto_promote_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR_AUTO_PROMOTE": {
                "disables_auto_promote": True,
                "raw": "0",
            },
        },
    )
    assert cap_off is not None
    assert "kill-switch" in cap_off
    cap_unset = agent_evaluator_auto_promote_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR_AUTO_PROMOTE": {
                "unset": True,
            },
        },
    )
    assert cap_unset is not None
    assert "unset" in cap_unset
    cap_bad = agent_evaluator_auto_promote_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR_AUTO_PROMOTE": {
                "unrecognised_value": True,
                "raw": "maybe",
            },
        },
    )
    assert cap_bad is not None
    assert "unrecognised" in cap_bad
    assert agent_evaluator_auto_promote_env_gate_caption(None) is None
    assert agent_evaluator_auto_promote_env_gate_caption({"load_error": "bad"}) is None


def test_agent_evaluator_auto_create_env_gate_caption() -> None:
    cap_off = agent_evaluator_auto_create_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR_AUTO_CREATE": {
                "disables_auto_create": True,
                "raw": "0",
            },
        },
    )
    assert cap_off is not None
    assert "kill-switch" in cap_off
    cap_unset = agent_evaluator_auto_create_env_gate_caption(
        {
            "HERMES_AGENT_EVALUATOR_AUTO_CREATE": {
                "unset": True,
            },
        },
    )
    assert cap_unset is not None
    assert "unset" in cap_unset
    assert agent_evaluator_auto_create_env_gate_caption(None) is None
    assert agent_evaluator_auto_create_env_gate_caption({"load_error": "bad"}) is None


def test_agent_evaluator_yaml_key_present_caption() -> None:
    cap_absent = agent_evaluator_yaml_key_present_caption(
        {"agent_evaluator_yaml_key_present": False},
    )
    assert cap_absent is not None
    assert "absent" in cap_absent
    cap_on = agent_evaluator_yaml_key_present_caption(
        {
            "agent_evaluator_yaml_key_present": True,
            "yaml_parsed_enabled": True,
        },
    )
    assert cap_on is not None
    assert "present" in cap_on
    assert "true" in cap_on
    cap_off = agent_evaluator_yaml_key_present_caption(
        {
            "agent_evaluator_yaml_key_present": True,
            "yaml_parsed_enabled": False,
        },
    )
    assert cap_off is not None
    assert "false" in cap_off
    assert agent_evaluator_yaml_key_present_caption(None) is None
    assert agent_evaluator_yaml_key_present_caption({"load_error": "bad"}) is None


def test_agent_evaluator_persona_id_caption() -> None:
    cap = agent_evaluator_persona_id_caption(
        {"yaml_parsed_persona_id": "default"},
    )
    assert cap is not None
    assert "`default`" in cap
    cap_custom = agent_evaluator_persona_id_caption(
        {"yaml_parsed_persona_id": "  custom-p  "},
    )
    assert cap_custom is not None
    assert "`custom-p`" in cap_custom
    assert agent_evaluator_persona_id_caption(None) is None
    assert agent_evaluator_persona_id_caption({"load_error": "bad"}) is None
    assert agent_evaluator_persona_id_caption({}) is None
    assert agent_evaluator_persona_id_caption(
        {"yaml_parsed_persona_id": ""},
    ) is None
    assert agent_evaluator_persona_id_caption(
        {"yaml_parsed_persona_id": "   "},
    ) is None


def test_agent_evaluator_yaml_parsed_enabled_caption() -> None:
    cap_on = agent_evaluator_yaml_parsed_enabled_caption(
        {
            "agent_evaluator_yaml_key_present": True,
            "yaml_parsed_enabled": True,
        },
    )
    assert cap_on is not None
    assert "**true**" in cap_on
    cap_off = agent_evaluator_yaml_parsed_enabled_caption(
        {
            "agent_evaluator_yaml_key_present": True,
            "yaml_parsed_enabled": False,
        },
    )
    assert cap_off is not None
    assert "**false**" in cap_off
    assert agent_evaluator_yaml_parsed_enabled_caption(None) is None
    assert agent_evaluator_yaml_parsed_enabled_caption({"load_error": "bad"}) is None
    assert agent_evaluator_yaml_parsed_enabled_caption(
        {"agent_evaluator_yaml_key_present": False, "yaml_parsed_enabled": True},
    ) is None
    assert agent_evaluator_yaml_parsed_enabled_caption(
        {"agent_evaluator_yaml_key_present": True, "yaml_parsed_enabled": "yes"},
    ) is None


def test_agent_evaluator_llm_evaluation_enabled_caption() -> None:
    cap_on = agent_evaluator_llm_evaluation_enabled_caption(
        {
            "agent_evaluator_yaml_key_present": True,
            "yaml_parsed_llm_evaluation_enabled": True,
        },
    )
    assert cap_on is not None
    assert "llm_evaluation_enabled" in cap_on
    assert "**on**" in cap_on
    cap_off = agent_evaluator_llm_evaluation_enabled_caption(
        {
            "agent_evaluator_yaml_key_present": True,
            "yaml_parsed_llm_evaluation_enabled": False,
        },
    )
    assert cap_off is not None
    assert "**off**" in cap_off
    assert agent_evaluator_llm_evaluation_enabled_caption(None) is None


def test_agent_evaluator_workflow_explainer_payload_llm_evaluation_enabled(
    tmp_path: Path,
) -> None:
    _write_profile(
        tmp_path,
        "ae_llm",
        "version: 1\nagent_evaluator:\n  enabled: true\n  llm_evaluation_enabled: true\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(tmp_path, workflow_profile="ae_llm")
    assert pl.get("yaml_parsed_llm_evaluation_enabled") is True


def test_agent_evaluator_would_emit_caption() -> None:
    cap_on = agent_evaluator_would_emit_caption({"would_emit_stage_started": True})
    assert cap_on is not None
    assert "would emit" in cap_on
    cap_off = agent_evaluator_would_emit_caption({"would_emit_stage_started": False})
    assert cap_off is not None
    assert "would not emit" in cap_off
    assert agent_evaluator_would_emit_caption(None) is None
    assert agent_evaluator_would_emit_caption({"load_error": "bad"}) is None


def test_agent_evaluator_yaml_raw_type_caption(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "ae",
        "version: 1\nagent_evaluator:\n  enabled: true\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae",
    )
    cap = agent_evaluator_yaml_raw_type_caption(pl)
    assert cap is not None
    assert "**dict**" in cap
    assert agent_evaluator_yaml_raw_type_caption(None) is None
    assert agent_evaluator_yaml_raw_type_caption({"load_error": "bad"}) is None
    assert agent_evaluator_yaml_raw_type_caption({}) is None


def test_agent_evaluator_yaml_true_bool_count_caption(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "ae",
        "version: 1\nagent_evaluator:\n  enabled: true\n  auto_promote_probation: true\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae",
    )
    cap = agent_evaluator_yaml_true_bool_count_caption(pl)
    assert cap is not None
    raw = pl.get("agent_evaluator_yaml_true_bool_value_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert agent_evaluator_yaml_true_bool_count_caption(None) is None
    assert agent_evaluator_yaml_true_bool_count_caption({"load_error": "bad"}) is None


def test_agent_evaluator_workflow_yaml_version_caption() -> None:
    cap = agent_evaluator_workflow_yaml_version_caption(
        {"workflow_yaml_top_level_version_int": 3},
    )
    assert cap is not None
    assert "**3**" in cap
    assert agent_evaluator_workflow_yaml_version_caption(None) is None
    assert agent_evaluator_workflow_yaml_version_caption(
        {"load_error": "bad"},
    ) is None
    assert agent_evaluator_workflow_yaml_version_caption(
        {"workflow_yaml_top_level_version_int": 0},
    ) is None
    assert agent_evaluator_workflow_yaml_version_caption(
        {"workflow_yaml_top_level_version_int": True},
    ) is None
    cap_one = agent_evaluator_workflow_yaml_version_caption(
        {"workflow_yaml_top_level_version_int": 1},
    )
    assert cap_one is not None
    assert "**1**" in cap_one


def test_explainer_missing_agent_evaluator_key(tmp_path: Path) -> None:
    _write_profile(tmp_path, "bare", "version: 1\n")
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="bare",
    )
    assert pl["agent_evaluator_yaml_key_present"] is False
    assert pl["agent_evaluator_yaml_raw_type"] is None
    assert pl["agent_evaluator_yaml_mapping_string_key_count"] is None
    assert pl["agent_evaluator_yaml_true_bool_value_count"] is None
    assert pl["agent_evaluator_yaml_false_bool_value_count"] is None
    assert pl["yaml_parsed_enabled"] is False
    assert pl["yaml_parsed_persona_id"] == "default"
    assert pl["yaml_parsed_auto_promote_probation"] is False
    assert pl["yaml_parsed_auto_create_persona"] == {
        "enabled": False,
        "shelf": "",
        "display_name": "",
    }
    ac_env = pl["HERMES_AGENT_EVALUATOR_AUTO_CREATE"]
    assert isinstance(ac_env, dict)
    assert ac_env.get("disables_auto_create") is False
    assert pl["would_emit_stage_started"] is False
    assert pl["load_error"] is None
    assert pl["workflow_yaml_top_level_version_int"] == 1


def test_explainer_workflow_yaml_top_level_version_missing(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "no_ver",
        "agent_evaluator:\n  enabled: false\n  persona_id: x\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="no_ver",
    )
    assert pl["workflow_yaml_top_level_version_int"] is None
    _write_profile(
        tmp_path,
        "ae_on",
        "version: 1\nagent_evaluator:\n  enabled: true\n  persona_id: custom-p\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae_on",
    )
    assert pl["agent_evaluator_yaml_key_present"] is True
    assert pl["agent_evaluator_yaml_raw_type"] == "dict"
    assert pl["agent_evaluator_yaml_mapping_string_key_count"] == 2
    assert pl["agent_evaluator_yaml_true_bool_value_count"] == 1
    assert pl["agent_evaluator_yaml_false_bool_value_count"] == 0
    assert pl["yaml_parsed_enabled"] is True
    assert pl["yaml_parsed_persona_id"] == "custom-p"
    assert pl["yaml_parsed_auto_promote_probation"] is False
    assert pl["would_emit_stage_started"] is True


def test_explainer_workflow_disabled(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "ae_off",
        "version: 1\nagent_evaluator:\n  enabled: false\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae_off",
    )
    assert pl["yaml_parsed_enabled"] is False
    assert pl["agent_evaluator_yaml_raw_type"] == "dict"
    assert pl["agent_evaluator_yaml_mapping_string_key_count"] == 1
    assert pl["agent_evaluator_yaml_true_bool_value_count"] == 0
    assert pl["agent_evaluator_yaml_false_bool_value_count"] == 1
    assert pl["would_emit_stage_started"] is False


def test_explainer_auto_promote_probation_yaml_true(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "ae_promo",
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: x\n  auto_promote_probation: true\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae_promo",
    )
    assert pl["yaml_parsed_auto_promote_probation"] is True
    ap = pl["HERMES_AGENT_EVALUATOR_AUTO_PROMOTE"]
    assert isinstance(ap, dict)
    assert ap.get("disables_auto_promote") is False
    assert pl["agent_evaluator_yaml_raw_type"] == "dict"
    assert pl["agent_evaluator_yaml_mapping_string_key_count"] == 3
    assert pl["agent_evaluator_yaml_true_bool_value_count"] == 2


def test_explainer_auto_create_persona_yaml_block(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "ae_create",
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: net_new_ae_pid\n"
        "  auto_create_persona:\n"
        "    enabled: true\n"
        "    shelf: business_area\n"
        "    display_name: Net New AE\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae_create",
    )
    ac = pl["yaml_parsed_auto_create_persona"]
    assert ac == {
        "enabled": True,
        "shelf": "business_area",
        "display_name": "Net New AE",
    }
    env_ac = pl["HERMES_AGENT_EVALUATOR_AUTO_CREATE"]
    assert isinstance(env_ac, dict)
    assert env_ac.get("disables_auto_create") is False
    assert pl["agent_evaluator_yaml_true_bool_value_count"] == 1


def test_explainer_env_force_on_overrides_workflow_off(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "1")
    _write_profile(
        tmp_path,
        "ae_off",
        "version: 1\nagent_evaluator:\n  enabled: false\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae_off",
    )
    assert pl["yaml_parsed_enabled"] is False
    assert pl["would_emit_stage_started"] is True
    env = pl["HERMES_AGENT_EVALUATOR"]
    assert isinstance(env, dict)
    assert env.get("forces_on") is True


def test_explainer_env_kill_switch_overrides_workflow_on(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "0")
    _write_profile(
        tmp_path,
        "ae_on",
        "version: 1\nagent_evaluator:\n  enabled: true\n",
    )
    pl = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae_on",
    )
    assert pl["yaml_parsed_enabled"] is True
    assert pl["would_emit_stage_started"] is False
    env = pl["HERMES_AGENT_EVALUATOR"]
    assert isinstance(env, dict)
    assert env.get("forces_off") is True


def test_agent_evaluator_explainer_table_rows_export_json_and_csv(
    tmp_path: Path,
) -> None:
    _write_profile(
        tmp_path,
        "ae",
        "version: 1\n"
        "agent_evaluator:\n"
        "  enabled: true\n"
        "  persona_id: p1\n",
    )
    payload = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="ae",
    )
    rows = agent_evaluator_explainer_table_rows(payload)
    fields = {r["field"] for r in rows}
    assert "yaml_parsed_enabled" in fields
    assert "would_emit_stage_started" in fields
    assert len(rows) == len(payload)
    parsed = json.loads(agent_evaluator_explainer_export_json(payload))
    assert parsed == payload
    csv_text = agent_evaluator_explainer_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert agent_evaluator_explainer_table_rows({}) == []  # type: ignore[arg-type]
    assert agent_evaluator_explainer_table_rows_csv([]) == ""
    assert agent_evaluator_export_filename_slug() == "agent_evaluator"


def test_agent_evaluator_explainer_table_rows_minimal_fixture() -> None:
    payload = {
        "workflow_profile": "wf",
        "yaml_parsed_enabled": True,
        "HERMES_AGENT_EVALUATOR": {"forces_off": False, "forces_on": True},
    }
    rows = agent_evaluator_explainer_table_rows(payload)
    assert len(rows) == 3
    env_row = next(r for r in rows if r["field"] == "HERMES_AGENT_EVALUATOR")
    assert '"forces_on": true' in env_row["value"]
    assert json.loads(agent_evaluator_explainer_export_json(payload)) == payload


def test_agent_evaluator_workflow_explainer_operator_metrics_would_emit_llm() -> None:
    payload = {
        "would_emit_llm_evaluation": True,
        "yaml_parsed_llm_evaluation_enabled": True,
        "would_emit_stage_started": True,
    }
    m = agent_evaluator_workflow_explainer_operator_metrics(payload)
    assert m["would_emit_llm_evaluation"] is True
    cap = agent_evaluator_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "LLM branch" in cap


def test_agent_evaluator_workflow_explainer_operator_metrics_llm_and_env_gates() -> None:
    payload = {
        "yaml_parsed_llm_evaluation_enabled": True,
        "HERMES_AGENT_EVALUATOR_AUTO_PROMOTE": {"disables_auto_promote": True},
        "HERMES_AGENT_EVALUATOR_AUTO_CREATE": {"disables_auto_create": True},
    }
    m = agent_evaluator_workflow_explainer_operator_metrics(payload)
    assert m["llm_evaluation_enabled"] is True
    assert m["auto_promote_disabled"] is True
    assert m["auto_create_disabled"] is True
    cap = agent_evaluator_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "LLM" in cap
    assert "auto-promote" in cap


def test_agent_evaluator_workflow_explainer_operator_metrics_yaml_bool_counts() -> None:
    payload = {
        "agent_evaluator_yaml_true_bool_value_count": 2,
        "agent_evaluator_yaml_false_bool_value_count": 1,
    }
    m = agent_evaluator_workflow_explainer_operator_metrics(payload)
    assert m["yaml_true_bool_value_count"] == 2
    assert m["yaml_false_bool_value_count"] == 1
    cap = agent_evaluator_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "true" in cap.lower()


def test_agent_evaluator_workflow_explainer_operator_metrics_env_forces_on() -> None:
    payload = {
        "agent_evaluator_yaml_key_present": True,
        "yaml_parsed_enabled": False,
        "yaml_parsed_persona_id": "p1",
        "would_emit_stage_started": True,
        "HERMES_AGENT_EVALUATOR": {
            "forces_on": True,
            "forces_off": False,
            "unset": False,
        },
        "workflow_yaml_top_level_version_int": 3,
    }
    m = agent_evaluator_workflow_explainer_operator_metrics(payload)
    assert m["env_forces_on"] is True
    assert m["would_emit_stage_started"] is True
    assert m["persona_id_present"] is True
    assert m["workflow_yaml_version_int"] == 3
    cap = agent_evaluator_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "emit" in cap.lower()


def test_agent_evaluator_workflow_explainer_operator_metrics_load_error() -> None:
    m = agent_evaluator_workflow_explainer_operator_metrics(
        {"load_error": "missing file"},
    )
    assert m["load_error_present"] is True
    rows = agent_evaluator_workflow_explainer_operator_metrics_table_rows(m)
    assert any(r["field"] == "Load error" for r in rows)


def test_agent_evaluator_workflow_explainer_operator_metrics_export() -> None:
    m = agent_evaluator_workflow_explainer_operator_metrics({})
    assert json.loads(
        agent_evaluator_workflow_explainer_operator_metrics_export_json(m),
    ) == m
    assert json.loads(
        agent_evaluator_workflow_explainer_operator_metrics_export_json(None),
    ) == {}
    assert (
        agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug()
        == "agent_evaluator_workflow_explainer_operator_metrics"
    )
