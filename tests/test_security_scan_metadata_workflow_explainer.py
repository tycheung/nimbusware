"""§14 #18 / fo136: read-only security scan metadata workflow explainer payload."""

from __future__ import annotations

import json
from pathlib import Path

from nimbusware_console.security_scan_metadata_workflow_explainer import (
    security_scan_metadata_effective_enabled_caption,
    security_scan_metadata_env_gate_caption,
    security_scan_metadata_explainer_export_json,
    security_scan_metadata_explainer_table_rows,
    security_scan_metadata_explainer_table_rows_csv,
    security_scan_metadata_export_filename_slug,
    security_scan_metadata_mapping_key_count_caption,
    security_scan_metadata_workflow_explainer_operator_metrics,
    security_scan_metadata_workflow_explainer_operator_metrics_caption,
    security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug,
    security_scan_metadata_workflow_explainer_operator_metrics_export_json,
    security_scan_metadata_workflow_explainer_payload,
    security_scan_metadata_workflow_yaml_file_bytes_caption,
    security_scan_metadata_workflow_yaml_relpath_caption,
    security_scan_metadata_workflow_yaml_string_key_count_caption,
    security_scan_metadata_workflow_yaml_version_caption,
    security_scan_metadata_yaml_effective_mismatch_caption,
    security_scan_metadata_yaml_raw_type_caption,
)


def _write_profile(tmp_path: Path, name: str, body: str) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_security_scan_metadata_workflow_yaml_relpath_caption(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, "wf", "version: 1\n")
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="wf",
    )
    cap = security_scan_metadata_workflow_yaml_relpath_caption(pl)
    assert cap is not None
    assert "wf.yaml" in cap
    assert security_scan_metadata_workflow_yaml_relpath_caption(None) is None
    assert security_scan_metadata_workflow_yaml_relpath_caption(
        {"load_error": "bad"},
    ) is None


def test_security_scan_metadata_workflow_yaml_version_caption(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, "wf", "version: 2\n")
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="wf",
    )
    cap = security_scan_metadata_workflow_yaml_version_caption(pl)
    assert cap is not None
    assert "**2**" in cap
    assert security_scan_metadata_workflow_yaml_version_caption(None) is None
    assert security_scan_metadata_workflow_yaml_version_caption(
        {"load_error": "bad"},
    ) is None
    assert security_scan_metadata_workflow_yaml_version_caption(
        {"workflow_yaml_top_level_version_int": 0},
    ) is None
    assert security_scan_metadata_workflow_yaml_version_caption(
        {"workflow_yaml_top_level_version_int": True},
    ) is None


def test_security_scan_metadata_workflow_yaml_string_key_count_caption(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, "wf", "version: 1\nname: demo\n")
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="wf",
    )
    cap = security_scan_metadata_workflow_yaml_string_key_count_caption(pl)
    assert cap is not None
    raw = pl.get("workflow_yaml_top_level_string_key_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert security_scan_metadata_workflow_yaml_string_key_count_caption(None) is None
    assert security_scan_metadata_workflow_yaml_string_key_count_caption(
        {"load_error": "bad"},
    ) is None


def test_security_scan_metadata_workflow_yaml_file_bytes_caption(
    tmp_path: Path,
) -> None:
    _write_profile(tmp_path, "wf", "version: 1\n")
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="wf",
    )
    cap = security_scan_metadata_workflow_yaml_file_bytes_caption(pl)
    assert cap is not None
    assert "bytes" in cap
    raw = pl.get("workflow_yaml_file_bytes")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert security_scan_metadata_workflow_yaml_file_bytes_caption(None) is None
    assert security_scan_metadata_workflow_yaml_file_bytes_caption(
        {"load_error": "bad"},
    ) is None
    assert security_scan_metadata_workflow_yaml_file_bytes_caption(
        {"workflow_yaml_file_bytes": -1},
    ) is None
    assert security_scan_metadata_workflow_yaml_file_bytes_caption(
        {"workflow_yaml_file_bytes": True},
    ) is None


