from __future__ import annotations
import json
from pathlib import Path
import pytest
from nimbusware_console.self_refinement import self_refinement_snapshot_from_compare_paste
from nimbusware_console.workflow_explainers.self_refinement import self_refinement_explainer_export_json, self_refinement_explainer_table_rows, self_refinement_explainer_table_rows_csv, self_refinement_export_filename_slug, self_refinement_marker_merge_compare_export_filename_slug, self_refinement_marker_merge_compare_export_json, self_refinement_marker_merge_compare_snapshot, self_refinement_marker_merge_compare_table_rows_csv, self_refinement_marker_merge_vs_timeline_rows, self_refinement_merged_description_preview_caption, self_refinement_merged_version_caption, self_refinement_policy_yaml_disk_version_caption, self_refinement_policy_yaml_file_bytes_caption, self_refinement_ungated_loop_env_gate_caption, self_refinement_workflow_explainer_operator_metrics, self_refinement_workflow_explainer_operator_metrics_caption, self_refinement_workflow_explainer_operator_metrics_export_filename_slug, self_refinement_workflow_explainer_operator_metrics_table_rows, self_refinement_workflow_explainer_payload, self_refinement_workflow_yaml_raw_type_caption, self_refinement_would_emit_after_env_caption, self_refinement_would_emit_marker_caption
_POLICY_AND_WORKFLOW_POLICY_TEXT = 'version: 1\nenabled: false\ndescription: "from disk policy"\n'

def test_self_refinement_policy_yaml_file_bytes_caption(repo_sr_policy_and_workflow: Path) -> None:
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    cap = self_refinement_policy_yaml_file_bytes_caption(out)
    assert cap is not None
    assert 'bytes' in cap
    raw = out.get('policy_yaml', {}).get('policy_yaml_file_bytes')
    assert isinstance(raw, int)
    assert f'**{raw}**' in cap
    assert self_refinement_policy_yaml_file_bytes_caption(None) is None
    assert self_refinement_policy_yaml_file_bytes_caption({'load_error': 'x'}) is None

def test_self_refinement_policy_yaml_disk_version_caption(repo_sr_policy_and_workflow: Path) -> None:
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    cap = self_refinement_policy_yaml_disk_version_caption(out)
    assert cap is not None
    assert '**1**' in cap
    assert self_refinement_policy_yaml_disk_version_caption(None) is None
    assert self_refinement_policy_yaml_disk_version_caption({'load_error': 'x'}) is None
    assert self_refinement_policy_yaml_disk_version_caption({'policy_yaml': {}}) is None

def test_self_refinement_workflow_yaml_raw_type_caption(repo_sr_policy_and_workflow: Path) -> None:
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    cap = self_refinement_workflow_yaml_raw_type_caption(out)
    assert cap is not None
    assert '**dict**' in cap
    assert self_refinement_workflow_yaml_raw_type_caption(None) is None
    assert self_refinement_workflow_yaml_raw_type_caption({'load_error': 'x'}) is None

def test_self_refinement_merged_version_caption() -> None:
    cap = self_refinement_merged_version_caption({'merged_version': 3})
    assert cap is not None
    assert '**3**' in cap
    assert self_refinement_merged_version_caption(None) is None
    assert self_refinement_merged_version_caption({}) is None
    assert self_refinement_merged_version_caption({'merged_version': 0}) is None
    assert self_refinement_merged_version_caption({'merged_version': True}) is None

def test_self_refinement_merged_description_preview_caption() -> None:
    cap = self_refinement_merged_description_preview_caption({'merged_description_preview': 'override desc', 'merged_description_len': 13})
    assert cap is not None
    assert 'override desc' in cap
    assert '13 chars' in cap
    long_text = 'x' * 150
    cap_trunc = self_refinement_merged_description_preview_caption({'merged_description_preview': long_text, 'merged_description_len': 150}, max_chars=120)
    assert cap_trunc is not None
    assert '…' in cap_trunc
    assert '150 chars' in cap_trunc
    assert self_refinement_merged_description_preview_caption(None) is None
    assert self_refinement_merged_description_preview_caption({}) is None
    assert self_refinement_merged_description_preview_caption({'merged_description_preview': ''}) is None

