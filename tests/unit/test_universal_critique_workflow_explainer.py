"""Unit tests for universal critique workflow explainer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nimbusware_console.universal_critique_timeline_display import (
    universal_critique_snapshot_from_compare_paste,
)
from nimbusware_console.universal_critique_workflow_explainer import (
    universal_critique_default_enabled_caption,
    universal_critique_enabled_stages_caption,
    universal_critique_env_override_deltas,
    universal_critique_env_override_summary_caption,
    universal_critique_explainer_export_json,
    universal_critique_explainer_table_rows,
    universal_critique_explainer_table_rows_csv,
    universal_critique_export_filename_slug,
    universal_critique_workflow_explainer_operator_metrics,
    universal_critique_workflow_explainer_operator_metrics_caption,
    universal_critique_workflow_explainer_operator_metrics_export_filename_slug,
    universal_critique_workflow_explainer_operator_metrics_export_json,
    universal_critique_workflow_explainer_operator_metrics_table_rows,
    universal_critique_workflow_explainer_payload,
    universal_critique_workflow_vs_timeline_rows,
    universal_critique_workflow_yaml_bytes_caption,
    universal_critique_workflow_yaml_relpath_caption,
    universal_critique_yaml_enabled_bucket_caption,
    universal_critique_yaml_present_caption,
    universal_critique_yaml_stage_keys_caption,
    universal_critique_yaml_top_level_enabled_false_count_caption,
    universal_critique_yaml_top_level_enabled_true_count_caption,
    universal_critique_yaml_top_level_list_child_count_caption,
    universal_critique_yaml_top_level_mapping_child_count_caption,
    universal_critique_yaml_top_level_nonempty_count_caption,
)
from nimbusware_env import find_repo_root


@pytest.fixture()
def repo_uc_stub(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "stub.yaml").write_text(
        "version: 1\n"
        "universal_critique:\n"
        "  implementation:\n"
        "    llm: false\n"
        "    stub: true\n"
        "  test_writer:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n"
        "  planner:\n"
        "    enabled: false\n"
        "  frontend_writer:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n"
        "  module_integrator:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n",
        encoding="utf-8",
    )
    return tmp_path


def test_explainer_yaml_and_effective_match_without_env(repo_uc_stub: Path) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    assert out["workflow_profile"] == "stub"
    assert out["universal_critique_yaml_present"] is True
    assert out["universal_critique_yaml_top_level_keys"] == [
        "frontend_writer",
        "implementation",
        "module_integrator",
        "planner",
        "test_writer",
    ]
    assert out["universal_critique_yaml_top_level_nonempty_count"] == 5
    assert out["universal_critique_yaml_top_level_enabled_true_count"] == 3
    assert out["universal_critique_yaml_top_level_enabled_false_count"] == 1
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 5
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 0
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0
    assert out["universal_critique_yaml_top_level_enabled_unset_mapping_count"] == 1
    assert isinstance(out["universal_critique_workflow_yaml_bytes"], int)
    assert out["universal_critique_workflow_yaml_bytes"] > 0
    assert out["load_error"] is None
    assert out["workflow_yaml_relpath"] is not None
    _norm = str(out["workflow_yaml_relpath"]).replace("\\", "/")
    assert _norm.endswith("configs/workflows/stub.yaml")
    assert out["yaml_only"] == out["effective_with_env"]
    assert universal_critique_env_override_deltas(out) == []


def test_explainer_env_overrides_yaml(repo_uc_stub: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_IMPLEMENTATION_CRITIQUE_LLM", "1")
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    assert out["yaml_only"]["impl_llm"] is False
    assert out["effective_with_env"]["impl_llm"] is True
    deltas = universal_critique_env_override_deltas(out)
    assert any(r["knob"] == "impl_llm" for r in deltas)
    assert any(r["yaml_only"] == "False" and r["effective_with_env"] == "True" for r in deltas)


def test_explainer_new_stage_env_overrides_yaml(
    repo_uc_stub: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_ENABLE_FRONTEND_WRITER_CRITIQUE", "0")
    monkeypatch.setenv("HERMES_STUB_MODULE_INTEGRATOR_CRITICS", "0")
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    assert out["yaml_only"]["fw_enabled"] is True
    assert out["effective_with_env"]["fw_enabled"] is False
    assert out["yaml_only"]["mi_stub"] is True
    assert out["effective_with_env"]["mi_stub"] is False


def test_explainer_top_level_scalar_leaf_counts_bool_and_string(tmp_path: Path) -> None:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "scalars.yaml").write_text(
        "version: 2\n"
        "universal_critique:\n"
        "  hard_block: true\n"
        "  note: \"watch\"\n"
        "  implementation:\n"
        "    enabled: false\n",
        encoding="utf-8",
    )
    out = universal_critique_workflow_explainer_payload(
        tmp_path,
        workflow_profile="scalars",
    )
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 1
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 2
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0


def test_explainer_top_level_list_child_count(tmp_path: Path) -> None:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "lists.yaml").write_text(
        "version: 1\n"
        "universal_critique:\n"
        "  tags:\n"
        "    - alpha\n"
        "    - beta\n"
        "  implementation:\n"
        "    enabled: false\n",
        encoding="utf-8",
    )
    out = universal_critique_workflow_explainer_payload(
        tmp_path,
        workflow_profile="lists",
    )
    assert out["universal_critique_yaml_top_level_list_child_count"] == 1
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 1


def test_explainer_top_level_nonempty_count_skips_empty_planner(tmp_path: Path) -> None:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "sparse.yaml").write_text(
        "version: 1\n"
        "universal_critique:\n"
        "  implementation:\n"
        "    llm: false\n"
        "  planner: {}\n"
        "  test_writer:\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    out = universal_critique_workflow_explainer_payload(
        tmp_path,
        workflow_profile="sparse",
    )
    assert out["universal_critique_yaml_top_level_keys"] == [
        "implementation",
        "planner",
        "test_writer",
    ]
    assert out["universal_critique_yaml_top_level_nonempty_count"] == 2
    assert out["universal_critique_yaml_top_level_enabled_true_count"] == 1
    assert out["universal_critique_yaml_top_level_enabled_false_count"] == 0
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 3
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 0
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0


def test_universal_critique_workflow_yaml_relpath_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_workflow_yaml_relpath_caption(out)
    assert cap is not None
    assert "stub.yaml" in cap
    assert universal_critique_workflow_yaml_relpath_caption(None) is None
    assert universal_critique_workflow_yaml_relpath_caption(
        {"load_error": "bad"},
    ) is None
    assert universal_critique_workflow_yaml_relpath_caption({}) is None


def test_universal_critique_yaml_top_level_nonempty_count_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_yaml_top_level_nonempty_count_caption(out)
    assert cap is not None
    raw = out.get("universal_critique_yaml_top_level_nonempty_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert universal_critique_yaml_top_level_nonempty_count_caption(None) is None
    assert universal_critique_yaml_top_level_nonempty_count_caption(
        {"load_error": "bad"},
    ) is None
    assert universal_critique_yaml_top_level_nonempty_count_caption(
        {"universal_critique_yaml_present": False},
    ) is None


def test_universal_critique_yaml_top_level_enabled_true_count_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_yaml_top_level_enabled_true_count_caption(out)
    assert cap is not None
    raw = out.get("universal_critique_yaml_top_level_enabled_true_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert universal_critique_yaml_top_level_enabled_true_count_caption(None) is None


def test_universal_critique_yaml_top_level_enabled_false_count_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_yaml_top_level_enabled_false_count_caption(out)
    assert cap is not None
    raw = out.get("universal_critique_yaml_top_level_enabled_false_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert universal_critique_yaml_top_level_enabled_false_count_caption(None) is None
    assert universal_critique_yaml_top_level_enabled_false_count_caption(
        {"universal_critique_yaml_present": False},
    ) is None


def test_universal_critique_yaml_top_level_mapping_child_count_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_yaml_top_level_mapping_child_count_caption(out)
    assert cap is not None
    raw = out.get("universal_critique_yaml_top_level_mapping_child_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert universal_critique_yaml_top_level_mapping_child_count_caption(None) is None
    assert universal_critique_yaml_top_level_mapping_child_count_caption(
        {"load_error": "bad"},
    ) is None


def test_universal_critique_yaml_top_level_list_child_count_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_yaml_top_level_list_child_count_caption(out)
    assert cap is not None
    raw = out.get("universal_critique_yaml_top_level_list_child_count")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert universal_critique_yaml_top_level_list_child_count_caption(None) is None


def test_universal_critique_workflow_yaml_bytes_caption(
    repo_uc_stub: Path,
) -> None:
    out = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    cap = universal_critique_workflow_yaml_bytes_caption(out)
    assert cap is not None
    assert "bytes" in cap
    raw = out.get("universal_critique_workflow_yaml_bytes")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert universal_critique_workflow_yaml_bytes_caption(None) is None
    assert universal_critique_workflow_yaml_bytes_caption(
        {"load_error": "bad"},
    ) is None
    assert universal_critique_workflow_yaml_bytes_caption({}) is None
    assert universal_critique_workflow_yaml_bytes_caption(
        {"universal_critique_workflow_yaml_bytes": -1},
    ) is None
    assert universal_critique_workflow_yaml_bytes_caption(
        {"universal_critique_workflow_yaml_bytes": True},
    ) is None


def test_universal_critique_yaml_present_caption() -> None:
    cap_absent = universal_critique_yaml_present_caption(
        {"universal_critique_yaml_present": False},
    )
    assert cap_absent is not None
    assert "absent" in cap_absent
    cap_present = universal_critique_yaml_present_caption(
        {
            "universal_critique_yaml_present": True,
            "universal_critique_yaml_top_level_keys": ["a", "b"],
        },
    )
    assert cap_present is not None
    assert "present" in cap_present
    assert "**2**" in cap_present
    assert universal_critique_yaml_present_caption(None) is None
    assert universal_critique_yaml_present_caption(
        {"load_error": "bad"},
    ) is None


def test_universal_critique_default_enabled_caption() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    payload = universal_critique_workflow_explainer_payload(
        root,
        workflow_profile="universal_critique_on",
    )
    cap = universal_critique_default_enabled_caption(payload)
    assert cap is not None
    assert "default_enabled" in cap
    assert "**on**" in cap
    off_payload = universal_critique_workflow_explainer_payload(
        root,
        workflow_profile="default",
    )
    off_cap = universal_critique_default_enabled_caption(off_payload)
    assert off_cap is not None
    assert "**off**" in off_cap


def test_universal_critique_yaml_enabled_bucket_caption() -> None:
    cap = universal_critique_yaml_enabled_bucket_caption(
        {
            "universal_critique_yaml_present": True,
            "universal_critique_yaml_top_level_enabled_true_count": 2,
            "universal_critique_yaml_top_level_enabled_false_count": 1,
            "universal_critique_yaml_top_level_enabled_unset_mapping_count": 0,
        },
    )
    assert cap is not None
    assert "**2** true" in cap
    assert "**1** false" in cap
    assert universal_critique_yaml_enabled_bucket_caption(None) is None
    assert universal_critique_yaml_enabled_bucket_caption(
        {"universal_critique_yaml_present": False},
    ) is None
    assert universal_critique_yaml_enabled_bucket_caption(
        {
            "universal_critique_yaml_present": True,
            "load_error": "bad yaml",
        },
    ) is None


def test_universal_critique_yaml_stage_keys_caption() -> None:
    cap = universal_critique_yaml_stage_keys_caption(
        {
            "universal_critique_yaml_present": True,
            "universal_critique_yaml_top_level_keys": [
                "test_writer",
                "implementation",
                "planner",
            ],
        },
    )
    assert cap is not None
    assert "implementation" in cap
    assert "planner" in cap
    keys = [f"stage_{i}" for i in range(8)]
    cap_trunc = universal_critique_yaml_stage_keys_caption(
        {
            "universal_critique_yaml_present": True,
            "universal_critique_yaml_top_level_keys": keys,
        },
    )
    assert cap_trunc is not None
    assert "+2 more" in cap_trunc
    assert universal_critique_yaml_stage_keys_caption(None) is None
    assert universal_critique_yaml_stage_keys_caption(
        {"universal_critique_yaml_present": False},
    ) is None
    assert universal_critique_yaml_stage_keys_caption(
        {
            "universal_critique_yaml_present": True,
            "load_error": "bad yaml",
        },
    ) is None


def test_universal_critique_enabled_stages_caption() -> None:
    cap = universal_critique_enabled_stages_caption(
        {
            "universal_critique_yaml_present": True,
            "universal_critique_yaml_top_level_enabled_true_count": 2,
            "universal_critique_yaml_top_level_enabled_false_count": 1,
            "universal_critique_yaml_top_level_enabled_unset_mapping_count": 0,
            "universal_critique_yaml_top_level_keys": ["implementation", "planner", "test_writer"],
        },
    )
    assert cap is not None
    assert "enabled: true" in cap
    assert "enabled: false" in cap
    assert universal_critique_enabled_stages_caption(None) is None
    assert universal_critique_enabled_stages_caption(
        {"universal_critique_yaml_present": False},
    ) is None


def test_explainer_enabled_true_counts_two_subtrees(tmp_path: Path) -> None:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "two_en.yaml").write_text(
        "version: 1\n"
        "universal_critique:\n"
        "  implementation:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "  test_writer:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n",
        encoding="utf-8",
    )
    out = universal_critique_workflow_explainer_payload(
        tmp_path,
        workflow_profile="two_en",
    )
    assert out["universal_critique_yaml_top_level_enabled_true_count"] == 2
    assert out["universal_critique_yaml_top_level_enabled_false_count"] == 0
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 2
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 0
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0


def test_env_override_deltas_empty_on_bad_payload() -> None:
    assert universal_critique_env_override_deltas({}) == []


def test_missing_profile_returns_defaults(tmp_path: Path) -> None:
    out = universal_critique_workflow_explainer_payload(tmp_path, workflow_profile="nope")
    assert out["load_error"] is not None
    assert out["universal_critique_yaml_present"] is False
    assert out["universal_critique_yaml_top_level_keys"] == []
    assert out["universal_critique_workflow_yaml_bytes"] is None
    assert out["universal_critique_yaml_top_level_enabled_true_count"] == 0
    assert out["universal_critique_yaml_top_level_enabled_false_count"] == 0
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 0
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 0
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0
    assert out["yaml_only"]["impl_llm"] is False
    assert out["effective_with_env"]["impl_llm"] is False


def test_empty_workflow_profile(tmp_path: Path) -> None:
    out = universal_critique_workflow_explainer_payload(tmp_path, workflow_profile=None)
    assert out["workflow_profile"] is None
    assert out["workflow_yaml_relpath"] is None
    assert out["universal_critique_yaml_present"] is False
    assert out["universal_critique_yaml_top_level_keys"] == []
    assert out["universal_critique_workflow_yaml_bytes"] is None
    assert out["universal_critique_yaml_top_level_enabled_true_count"] == 0
    assert out["universal_critique_yaml_top_level_enabled_false_count"] == 0
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 0
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 0
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0


def test_explainer_yaml_top_level_keys_empty_when_block_absent(tmp_path: Path) -> None:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "bare.yaml").write_text(
        "version: 1\n",
        encoding="utf-8",
    )
    out = universal_critique_workflow_explainer_payload(tmp_path, workflow_profile="bare")
    assert out["universal_critique_yaml_present"] is False
    assert out["universal_critique_yaml_top_level_keys"] == []
    assert isinstance(out["universal_critique_workflow_yaml_bytes"], int)
    assert out["universal_critique_workflow_yaml_bytes"] > 0
    assert out["universal_critique_yaml_top_level_enabled_true_count"] == 0
    assert out["universal_critique_yaml_top_level_enabled_false_count"] == 0
    assert out["universal_critique_yaml_top_level_mapping_child_count"] == 0
    assert out["universal_critique_yaml_top_level_scalar_leaf_count"] == 0
    assert out["universal_critique_yaml_top_level_list_child_count"] == 0


def test_universal_critique_env_override_summary_caption() -> None:
    no_delta = universal_critique_env_override_summary_caption(
        {
            "yaml_only": {"tw_enabled": True},
            "effective_with_env": {"tw_enabled": True},
        },
    )
    assert no_delta is not None
    assert "no env overrides" in no_delta
    with_delta = universal_critique_env_override_summary_caption(
        {
            "yaml_only": {"tw_enabled": True, "pll_enabled": False},
            "effective_with_env": {"tw_enabled": False, "pll_enabled": False},
        },
    )
    assert with_delta is not None
    assert "**1**" in with_delta
    assert universal_critique_env_override_summary_caption(None) is None


def test_workflow_vs_timeline_rows_no_timeline() -> None:
    rows = universal_critique_workflow_vs_timeline_rows(
        {"universal_critique_yaml_top_level_enabled_true_count": 1},
        None,
    )
    assert rows[0]["timeline_universal_critique"] == "—"
    assert rows[1]["timeline_universal_critique"] == "—"
    assert rows[2]["timeline_universal_critique"] == "—"


def test_workflow_vs_timeline_rows_stage_count_match() -> None:
    exp = {"universal_critique_yaml_top_level_enabled_true_count": 2}
    tl = {"stage_count": 2, "fail_count": 0}
    rows = universal_critique_workflow_vs_timeline_rows(exp, tl)
    assert rows[0]["workflow_explainer"] == "2"
    assert rows[0]["timeline_universal_critique"] == "2"
    assert rows[1]["timeline_universal_critique"] == "0"
    assert "stage_count matches" in rows[2]["timeline_universal_critique"]


def test_workflow_vs_timeline_rows_stage_count_mismatch() -> None:
    rows = universal_critique_workflow_vs_timeline_rows(
        {"universal_critique_yaml_top_level_enabled_true_count": 1},
        {"stage_count": 3, "fail_count": 1},
    )
    assert "mismatch" in rows[2]["timeline_universal_critique"]
    assert rows[1]["timeline_universal_critique"] == "1"


def test_workflow_vs_timeline_rows_with_full_timeline_paste_resolution() -> None:
    wall = {
        "run_id": "00000000-0000-4000-8000-000000000002",
        "events": [],
        "universal_critique": {"stage_count": 1, "fail_count": 0, "stages": []},
    }
    tl = universal_critique_snapshot_from_compare_paste(wall)
    rows = universal_critique_workflow_vs_timeline_rows(
        {"universal_critique_yaml_top_level_enabled_true_count": 1},
        tl,
    )
    assert rows[0]["timeline_universal_critique"] == "1"
    assert "stage_count matches" in rows[2]["timeline_universal_critique"]


def test_universal_critique_explainer_table_rows_export_json_and_csv(
    repo_uc_stub: Path,
) -> None:
    payload = universal_critique_workflow_explainer_payload(
        repo_uc_stub,
        workflow_profile="stub",
    )
    rows = universal_critique_explainer_table_rows(payload)
    fields = {r["field"] for r in rows}
    assert "workflow_profile" in fields
    assert "universal_critique_yaml_present" in fields
    assert "yaml_only" in fields
    assert "effective_with_env" in fields
    yaml_row = next(r for r in rows if r["field"] == "yaml_only")
    assert "impl_stub" in yaml_row["value"]
    assert len(rows) == len(payload)
    parsed = json.loads(universal_critique_explainer_export_json(payload))
    assert parsed["workflow_profile"] == "stub"
    csv_text = universal_critique_explainer_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert universal_critique_explainer_table_rows({}) == []  # type: ignore[arg-type]
    assert universal_critique_explainer_table_rows_csv([]) == ""
    assert universal_critique_export_filename_slug() == "universal_critique"


def test_universal_critique_explainer_table_rows_minimal_fixture() -> None:
    payload = {
        "workflow_profile": "wf",
        "yaml_only": {"impl_stub": True},
        "effective_with_env": {"impl_stub": False},
    }
    rows = universal_critique_explainer_table_rows(payload)
    assert len(rows) == 3
    assert json.loads(universal_critique_explainer_export_json(payload)) == payload


def test_universal_critique_workflow_explainer_operator_metrics() -> None:
    payload = {
        "universal_critique_yaml_present": True,
        "universal_critique_yaml_top_level_keys": ["a", "b"],
        "universal_critique_yaml_top_level_enabled_true_count": 1,
        "universal_critique_yaml_top_level_enabled_false_count": 0,
        "universal_critique_yaml_top_level_enabled_unset_mapping_count": 1,
        "universal_critique_yaml_top_level_mapping_child_count": 2,
        "universal_critique_yaml_top_level_scalar_leaf_count": 1,
        "yaml_only": {"default_enabled": True},
    }
    m = universal_critique_workflow_explainer_operator_metrics(payload)
    assert m["yaml_present"] is True
    assert m["top_level_key_count"] == 2
    assert m["enabled_true_count"] == 1
    assert m["scalar_leaf_count"] == 1
    assert m["default_enabled_on"] is True
    cap = universal_critique_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "2" in cap
    assert "default_enabled" in cap


def test_universal_critique_workflow_explainer_operator_metrics_list_child_count() -> None:
    payload = {
        "universal_critique_yaml_present": True,
        "universal_critique_yaml_top_level_list_child_count": 2,
    }
    m = universal_critique_workflow_explainer_operator_metrics(payload)
    assert m["list_child_count"] == 2
    cap = universal_critique_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "list child" in cap


def test_universal_critique_workflow_explainer_operator_metrics_effective_panels() -> None:
    payload = {
        "universal_critique_yaml_present": True,
        "universal_critique_yaml_top_level_keys": ["fw", "mi"],
        "effective_with_env": {
            "unanimous_gate_enforce": True,
            "fw_enabled": True,
            "mi_enabled": False,
        },
    }
    m = universal_critique_workflow_explainer_operator_metrics(payload)
    assert m["unanimous_gate_enforce"] is True
    assert m["fw_enabled"] is True
    assert m["mi_enabled"] is False
    cap = universal_critique_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "unanimous" in cap
    assert "fw panel" in cap


def test_universal_critique_workflow_explainer_operator_metrics_export() -> None:
    m = universal_critique_workflow_explainer_operator_metrics({})
    assert universal_critique_workflow_explainer_operator_metrics_caption(m) is None
    parsed = json.loads(
        universal_critique_workflow_explainer_operator_metrics_export_json(m),
    )
    assert parsed["yaml_present"] is False
    rows = universal_critique_workflow_explainer_operator_metrics_table_rows(m)
    assert rows[0]["field"] == "YAML present"
    assert (
        universal_critique_workflow_explainer_operator_metrics_export_filename_slug()
        == "universal_critique_workflow_explainer_operator_metrics"
    )