def test_security_scan_metadata_yaml_raw_type_caption() -> None:
    cap = security_scan_metadata_yaml_raw_type_caption(
        {"security_scan_metadata_on_verify_yaml_raw_type": "dict"},
    )
    assert cap is not None
    assert "**dict**" in cap
    assert security_scan_metadata_yaml_raw_type_caption(None) is None
    assert security_scan_metadata_yaml_raw_type_caption({}) is None
    assert security_scan_metadata_yaml_raw_type_caption(
        {"load_error": "bad"},
    ) is None


def test_security_scan_metadata_effective_enabled_caption() -> None:
    cap = security_scan_metadata_effective_enabled_caption(
        {"yaml_parsed_bool": True, "effective_enabled": False},
    )
    assert cap is not None
    assert "yaml_parsed_bool=**true**" in cap
    assert "effective_enabled=**false**" in cap
    assert security_scan_metadata_effective_enabled_caption(None) is None
    assert security_scan_metadata_effective_enabled_caption({}) is None
    assert security_scan_metadata_effective_enabled_caption(
        {"load_error": "bad yaml"},
    ) is None
    assert security_scan_metadata_effective_enabled_caption(
        {"yaml_parsed_bool": "yes", "effective_enabled": True},
    ) is None


def test_security_scan_metadata_env_gate_caption() -> None:
    cap_off = security_scan_metadata_env_gate_caption(
        {
            "HERMES_ATTACH_SECURITY_SCAN_METADATA": {
                "forces_off": True,
                "raw": "0",
            },
        },
    )
    assert cap_off is not None
    assert "kill-switch" in cap_off
    cap_on = security_scan_metadata_env_gate_caption(
        {
            "HERMES_ATTACH_SECURITY_SCAN_METADATA": {
                "forces_on": True,
                "raw": "1",
            },
        },
    )
    assert cap_on is not None
    assert "force-on" in cap_on
    cap_unset = security_scan_metadata_env_gate_caption(
        {
            "HERMES_ATTACH_SECURITY_SCAN_METADATA": {
                "unset_follows_yaml": True,
            },
        },
    )
    assert cap_unset is not None
    assert "unset" in cap_unset
    assert security_scan_metadata_env_gate_caption(None) is None
    assert security_scan_metadata_env_gate_caption({"load_error": "bad"}) is None


def test_explainer_scalar_true(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_scalar",
        "version: 1\nsecurity_scan_metadata_on_verify: true\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_scalar",
    )
    assert pl["yaml_parsed_bool"] is True
    assert pl["effective_enabled"] is True
    assert pl["security_scan_metadata_on_verify_yaml_key_present"] is True
    assert pl["security_scan_metadata_on_verify_yaml_value"] is True
    assert pl["security_scan_metadata_on_verify_yaml_raw_type"] == "bool"
    assert pl["security_scan_metadata_on_verify_mapping_string_key_count"] is None
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2
    wf_path = tmp_path / "configs" / "workflows" / "sec_scalar.yaml"
    assert pl["workflow_yaml_file_bytes"] == wf_path.stat().st_size
    assert pl["load_error"] is None


def test_explainer_dict_enabled_false(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_dict_off",
        "version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: false\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_dict_off",
    )
    assert pl["yaml_parsed_bool"] is False
    assert pl["effective_enabled"] is False
    assert pl["security_scan_metadata_on_verify_yaml_value"] == {"enabled": False}
    assert pl["security_scan_metadata_on_verify_yaml_raw_type"] == "dict"
    assert pl["security_scan_metadata_on_verify_mapping_string_key_count"] == 1
    assert pl["security_scan_metadata_yaml_parsed_bool_matches_effective"] is True
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_explainer_mapping_empty_counts_zero(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_empty_map",
        "version: 1\nsecurity_scan_metadata_on_verify: {}\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_empty_map",
    )
    assert pl["security_scan_metadata_on_verify_yaml_raw_type"] == "dict"
    assert pl["security_scan_metadata_on_verify_mapping_string_key_count"] == 0
    assert pl["security_scan_metadata_yaml_parsed_bool_matches_effective"] is True
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_explainer_missing_key(tmp_path: Path) -> None:
    _write_profile(tmp_path, "bare", "version: 1\n")
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="bare",
    )
    assert pl["security_scan_metadata_on_verify_yaml_key_present"] is False
    assert pl["security_scan_metadata_on_verify_yaml_value"] is None
    assert pl["security_scan_metadata_on_verify_yaml_raw_type"] is None
    assert pl["security_scan_metadata_on_verify_mapping_string_key_count"] is None
    assert pl["yaml_parsed_bool"] is False
    assert pl["effective_enabled"] is False
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 1