def test_self_refinement_would_emit_after_env_caption() -> None:
    cap_on = self_refinement_would_emit_after_env_caption({'would_emit_marker_after_env': True})
    assert cap_on is not None
    assert 'would emit' in cap_on
    cap_off = self_refinement_would_emit_after_env_caption({'would_emit_marker_after_env': False})
    assert cap_off is not None
    assert 'would not emit' in cap_off
    assert self_refinement_would_emit_after_env_caption(None) is None
    assert self_refinement_would_emit_after_env_caption({}) is None

def test_self_refinement_would_emit_marker_caption() -> None:
    cap_on = self_refinement_would_emit_marker_caption({'would_emit_self_refinement_marker': True, 'would_emit_marker_after_env': True})
    assert cap_on is not None
    assert 'would emit' in cap_on
    cap_env_off = self_refinement_would_emit_marker_caption({'would_emit_self_refinement_marker': True, 'would_emit_marker_after_env': False})
    assert cap_env_off is not None
    assert 'kill-switch' in cap_env_off
    cap_off = self_refinement_would_emit_marker_caption({'would_emit_self_refinement_marker': False, 'would_emit_marker_after_env': False})
    assert cap_off is not None
    assert 'would not emit' in cap_off
    assert self_refinement_would_emit_marker_caption(None) is None
    assert self_refinement_would_emit_marker_caption({}) is None

@pytest.fixture()
def repo_sr_workflow_only(tmp_path: Path) -> Path:
    (tmp_path / 'configs' / 'workflows').mkdir(parents=True)
    (tmp_path / 'configs' / 'workflows' / 'wf.yaml').write_text('version: 1\nself_refinement:\n  enabled: true\n  version: 2\n  description: "from workflow"\n', encoding='utf-8')
    return tmp_path

@pytest.fixture()
def repo_sr_policy_and_workflow(tmp_path: Path) -> Path:
    (tmp_path / 'configs' / 'self_refinement').mkdir(parents=True)
    (tmp_path / 'configs' / 'self_refinement' / 'policy.yaml').write_text(_POLICY_AND_WORKFLOW_POLICY_TEXT, encoding='utf-8')
    (tmp_path / 'configs' / 'workflows').mkdir(parents=True)
    (tmp_path / 'configs' / 'workflows' / 'on.yaml').write_text('version: 1\nself_refinement:\n  enabled: true\n  version: 9\n', encoding='utf-8')
    return tmp_path

def test_would_emit_when_workflow_enables_even_if_policy_off(repo_sr_policy_and_workflow: Path) -> None:
    pol_path = repo_sr_policy_and_workflow / 'configs' / 'self_refinement' / 'policy.yaml'
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    assert out['policy_yaml']['enabled'] is False
    assert out['workflow_self_refinement']['enabled'] is True
    assert out['self_refinement_yaml_mapping_string_key_count'] == 2
    assert out['self_refinement_workflow_yaml_raw_type'] == 'dict'
    assert out['policy_yaml']['description_char_len'] == len('from disk policy')
    assert out['policy_yaml']['policy_yaml_file_bytes'] == pol_path.stat().st_size
    assert out['policy_yaml']['policy_yaml_top_level_version_int'] == 1
    assert out['marker_merge']['would_emit_self_refinement_marker'] is True
    assert out['marker_merge']['merged_version'] == 9

def test_workflow_description_overrides_policy(repo_sr_policy_and_workflow: Path) -> None:
    (repo_sr_policy_and_workflow / 'configs' / 'workflows' / 'on.yaml').write_text('version: 1\nself_refinement:\n  enabled: true\n  description: "override desc"\n', encoding='utf-8')
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    assert out['marker_merge']['merged_description_preview'] == 'override desc'
    assert out['self_refinement_yaml_mapping_string_key_count'] == 2

def test_missing_policy_uses_defaults(repo_sr_workflow_only: Path) -> None:
    out = self_refinement_workflow_explainer_payload(repo_sr_workflow_only, workflow_profile='wf')
    assert out['policy_yaml']['exists'] is False
    assert out['policy_yaml']['policy_yaml_file_bytes'] is None
    assert out['policy_yaml']['policy_yaml_top_level_version_int'] is None
    assert out['policy_yaml']['description_char_len'] == 0
    assert out['self_refinement_yaml_mapping_string_key_count'] == 3
    assert out['marker_merge']['would_emit_self_refinement_marker'] is True

