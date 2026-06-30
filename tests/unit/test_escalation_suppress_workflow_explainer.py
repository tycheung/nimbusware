from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import pytest
from nimbusware_console.workflow_explainers.escalation_suppress import escalation_policy_export_filename_slug, escalation_policy_yaml_age_caption, escalation_policy_yaml_anti_deadlock_min_progress_caption, escalation_policy_yaml_anti_deadlock_shape_caption, escalation_policy_yaml_deadlock_minutes_caption, escalation_policy_yaml_file_bytes_caption, escalation_policy_yaml_key_count_caption, escalation_policy_yaml_keys_all_export_json, escalation_policy_yaml_keys_all_table_rows, escalation_policy_yaml_keys_all_table_rows_csv, escalation_policy_yaml_keys_sample_caption, escalation_policy_yaml_max_retries_caption, escalation_policy_yaml_mtime_caption, escalation_policy_yaml_relpath_caption, escalation_policy_yaml_top_level_kinds_caption, escalation_policy_yaml_top_level_kinds_export_json, escalation_policy_yaml_top_level_kinds_table_rows, escalation_policy_yaml_top_level_kinds_table_rows_csv, escalation_policy_yaml_verification_shape_caption, escalation_policy_yaml_version_caption, escalation_suppress_explainer_export_json, escalation_suppress_explainer_table_rows, escalation_suppress_explainer_table_rows_csv, escalation_suppress_export_filename_slug, escalation_suppress_flag_caption, escalation_suppress_workflow_explainer_operator_metrics, escalation_suppress_workflow_explainer_operator_metrics_caption, escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug, escalation_suppress_workflow_explainer_operator_metrics_table_rows, escalation_suppress_workflow_explainer_payload, escalation_yaml_key_present_caption
from nimbusware_env import find_repo_root
from unit.composite_repo_fixtures import write_workflow_profile
from unit.workflow_explainer_helpers import escalation_explainer_payload
pytestmark = pytest.mark.slow