def test_explainer_workflow_yaml_top_level_version_missing(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "no_ver",
        "security_scan_metadata_on_verify: true\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="no_ver",
    )
    assert pl["workflow_yaml_top_level_version_int"] is None
    assert pl["workflow_yaml_top_level_string_key_count"] == 1
    assert pl["yaml_parsed_bool"] is True
    assert pl["effective_enabled"] is True


def test_explainer_workflow_yaml_top_level_version_non_int_returns_none(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "v_bad",
        "version: \"1\"\nsecurity_scan_metadata_on_verify: false\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="v_bad",
    )
    assert pl["workflow_yaml_top_level_version_int"] is None
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_explainer_workflow_yaml_top_level_string_key_count_none_without_profile(
    tmp_path: Path,
) -> None:
    pl = security_scan_metadata_workflow_explainer_payload(tmp_path, workflow_profile=None)
    assert pl["workflow_yaml_top_level_string_key_count"] is None


def test_explainer_env_force_on_overrides_yaml_off(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("HERMES_ATTACH_SECURITY_SCAN_METADATA", "1")
    _write_profile(
        tmp_path,
        "sec_off",
        "version: 1\nsecurity_scan_metadata_on_verify: false\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_off",
    )
    assert pl["yaml_parsed_bool"] is False
    assert pl["effective_enabled"] is True
    env = pl["HERMES_ATTACH_SECURITY_SCAN_METADATA"]
    assert isinstance(env, dict)
    assert env.get("forces_on") is True
    assert pl["security_scan_metadata_yaml_parsed_bool_matches_effective"] is False
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_explainer_yaml_raw_type_for_explicit_null(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_null",
        "version: 1\nsecurity_scan_metadata_on_verify: null\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_null",
    )
    assert pl["security_scan_metadata_on_verify_yaml_key_present"] is True
    assert pl["security_scan_metadata_on_verify_yaml_value"] is None
    assert pl["security_scan_metadata_on_verify_yaml_raw_type"] is None
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_explainer_yaml_raw_type_for_string_scalar(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_str",
        "version: 1\nsecurity_scan_metadata_on_verify: 'yes'\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_str",
    )
    assert pl["security_scan_metadata_on_verify_yaml_raw_type"] == "str"
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_explainer_env_kill_switch_overrides_yaml_on(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("HERMES_ATTACH_SECURITY_SCAN_METADATA", "0")
    _write_profile(
        tmp_path,
        "sec_on",
        "version: 1\nsecurity_scan_metadata_on_verify: true\n",
    )
    pl = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sec_on",
    )
    assert pl["yaml_parsed_bool"] is True
    assert pl["effective_enabled"] is False
    env = pl["HERMES_ATTACH_SECURITY_SCAN_METADATA"]
    assert isinstance(env, dict)
    assert env.get("forces_off") is True
    assert pl["security_scan_metadata_yaml_parsed_bool_matches_effective"] is False
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["workflow_yaml_top_level_string_key_count"] == 2


def test_yaml_effective_mismatch_caption_when_env_overrides() -> None:
    cap = security_scan_metadata_yaml_effective_mismatch_caption(
        {"security_scan_metadata_yaml_parsed_bool_matches_effective": False},
    )
    assert cap is not None
    assert "yaml_parsed_bool" in cap
    assert "effective_enabled" in cap


def test_yaml_effective_mismatch_caption_none_when_aligned() -> None:
    assert (
        security_scan_metadata_yaml_effective_mismatch_caption(
            {"security_scan_metadata_yaml_parsed_bool_matches_effective": True},
        )
        is None
    )


def test_yaml_effective_mismatch_caption_none_for_bad_payload() -> None:
    assert security_scan_metadata_yaml_effective_mismatch_caption(None) is None
    assert security_scan_metadata_yaml_effective_mismatch_caption("x") is None


def test_security_scan_metadata_operator_metrics_yaml_effective_mismatch() -> None:
    from nimbusware_console.security_scan_metadata_workflow_explainer import (
        security_scan_metadata_workflow_explainer_operator_metrics,
    )

    payload = {
        "security_scan_metadata_yaml_parsed_bool_matches_effective": False,
        "yaml_parsed_bool": True,
        "effective_enabled": False,
    }
    m = security_scan_metadata_workflow_explainer_operator_metrics(payload)
    assert m["yaml_effective_mismatch"] is True
    assert m["yaml_matches_effective"] is False


def test_mapping_key_count_caption_for_dict_payload() -> None:
    cap = security_scan_metadata_mapping_key_count_caption(
        {
            "security_scan_metadata_on_verify_yaml_raw_type": "dict",
            "security_scan_metadata_on_verify_mapping_string_key_count": 2,
        },
    )
    assert cap is not None
    assert "**2**" in cap


def test_mapping_key_count_caption_none_for_scalar_type() -> None:
    assert (
        security_scan_metadata_mapping_key_count_caption(
            {
                "security_scan_metadata_on_verify_yaml_raw_type": "bool",
                "security_scan_metadata_on_verify_mapping_string_key_count": None,
            },
        )
        is None
    )


def test_mapping_key_count_caption_none_for_bad_payload() -> None:
    assert security_scan_metadata_mapping_key_count_caption(None) is None
    assert security_scan_metadata_mapping_key_count_caption("x") is None


def test_security_scan_metadata_explainer_table_rows_export_json_and_csv(
    tmp_path: Path,
) -> None:
    _write_profile(
        tmp_path,
        "wf",
        "version: 1\nsecurity_scan_metadata_on_verify: true\n",
    )
    payload = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="wf",
    )
    rows = security_scan_metadata_explainer_table_rows(payload)
    fields = {r["field"] for r in rows}
    assert "effective_enabled" in fields
    assert "yaml_parsed_bool" in fields
    env_row = next(
        r for r in rows if r["field"] == "HERMES_ATTACH_SECURITY_SCAN_METADATA"
    )
    assert '"unset_follows_yaml"' in env_row["value"]
    assert len(rows) == len(payload)
    parsed = json.loads(security_scan_metadata_explainer_export_json(payload))
    assert parsed == payload
    csv_text = security_scan_metadata_explainer_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert security_scan_metadata_explainer_table_rows({}) == []  # type: ignore[arg-type]
    assert security_scan_metadata_explainer_table_rows_csv([]) == ""
    assert security_scan_metadata_export_filename_slug() == "security_scan_metadata"