def test_missing_workflow_profile(tmp_path: Path) -> None:
    out = self_refinement_workflow_explainer_payload(tmp_path, workflow_profile=None)
    assert out['workflow_profile'] is None
    assert out['self_refinement_yaml_mapping_string_key_count'] is None
    assert out['marker_merge']['would_emit_self_refinement_marker'] is False

def test_unknown_workflow_profile(tmp_path: Path) -> None:
    out = self_refinement_workflow_explainer_payload(tmp_path, workflow_profile='missing')
    assert out['load_error'] is not None
    assert out['self_refinement_yaml_mapping_string_key_count'] is None

def test_env_kill_switch_marks_effective_emit_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / 'configs' / 'self_refinement').mkdir(parents=True)
    pol_text = 'version: 1\nenabled: true\ndescription: pol\n'
    (tmp_path / 'configs' / 'self_refinement' / 'policy.yaml').write_text(pol_text, encoding='utf-8')
    (tmp_path / 'configs' / 'workflows').mkdir(parents=True)
    (tmp_path / 'configs' / 'workflows' / 'w.yaml').write_text('version: 1\nself_refinement:\n  enabled: false\n', encoding='utf-8')
    monkeypatch.setenv('NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER', '0')
    policy_path = tmp_path / 'configs' / 'self_refinement' / 'policy.yaml'
    out = self_refinement_workflow_explainer_payload(tmp_path, workflow_profile='w')
    assert out['policy_yaml']['policy_yaml_file_bytes'] == policy_path.stat().st_size
    assert out['marker_merge']['would_emit_self_refinement_marker'] is True
    assert out['marker_merge']['would_emit_marker_after_env'] is False
    assert out['marker_merge']['NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER']['disables_marker'] is True

def test_marker_merge_vs_timeline_rows_no_timeline() -> None:
    rows = self_refinement_marker_merge_vs_timeline_rows({'would_emit_self_refinement_marker': True, 'would_emit_marker_after_env': True}, None)
    assert rows[0]['timeline_self_refinement'] == '—'
    assert rows[2]['timeline_self_refinement'] == '—'
    assert rows[3]['timeline_self_refinement'] == '—'

def test_marker_merge_vs_timeline_version_match() -> None:
    mm = {'would_emit_self_refinement_marker': True, 'would_emit_marker_after_env': True, 'merged_version': 9, 'merged_description_len': 10}
    tl = {'version': 9, 'description': '1234567890'}
    rows = self_refinement_marker_merge_vs_timeline_rows(mm, tl)
    assert rows[4]['explainer_marker_merge'] == 'match'
    assert rows[6]['explainer_marker_merge'] == '0'

def test_marker_merge_vs_timeline_version_mismatch() -> None:
    rows = self_refinement_marker_merge_vs_timeline_rows({'merged_version': 1, 'merged_description_len': 0}, {'version': 2})
    assert 'mismatch' in rows[4]['explainer_marker_merge']

def test_marker_merge_vs_timeline_empty_object() -> None:
    rows = self_refinement_marker_merge_vs_timeline_rows({'merged_version': 1, 'merged_description_len': 0}, {})
    assert rows[0]['timeline_self_refinement'] == '(empty object)'
    assert 'n/a' in rows[4]['explainer_marker_merge']

def test_marker_merge_vs_timeline_from_explainer_payload(repo_sr_policy_and_workflow: Path) -> None:
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    rows = self_refinement_marker_merge_vs_timeline_rows(out['marker_merge'], {'version': 9, 'description': 'x'})
    assert rows[4]['explainer_marker_merge'] == 'match'

def test_marker_merge_vs_timeline_marker_count_from_timeline() -> None:
    rows = self_refinement_marker_merge_vs_timeline_rows({'merged_version': 1, 'merged_description_len': 0}, {'version': 1, 'marker_count': 3})
    assert rows[2]['metric'].startswith('Session marker_count')
    assert rows[2]['explainer_marker_merge'] == '—'
    assert rows[2]['timeline_self_refinement'] == '3'