def test_explainer_no_escalation_key(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'bare', 'version: 1\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='bare')
    assert pl['escalation_yaml_key_present'] is False
    assert pl['escalation_yaml_value'] is None
    assert pl['suppress_automatic_escalation_yaml_raw'] is None
    assert pl['suppress_automatic_escalation_effective'] is False
    assert pl['load_error'] is None
    assert pl['suppress_automatic_escalation_yaml_raw_type'] is None
    assert pl['workflow_yaml_top_level_version_int'] == 1
    write_workflow_profile(tmp_path, 'sup_on', 'version: 1\nescalation:\n  suppress_automatic_escalation: true\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='sup_on')
    assert pl['escalation_yaml_key_present'] is True
    assert pl['suppress_automatic_escalation_effective'] is True
    assert pl['suppress_automatic_escalation_yaml_raw'] is True
    assert pl['suppress_automatic_escalation_yaml_raw_type'] == 'bool'
    assert pl['workflow_yaml_top_level_version_int'] == 1

def test_explainer_suppress_false(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'sup_off', 'version: 1\nescalation:\n  suppress_automatic_escalation: false\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='sup_off')
    assert pl['suppress_automatic_escalation_effective'] is False
    assert pl['suppress_automatic_escalation_yaml_raw'] is False
    assert pl['suppress_automatic_escalation_yaml_raw_type'] == 'bool'
    assert pl['workflow_yaml_top_level_version_int'] == 1

def test_explainer_string_yes_truthy(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'yes_str', 'version: 1\nescalation:\n  suppress_automatic_escalation: "yes"\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='yes_str')
    assert pl['suppress_automatic_escalation_effective'] is True
    assert pl['suppress_automatic_escalation_yaml_raw_type'] == 'str'
    assert pl['workflow_yaml_top_level_version_int'] == 1

def test_explainer_malformed_escalation_scalar_collapses(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'bad_esc', 'version: 1\nescalation: true\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='bad_esc')
    assert pl['escalation_yaml_key_present'] is True
    assert pl['escalation_yaml_value'] is True
    assert pl['suppress_automatic_escalation_yaml_raw'] is None
    assert pl['suppress_automatic_escalation_effective'] is False
    assert pl['suppress_automatic_escalation_yaml_raw_type'] is None
    assert pl['workflow_yaml_top_level_version_int'] == 1

def test_explainer_workflow_yaml_top_level_version_missing(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'no_ver', 'escalation:\n  suppress_automatic_escalation: false\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='no_ver')
    assert pl['workflow_yaml_top_level_version_int'] is None
    assert pl['escalation_yaml_key_present'] is True

def test_explainer_workflow_yaml_top_level_version_non_int_returns_none(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'v_bad', 'version: "1"\nescalation:\n  suppress_automatic_escalation: false\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='v_bad')
    assert pl['workflow_yaml_top_level_version_int'] is None

def test_explainer_escalation_policy_yaml_absent(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'bare', 'version: 1\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='bare')
    assert pl['escalation_policy_yaml_path_exists'] is False
    assert pl['escalation_policy_yaml_relpath'] is None
    assert pl['escalation_policy_yaml_file_bytes'] is None
    assert pl['escalation_policy_yaml_mtime_iso'] is None
    assert pl['escalation_policy_yaml_top_level_key_count'] == 0
    assert pl['escalation_policy_yaml_top_level_keys_sample'] == []
    assert pl['escalation_policy_yaml_top_level_kinds'] == {'mapping': 0, 'scalar': 0, 'list': 0, 'other': 0}
    assert pl['escalation_policy_yaml_load_error'] is None
    assert pl['escalation_policy_yaml_has_verification_mapping'] is None
    assert pl['escalation_policy_yaml_has_anti_deadlock_mapping'] is None
    assert pl.get('escalation_policy_yaml_anti_deadlock_min_progress_events') is None

def test_explainer_escalation_policy_yaml_peek_when_present(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nfoo: {a: 1}\nbar: 2\n', encoding='utf-8')
    pol_path = pol_dir / 'policy.yaml'
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_path_exists'] is True
    assert pl['escalation_policy_yaml_relpath'] is not None
    assert 'escalation' in pl['escalation_policy_yaml_relpath'].replace('\\', '/')
    assert pl['escalation_policy_yaml_file_bytes'] == pol_path.stat().st_size
    assert pl['escalation_policy_yaml_top_level_key_count'] == 3
    full_keys = pl['escalation_policy_yaml_top_level_keys']
    assert full_keys == ['bar', 'foo', 'version']
    sample = pl['escalation_policy_yaml_top_level_keys_sample']
    assert isinstance(sample, list) and len(sample) <= 12
    assert set(sample) <= {'bar', 'foo', 'version'}
    assert sample == full_keys
    kinds = pl['escalation_policy_yaml_top_level_kinds']
    assert kinds == {'mapping': 1, 'scalar': 2, 'list': 0, 'other': 0}
    assert sum(kinds.values()) == pl['escalation_policy_yaml_top_level_key_count']
    assert pl['escalation_policy_yaml_load_error'] is None
    assert pl['escalation_policy_yaml_has_verification_mapping'] is False
    assert pl['escalation_policy_yaml_has_anti_deadlock_mapping'] is False
    assert pl['escalation_policy_yaml_max_retries_per_stage'] is None
    assert pl['escalation_policy_yaml_deadlock_escalation_after_minutes'] is None
    assert pl['escalation_policy_yaml_version'] == 1
    assert pl['workflow_yaml_top_level_version_int'] == 1
    assert pl['escalation_policy_yaml_anti_deadlock_enabled'] is None
    assert pl['escalation_policy_yaml_anti_deadlock_min_progress_events'] is None

def test_explainer_escalation_policy_yaml_scalar_retry_fields(tmp_path: Path) -> None:
    pl = escalation_explainer_payload(tmp_path, policy_yaml='version: 1\nmax_retries_per_stage: 5\ndeadlock_escalation_after_minutes: 12\n')
    assert pl['escalation_policy_yaml_max_retries_per_stage'] == 5
    assert pl['escalation_policy_yaml_deadlock_escalation_after_minutes'] == 12
    assert pl['escalation_policy_yaml_version'] == 1
    assert pl['escalation_policy_yaml_anti_deadlock_enabled'] is None

@pytest.mark.parametrize(('policy_yaml', 'field', 'expected'), (('version: 1\nmax_retries_per_stage: true\ndeadlock_escalation_after_minutes: "12"\n', 'escalation_policy_yaml_max_retries_per_stage', None), ('version: 1\nmax_retries_per_stage: true\ndeadlock_escalation_after_minutes: "12"\n', 'escalation_policy_yaml_deadlock_escalation_after_minutes', None), ('version: 1\nanti_deadlock:\n  min_progress_events: not_int\n', 'escalation_policy_yaml_anti_deadlock_min_progress_events', None)))
def test_explainer_escalation_policy_yaml_rejects_non_int_scalars(tmp_path: Path, policy_yaml: str, field: str, expected: object) -> None:
    pl = escalation_explainer_payload(tmp_path, policy_yaml=policy_yaml)
    assert pl[field] == expected

def test_explainer_escalation_policy_yaml_anti_deadlock_enabled_false(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 2\nanti_deadlock:\n  enabled: false\n  min_progress_events: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_version'] == 2
    assert pl['escalation_policy_yaml_anti_deadlock_enabled'] is False
    assert pl['escalation_policy_yaml_anti_deadlock_min_progress_events'] == 1

def test_explainer_escalation_policy_yaml_anti_deadlock_min_progress_events_only(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nanti_deadlock:\n  min_progress_events: 9\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_has_anti_deadlock_mapping'] is True
    assert pl['escalation_policy_yaml_anti_deadlock_enabled'] is None
    assert pl['escalation_policy_yaml_anti_deadlock_min_progress_events'] == 9

def test_explainer_escalation_policy_yaml_anti_deadlock_mapping_true(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nanti_deadlock:\n  max_retries: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_has_anti_deadlock_mapping'] is True
    assert pl['escalation_policy_yaml_max_retries_per_stage'] is None
    assert pl['escalation_policy_yaml_deadlock_escalation_after_minutes'] is None
    assert pl['escalation_policy_yaml_anti_deadlock_min_progress_events'] is None

def test_explainer_escalation_policy_yaml_anti_deadlock_scalar_false(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nanti_deadlock: true\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_has_anti_deadlock_mapping'] is False

def test_escalation_policy_yaml_deadlock_minutes_caption() -> None:
    cap = escalation_policy_yaml_deadlock_minutes_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_deadlock_escalation_after_minutes': 12})
    assert cap is not None
    assert '12' in cap
    assert 'minutes' in cap
    cap1 = escalation_policy_yaml_deadlock_minutes_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_deadlock_escalation_after_minutes': 1})
    assert cap1 is not None
    assert 'minute.' in cap1
    assert escalation_policy_yaml_deadlock_minutes_caption(None) is None
    assert escalation_policy_yaml_deadlock_minutes_caption({'load_error': 'bad'}) is None
    assert escalation_policy_yaml_deadlock_minutes_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': 'x', 'escalation_policy_yaml_deadlock_escalation_after_minutes': 1}) is None
    assert escalation_policy_yaml_deadlock_minutes_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_deadlock_escalation_after_minutes': -1}) is None

def test_escalation_policy_yaml_anti_deadlock_min_progress_caption() -> None:
    assert escalation_policy_yaml_anti_deadlock_min_progress_caption(None) is None
    assert escalation_policy_yaml_anti_deadlock_min_progress_caption({'escalation_policy_yaml_path_exists': False}) is None
    cap = escalation_policy_yaml_anti_deadlock_min_progress_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_anti_deadlock_min_progress_events': 9})
    assert cap == 'Escalation policy anti_deadlock.min_progress_events: **9** events.'
    cap_one = escalation_policy_yaml_anti_deadlock_min_progress_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_anti_deadlock_min_progress_events': 1})
    assert cap_one is not None
    assert '1** event.' in cap_one
    assert escalation_policy_yaml_anti_deadlock_min_progress_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_anti_deadlock_min_progress_events': True}) is None

def test_escalation_policy_yaml_anti_deadlock_shape_caption_true() -> None:
    cap = escalation_policy_yaml_anti_deadlock_shape_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_has_anti_deadlock_mapping': True})
    assert cap is not None
    assert 'anti_deadlock' in cap.lower()

def test_escalation_policy_yaml_anti_deadlock_shape_caption_false() -> None:
    cap = escalation_policy_yaml_anti_deadlock_shape_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_has_anti_deadlock_mapping': False})
    assert cap is not None
    assert 'no top-level' in cap.lower()

def test_escalation_policy_yaml_anti_deadlock_shape_caption_none_unknown() -> None:
    assert escalation_policy_yaml_anti_deadlock_shape_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_has_anti_deadlock_mapping': None}) is None

def test_explainer_escalation_policy_yaml_verification_mapping_true(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nverification:\n  auto_escalate_after_cumulative_findings: null\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_has_verification_mapping'] is True

def test_explainer_escalation_policy_yaml_malformed_surfaces_load_error(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text(': not valid yaml :\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_path_exists'] is True
    err = pl['escalation_policy_yaml_load_error']
    assert isinstance(err, str) and err.strip() != ''
    assert pl['escalation_policy_yaml_top_level_key_count'] == 0
    assert pl['escalation_policy_yaml_top_level_keys_sample'] == []
    assert pl['escalation_policy_yaml_top_level_kinds'] == {'mapping': 0, 'scalar': 0, 'list': 0, 'other': 0}
    assert pl['load_error'] is None
    assert pl.get('escalation_policy_yaml_has_verification_mapping') is None
    assert pl.get('escalation_policy_yaml_has_anti_deadlock_mapping') is None

def test_explainer_escalation_policy_yaml_mtime_iso_when_present(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    before = datetime.now(timezone.utc)
    (pol_dir / 'policy.yaml').write_text('version: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    iso = pl['escalation_policy_yaml_mtime_iso']
    assert isinstance(iso, str) and iso.endswith('Z')
    parsed = datetime.fromisoformat(iso[:-1] + '+00:00')
    assert parsed.tzinfo is not None
    after = datetime.now(timezone.utc)
    assert (parsed - before).total_seconds() >= -1
    assert (after - parsed).total_seconds() <= 300

def test_explainer_escalation_policy_yaml_top_level_kinds_mixed_types(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('a: {x: 1}\nb: 1\nc: [1, 2]\nd: null\ne: hello\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    kinds = pl['escalation_policy_yaml_top_level_kinds']
    assert kinds == {'mapping': 1, 'scalar': 3, 'list': 1, 'other': 0}
    assert sum(kinds.values()) == pl['escalation_policy_yaml_top_level_key_count'] == 5

def test_escalation_policy_yaml_top_level_kinds_caption_none_when_policy_absent(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_path_exists'] is False
    assert escalation_policy_yaml_top_level_kinds_caption(pl) is None

def test_escalation_policy_yaml_top_level_kinds_caption_none_when_all_zero() -> None:
    payload = {'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_top_level_kinds': {'mapping': 0, 'scalar': 0, 'list': 0, 'other': 0}}
    assert escalation_policy_yaml_top_level_kinds_caption(payload) is None

def test_escalation_policy_yaml_top_level_kinds_caption_mixed(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('a: {x: 1}\nb: 1\nc: [1, 2]\nd: null\ne: hello\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_top_level_kinds_caption(pl)
    assert cap == 'Policy top-level kinds: 1 mapping(s), 3 scalar(s), 1 list(s), 0 other.'

def test_escalation_policy_yaml_top_level_kinds_caption_mapping_only(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('a: {x: 1}\nb: {y: 2}\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_top_level_kinds_caption(pl)
    assert cap == 'Policy top-level kinds: 2 mapping(s), 0 scalar(s), 0 list(s), 0 other.'

def test_escalation_policy_yaml_top_level_kinds_caption_accepts_bare_kinds_mapping() -> None:
    cap = escalation_policy_yaml_top_level_kinds_caption({'mapping': 2, 'scalar': 1, 'list': 0, 'other': 1})
    assert cap == 'Policy top-level kinds: 2 mapping(s), 1 scalar(s), 0 list(s), 1 other.'

def test_escalation_policy_yaml_top_level_kinds_caption_bare_zero_returns_none() -> None:
    cap = escalation_policy_yaml_top_level_kinds_caption({'mapping': 0, 'scalar': 0, 'list': 0, 'other': 0})
    assert cap is None

def test_escalation_policy_yaml_top_level_kinds_caption_treats_non_int_as_zero() -> None:
    cap = escalation_policy_yaml_top_level_kinds_caption({'mapping': '2', 'scalar': True, 'list': None, 'other': 1.5})
    assert cap is None

def test_escalation_policy_yaml_age_seconds_absent_policy_returns_none(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_path_exists'] is False
    assert pl['escalation_policy_yaml_age_seconds'] is None

def test_escalation_policy_yaml_age_seconds_load_error_returns_none(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text(': : not yaml\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert isinstance(pl['escalation_policy_yaml_load_error'], str)
    assert pl['escalation_policy_yaml_age_seconds'] is None

def test_escalation_policy_yaml_age_seconds_freshly_written_is_small_non_negative(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    age = pl['escalation_policy_yaml_age_seconds']
    assert isinstance(age, int)
    assert age >= 0
    assert age <= 300

def test_escalation_policy_yaml_age_seconds_past_mtime_within_tolerance(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    pol_path = pol_dir / 'policy.yaml'
    pol_path.write_text('version: 1\n', encoding='utf-8')
    now_ts = datetime.now(timezone.utc).timestamp()
    target_age = 3600
    past_ts = now_ts - target_age
    os.utime(pol_path, (past_ts, past_ts))
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    age = pl['escalation_policy_yaml_age_seconds']
    assert isinstance(age, int)
    assert abs(age - target_age) <= 5

def test_escalation_policy_yaml_age_seconds_future_mtime_returns_none(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    pol_path = pol_dir / 'policy.yaml'
    pol_path.write_text('version: 1\n', encoding='utf-8')
    now_ts = datetime.now(timezone.utc).timestamp()
    future_ts = now_ts + 3600
    os.utime(pol_path, (future_ts, future_ts))
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_age_seconds'] is None

def test_escalation_policy_yaml_file_bytes_caption(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_file_bytes_caption(pl)
    assert cap is not None
    raw = pl.get('escalation_policy_yaml_file_bytes')
    assert isinstance(raw, int)
    assert f'**{raw}**' in cap
    assert escalation_policy_yaml_file_bytes_caption(None) is None
    assert escalation_policy_yaml_file_bytes_caption({'escalation_policy_yaml_load_error': 'bad'}) is None
    assert escalation_policy_yaml_file_bytes_caption({'escalation_policy_yaml_path_exists': False}) is None

def test_escalation_policy_yaml_age_caption(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_age_caption(pl)
    assert cap is not None
    raw = pl.get('escalation_policy_yaml_age_seconds')
    assert isinstance(raw, int)
    assert f'**{raw}**' in cap
    assert escalation_policy_yaml_age_caption(None) is None
    assert escalation_policy_yaml_age_caption({'escalation_policy_yaml_load_error': 'bad'}) is None

def test_escalation_policy_yaml_mtime_caption_none_when_policy_absent(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_path_exists'] is False
    assert escalation_policy_yaml_mtime_caption(pl) is None

def test_escalation_policy_yaml_mtime_caption_none_when_mtime_iso_missing() -> None:
    payload = {'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_mtime_iso': None, 'escalation_policy_yaml_age_seconds': 10}
    assert escalation_policy_yaml_mtime_caption(payload) is None

def test_escalation_policy_yaml_mtime_caption_none_when_age_missing_or_bool() -> None:
    base = {'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_mtime_iso': '2026-01-01T00:00:00Z'}
    assert escalation_policy_yaml_mtime_caption({**base, 'escalation_policy_yaml_age_seconds': None}) is None
    assert escalation_policy_yaml_mtime_caption({**base, 'escalation_policy_yaml_age_seconds': True}) is None
    assert escalation_policy_yaml_mtime_caption({**base, 'escalation_policy_yaml_age_seconds': '5'}) is None

def test_escalation_policy_yaml_mtime_caption_freshly_written_caption(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    iso = pl['escalation_policy_yaml_mtime_iso']
    age = pl['escalation_policy_yaml_age_seconds']
    assert isinstance(iso, str) and iso
    assert isinstance(age, int) and age >= 0
    cap = escalation_policy_yaml_mtime_caption(pl)
    assert cap == f'Policy YAML last modified: {iso} ({age} seconds ago).'

def test_escalation_policy_yaml_mtime_caption_past_mtime_within_tolerance(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    pol_path = pol_dir / 'policy.yaml'
    pol_path.write_text('version: 1\n', encoding='utf-8')
    now_ts = datetime.now(timezone.utc).timestamp()
    target_age = 3600
    past_ts = now_ts - target_age
    os.utime(pol_path, (past_ts, past_ts))
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_mtime_caption(pl)
    assert isinstance(cap, str)
    assert cap.startswith('Policy YAML last modified: ')
    age = pl['escalation_policy_yaml_age_seconds']
    assert isinstance(age, int)
    assert abs(age - target_age) <= 5
    assert cap.endswith(f'({age} seconds ago).')

def test_escalation_yaml_key_present_caption() -> None:
    cap_absent = escalation_yaml_key_present_caption({'escalation_yaml_key_present': False})
    assert cap_absent is not None
    assert 'absent' in cap_absent
    cap_on = escalation_yaml_key_present_caption({'escalation_yaml_key_present': True, 'suppress_automatic_escalation_effective': True})
    assert cap_on is not None
    assert 'true' in cap_on
    cap_off = escalation_yaml_key_present_caption({'escalation_yaml_key_present': True, 'suppress_automatic_escalation_effective': False})
    assert cap_off is not None
    assert 'false' in cap_off
    assert escalation_yaml_key_present_caption(None) is None
    assert escalation_yaml_key_present_caption({'load_error': 'bad'}) is None

def test_escalation_suppress_flag_caption_none_when_effective_missing() -> None:
    payload = {'load_error': None, 'suppress_automatic_escalation_yaml_raw_type': 'bool'}
    assert escalation_suppress_flag_caption(payload) is None

def test_escalation_suppress_flag_caption_none_when_effective_non_bool() -> None:
    base = {'load_error': None, 'suppress_automatic_escalation_yaml_raw_type': 'bool'}
    assert escalation_suppress_flag_caption({**base, 'suppress_automatic_escalation_effective': 1}) is None
    assert escalation_suppress_flag_caption({**base, 'suppress_automatic_escalation_effective': 'true'}) is None
    assert escalation_suppress_flag_caption({**base, 'suppress_automatic_escalation_effective': None}) is None

def test_escalation_suppress_flag_caption_composite_true_bool() -> None:
    payload = {'load_error': None, 'suppress_automatic_escalation_effective': True, 'suppress_automatic_escalation_yaml_raw_type': 'bool'}
    assert escalation_suppress_flag_caption(payload) == 'Suppress automatic escalation: True (YAML raw type: bool).'

def test_escalation_suppress_flag_caption_composite_false_nonetype() -> None:
    payload = {'load_error': None, 'suppress_automatic_escalation_effective': False, 'suppress_automatic_escalation_yaml_raw_type': 'NoneType'}
    assert escalation_suppress_flag_caption(payload) == 'Suppress automatic escalation: False (YAML raw type: NoneType).'

def test_escalation_suppress_flag_caption_bare_when_raw_type_none() -> None:
    payload = {'load_error': None, 'suppress_automatic_escalation_effective': True, 'suppress_automatic_escalation_yaml_raw_type': None}
    assert escalation_suppress_flag_caption(payload) == 'Suppress automatic escalation: True.'

def test_escalation_suppress_flag_caption_bare_when_raw_type_empty_string() -> None:
    payload = {'load_error': None, 'suppress_automatic_escalation_effective': True, 'suppress_automatic_escalation_yaml_raw_type': '   '}
    assert escalation_suppress_flag_caption(payload) == 'Suppress automatic escalation: True.'

def test_escalation_suppress_flag_caption_freshly_written_workflow_prefix(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_suppress_flag_caption(pl)
    assert isinstance(cap, str)
    assert cap.startswith('Suppress automatic escalation: False')

def test_escalation_policy_yaml_verification_shape_caption_true() -> None:
    cap = escalation_policy_yaml_verification_shape_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_has_verification_mapping': True})
    assert cap is not None
    assert 'verification' in cap.lower()

def test_escalation_policy_yaml_verification_shape_caption_false() -> None:
    cap = escalation_policy_yaml_verification_shape_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_has_verification_mapping': False})
    assert cap is not None
    assert 'no top-level' in cap.lower()

def test_escalation_policy_yaml_verification_shape_caption_none_unknown() -> None:
    assert escalation_policy_yaml_verification_shape_caption({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_has_verification_mapping': None}) is None

def test_escalation_policy_yaml_key_count_caption_none_when_file_absent() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': False, 'escalation_policy_yaml_top_level_key_count': 3}
    assert escalation_policy_yaml_key_count_caption(payload) is None

def test_escalation_policy_yaml_key_count_caption_none_when_count_missing() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True}
    assert escalation_policy_yaml_key_count_caption(payload) is None

def test_escalation_policy_yaml_key_count_caption_none_when_count_non_int() -> None:
    base = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True}
    assert escalation_policy_yaml_key_count_caption({**base, 'escalation_policy_yaml_top_level_key_count': '3'}) is None
    assert escalation_policy_yaml_key_count_caption({**base, 'escalation_policy_yaml_top_level_key_count': None}) is None

def test_escalation_policy_yaml_key_count_caption_none_when_count_bool() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_key_count': True}
    assert escalation_policy_yaml_key_count_caption(payload) is None

def test_escalation_policy_yaml_key_count_caption_none_when_count_negative() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_key_count': -1}
    assert escalation_policy_yaml_key_count_caption(payload) is None

def test_escalation_policy_yaml_key_count_caption_emits_for_zero_when_file_present() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_key_count': 0}
    assert escalation_policy_yaml_key_count_caption(payload) == 'Policy YAML top-level keys: 0.'

def test_escalation_policy_yaml_key_count_caption_emits_for_positive_count() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_key_count': 4}
    assert escalation_policy_yaml_key_count_caption(payload) == 'Policy YAML top-level keys: 4.'

def test_escalation_policy_yaml_key_count_caption_freshly_written_two_key_policy(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nthresholds:\n  warning: 3\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_key_count_caption(pl)
    assert cap == 'Policy YAML top-level keys: 2.'
    assert pl['escalation_policy_yaml_top_level_key_count'] == 2

def test_escalation_policy_yaml_version_caption_none_when_file_absent() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': False, 'escalation_policy_yaml_version': 2}
    assert escalation_policy_yaml_version_caption(payload) is None

def test_escalation_policy_yaml_version_caption_none_when_version_missing() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True}
    assert escalation_policy_yaml_version_caption(payload) is None

def test_escalation_policy_yaml_version_caption_emits_for_positive_version() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_version': 3}
    assert escalation_policy_yaml_version_caption(payload) == 'Escalation policy YAML version: **3**.'

def test_escalation_policy_yaml_version_caption_none_when_version_bool() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_version': True}
    assert escalation_policy_yaml_version_caption(payload) is None

def test_escalation_policy_yaml_max_retries_caption_emits_for_non_negative() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_max_retries_per_stage': 5}
    assert escalation_policy_yaml_max_retries_caption(payload) == 'Escalation policy max retries per stage: **5**.'
    zero = {**payload, 'escalation_policy_yaml_max_retries_per_stage': 0}
    assert escalation_policy_yaml_max_retries_caption(zero) == 'Escalation policy max retries per stage: **0**.'

def test_escalation_policy_yaml_keys_sample_caption_none_when_file_absent() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': False, 'escalation_policy_yaml_top_level_keys_sample': ['a', 'b']}
    assert escalation_policy_yaml_keys_sample_caption(payload) is None

def test_escalation_policy_yaml_keys_sample_caption_none_when_sample_missing() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True}
    assert escalation_policy_yaml_keys_sample_caption(payload) is None

def test_escalation_policy_yaml_keys_sample_caption_none_when_sample_not_list() -> None:
    base = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True}
    assert escalation_policy_yaml_keys_sample_caption({**base, 'escalation_policy_yaml_top_level_keys_sample': 'a'}) is None
    assert escalation_policy_yaml_keys_sample_caption({**base, 'escalation_policy_yaml_top_level_keys_sample': None}) is None

def test_escalation_policy_yaml_keys_sample_caption_none_when_sample_empty() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_keys_sample': []}
    assert escalation_policy_yaml_keys_sample_caption(payload) is None

def test_escalation_policy_yaml_keys_sample_caption_none_when_all_unusable() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_keys_sample': ['   ', '', 1, None, False]}
    assert escalation_policy_yaml_keys_sample_caption(payload) is None

def test_escalation_policy_yaml_keys_sample_caption_single_entry() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_keys_sample': ['  foo  ']}
    assert escalation_policy_yaml_keys_sample_caption(payload) == 'Policy YAML top-level keys (sample): foo.'

def test_escalation_policy_yaml_keys_sample_caption_three_entries_order_preserved() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_keys_sample': ['z', 'a', 'm']}
    assert escalation_policy_yaml_keys_sample_caption(payload) == 'Policy YAML top-level keys (sample): z, a, m.'

def test_escalation_policy_yaml_keys_sample_caption_mixed_skips_non_strings() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_keys_sample': ['ok', 99, None, '  bar  ']}
    assert escalation_policy_yaml_keys_sample_caption(payload) == 'Policy YAML top-level keys (sample): ok, bar.'

def test_escalation_policy_yaml_keys_sample_caption_fresh_three_key_policy_sorted(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('zeta: 1\nalpha: 2\nbeta: 3\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_keys_sample_caption(pl)
    assert cap == 'Policy YAML top-level keys (sample): alpha, beta, zeta.'
    assert pl['escalation_policy_yaml_top_level_key_count'] == 3

def test_escalation_policy_yaml_relpath_caption_none_when_file_absent() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': False, 'escalation_policy_yaml_relpath': 'configs/escalation/policy.yaml'}
    assert escalation_policy_yaml_relpath_caption(payload) is None

def test_escalation_policy_yaml_relpath_caption_none_when_relpath_blank() -> None:
    payload = {'escalation_policy_yaml_load_error': None, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_relpath': '   '}
    assert escalation_policy_yaml_relpath_caption(payload) is None

def test_escalation_policy_yaml_relpath_caption_fresh_policy(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / 'policy.yaml').write_text('a: 1\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    cap = escalation_policy_yaml_relpath_caption(pl)
    assert cap is not None
    assert cap.startswith('Policy YAML path:')
    assert 'escalation' in cap.replace('\\', '/').lower()

def test_escalation_policy_yaml_keys_all_table_rows_thirteen_keys(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True)
    yaml_body = ''
    for i in range(13):
        yaml_body += f'key_{i}: {i}\n'
    (pol_dir / 'policy.yaml').write_text(yaml_body, encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    assert pl['escalation_policy_yaml_top_level_key_count'] == 13
    full = pl['escalation_policy_yaml_top_level_keys']
    sample = pl['escalation_policy_yaml_top_level_keys_sample']
    assert len(full) == 13
    assert len(sample) == 12
    all_rows = escalation_policy_yaml_keys_all_table_rows(pl)
    sample_rows = escalation_policy_yaml_keys_all_table_rows({'escalation_policy_yaml_top_level_keys_sample': sample})
    assert len(all_rows) == 13
    assert len(sample_rows) == 12
    assert {r['policy_key'] for r in all_rows} == set(full)
    parsed = json.loads(escalation_policy_yaml_keys_all_export_json(all_rows))
    assert len(parsed) == 13
    csv_text = escalation_policy_yaml_keys_all_table_rows_csv(all_rows)
    assert csv_text.splitlines()[0] == 'policy_key'

def test_escalation_policy_yaml_keys_all_table_rows_at_most_twelve(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nfoo: {a: 1}\nbar: 2\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    all_rows = escalation_policy_yaml_keys_all_table_rows(pl)
    sample_only = {'escalation_policy_yaml_top_level_keys_sample': pl['escalation_policy_yaml_top_level_keys_sample']}
    sample_rows = escalation_policy_yaml_keys_all_table_rows(sample_only)
    assert all_rows == sample_rows

def test_escalation_policy_yaml_keys_all_table_rows_real_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    pl = escalation_suppress_workflow_explainer_payload(root, workflow_profile='default')
    if not pl.get('escalation_policy_yaml_path_exists'):
        return
    if pl.get('escalation_policy_yaml_load_error'):
        return
    all_rows = escalation_policy_yaml_keys_all_table_rows(pl)
    count = pl.get('escalation_policy_yaml_top_level_key_count')
    assert isinstance(count, int)
    if count > 0:
        assert len(all_rows) == count

def test_escalation_policy_yaml_top_level_kinds_table_rows_mixed_policy(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, 'wf', 'version: 1\n')
    pol_dir = tmp_path / 'configs' / 'escalation'
    pol_dir.mkdir(parents=True)
    (pol_dir / 'policy.yaml').write_text('version: 1\nfoo: {a: 1}\nbar: 2\n', encoding='utf-8')
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile='wf')
    rows = escalation_policy_yaml_top_level_kinds_table_rows(pl)
    assert len(rows) == 4
    assert sum((int(r['count']) for r in rows)) == pl['escalation_policy_yaml_top_level_key_count']
    assert {r['kind'] for r in rows} == {'mapping', 'scalar', 'list', 'other'}
    parsed = json.loads(escalation_policy_yaml_top_level_kinds_export_json(rows))
    assert len(parsed) == 4
    csv_text = escalation_policy_yaml_top_level_kinds_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == 'kind,count'

def test_escalation_policy_yaml_top_level_kinds_table_rows_empty_cases() -> None:
    assert escalation_policy_yaml_top_level_kinds_table_rows({}) == []
    assert escalation_policy_yaml_top_level_kinds_table_rows_csv([]) == ''
    assert escalation_policy_yaml_top_level_kinds_table_rows({'escalation_policy_yaml_path_exists': False}) == []
    assert escalation_policy_yaml_top_level_kinds_table_rows({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_load_error': 'boom'}) == []
    assert escalation_policy_yaml_top_level_kinds_table_rows({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_kinds': {'mapping': 0, 'scalar': 0, 'list': 0, 'other': 0}}) == []

def test_escalation_policy_yaml_top_level_kinds_table_rows_real_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    pl = escalation_suppress_workflow_explainer_payload(root, workflow_profile='default')
    if not pl.get('escalation_policy_yaml_path_exists'):
        return
    if pl.get('escalation_policy_yaml_load_error'):
        return
    rows = escalation_policy_yaml_top_level_kinds_table_rows(pl)
    kinds = pl.get('escalation_policy_yaml_top_level_kinds')
    if not isinstance(kinds, dict):
        return
    if sum(kinds.values()) == 0:
        assert rows == []
        return
    assert len(rows) == 4
    assert {r['kind']: int(r['count']) for r in rows} == {k: int(v) for (k, v) in kinds.items() if isinstance(v, int)}

def test_escalation_policy_export_filename_slug() -> None:
    assert escalation_policy_export_filename_slug() == 'escalation_policy'

def test_escalation_suppress_workflow_explainer_operator_metrics_policy_file_bytes() -> None:
    m = escalation_suppress_workflow_explainer_operator_metrics({'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_file_bytes': 512})
    assert m['policy_yaml_file_bytes'] == 512
    cap = escalation_suppress_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert '512' in cap

def test_escalation_suppress_workflow_explainer_operator_metrics_anti_deadlock() -> None:
    m = escalation_suppress_workflow_explainer_operator_metrics({'escalation_policy_yaml_has_anti_deadlock_mapping': True, 'escalation_policy_yaml_anti_deadlock_min_progress_events': 9})
    assert m['anti_deadlock_mapping_present'] is True
    assert m['anti_deadlock_min_progress_events'] == 9
    cap = escalation_suppress_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert '9' in cap

def test_escalation_suppress_workflow_explainer_operator_metrics_policy_age() -> None:
    m = escalation_suppress_workflow_explainer_operator_metrics({'escalation_policy_yaml_age_seconds': 42})
    assert m['policy_yaml_age_seconds'] == 42
    cap = escalation_suppress_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert '42s' in cap

def test_escalation_suppress_workflow_explainer_operator_metrics() -> None:
    m = escalation_suppress_workflow_explainer_operator_metrics({'escalation_yaml_key_present': True, 'suppress_automatic_escalation_effective': True, 'escalation_policy_yaml_path_exists': True, 'escalation_policy_yaml_top_level_key_count': 5})
    assert m['escalation_key_present'] is True
    assert m['suppress_automatic_escalation_effective'] is True
    cap = escalation_suppress_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert 'on' in cap