def test_security_scan_metadata_workflow_explainer_operator_metrics_file_bytes() -> None:
    payload = {
        "security_scan_metadata_on_verify_yaml_key_present": True,
        "workflow_yaml_file_bytes": 4096,
    }
    m = security_scan_metadata_workflow_explainer_operator_metrics(payload)
    assert m["workflow_yaml_file_bytes"] == 4096
    cap = security_scan_metadata_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "4096" in cap


def test_security_scan_metadata_workflow_explainer_operator_metrics_env_forces_on() -> None:
    payload = {
        "security_scan_metadata_on_verify_yaml_key_present": True,
        "yaml_parsed_bool": False,
        "effective_enabled": True,
        "security_scan_metadata_yaml_parsed_bool_matches_effective": False,
        "HERMES_ATTACH_SECURITY_SCAN_METADATA": {
            "forces_on": True,
            "forces_off": False,
            "unset": False,
        },
    }
    m = security_scan_metadata_workflow_explainer_operator_metrics(payload)
    assert m["env_forces_on"] is True
    assert m["yaml_matches_effective"] is False
    cap = security_scan_metadata_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "mismatch" in cap


def test_security_scan_metadata_explainer_metrics_effective_disabled_caption() -> None:
    m = security_scan_metadata_workflow_explainer_operator_metrics(
        {
            "security_scan_metadata_on_verify_yaml_key_present": True,
            "yaml_parsed_bool": False,
            "effective_enabled": False,
        },
    )
    cap = security_scan_metadata_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "disabled" in cap


def test_security_scan_metadata_workflow_explainer_operator_metrics_export() -> None:
    m = security_scan_metadata_workflow_explainer_operator_metrics(None)
    assert json.loads(
        security_scan_metadata_workflow_explainer_operator_metrics_export_json(m),
    ) == m
    assert (
        security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug()
        == "security_scan_metadata_workflow_explainer_operator_metrics"
    )