def test_marker_merge_vs_timeline_marker_count_absent_in_paste() -> None:
    rows = self_refinement_marker_merge_vs_timeline_rows({'merged_version': 1, 'merged_description_len': 0}, {'version': 1})
    assert rows[2]['timeline_self_refinement'] == '—'

def test_marker_merge_vs_timeline_with_full_timeline_paste_resolution() -> None:
    wall = {'run_id': '00000000-0000-4000-8000-000000000002', 'events': [], 'self_refinement': {'version': 5, 'description': 'hi!'}}
    tl = self_refinement_snapshot_from_compare_paste(wall)
    rows = self_refinement_marker_merge_vs_timeline_rows({'would_emit_self_refinement_marker': True, 'would_emit_marker_after_env': True, 'merged_version': 5, 'merged_description_len': 3}, tl)
    assert rows[4]['explainer_marker_merge'] == 'match'

def test_self_refinement_marker_merge_compare_export_json_and_csv() -> None:
    marker = {'would_emit_self_refinement_marker': True, 'merged_version': 9}
    timeline = {'version': 9, 'marker_count': 2}
    snap = self_refinement_marker_merge_compare_snapshot(marker, timeline)
    parsed = json.loads(self_refinement_marker_merge_compare_export_json(snap))
    assert parsed['marker_merge'] == marker
    assert parsed['timeline_self_refinement'] == timeline
    compare_rows = self_refinement_marker_merge_vs_timeline_rows(marker, timeline)
    csv_text = self_refinement_marker_merge_compare_table_rows_csv(compare_rows)
    assert csv_text.splitlines()[0] == 'metric,explainer_marker_merge,timeline_self_refinement'
    assert self_refinement_marker_merge_compare_table_rows_csv([]) == ''
    assert self_refinement_marker_merge_compare_export_filename_slug() == 'self_refinement_marker_compare'

def test_self_refinement_ungated_loop_env_gate_caption() -> None:
    cap_on = self_refinement_ungated_loop_env_gate_caption({'NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP': {'forces_on': True, 'forces_off': False, 'unset': False, 'raw': '1'}})
    assert cap_on is not None
    assert 'force-on' in cap_on
    cap_unset = self_refinement_ungated_loop_env_gate_caption({'NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP': {'forces_on': False, 'forces_off': False, 'unset': True}})
    assert cap_unset is not None
    assert 'unset' in cap_unset
    assert self_refinement_ungated_loop_env_gate_caption(None) is None

def test_self_refinement_workflow_explainer_payload_includes_ungated_env(repo_sr_policy_and_workflow: Path) -> None:
    out = self_refinement_workflow_explainer_payload(repo_sr_policy_and_workflow, workflow_profile='on')
    env = out.get('NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP')
    assert isinstance(env, dict)
    assert 'unset' in env

def test_self_refinement_workflow_explainer_operator_metrics() -> None:
    payload = {'self_refinement_yaml_present': True, 'self_refinement_yaml_mapping_string_key_count': 3, 'policy_yaml': {'enabled': True, 'version': 2}, 'marker_merge': {'would_emit_self_refinement_marker': True, 'would_emit_marker_after_env': False}}
    m = self_refinement_workflow_explainer_operator_metrics(payload)
    assert m['yaml_present'] is True
    assert m['policy_enabled'] is True
    assert m['would_emit_marker'] is True
    cap = self_refinement_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None

def test_self_refinement_workflow_explainer_operator_metrics_merged_max_iterations() -> None:
    payload = {'merged_max_iterations': 5, 'policy_yaml': {'enabled': True}}
    m = self_refinement_workflow_explainer_operator_metrics(payload)
    assert m['merged_max_iterations'] == 5
    cap = self_refinement_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert '5' in cap

def test_self_refinement_workflow_explainer_operator_metrics_ungated_env() -> None:
    payload = {'NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP': {'forces_on': True, 'forces_off': False, 'unset': False}}
    m = self_refinement_workflow_explainer_operator_metrics(payload)
    assert m['ungated_loop_forces_on'] is True
    cap = self_refinement_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert 'ungated' in cap.lower()
