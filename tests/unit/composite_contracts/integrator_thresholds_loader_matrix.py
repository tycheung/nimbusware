from __future__ import annotations

from typing import Any

YAML_ROOT_MAPPING_PREFIX = "YAML root must be a mapping:"

MIN_SCORE_DEFENSIVE_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "c1_file_absent", "yaml_body": None, "expected": 0.0},
    {"case_id": "c2_key_missing", "yaml_body": "version: 1\nenabled: true\n", "expected": 0.0},
    {
        "case_id": "c3_explicit_null",
        "yaml_body": "version: 1\nmin_score_to_pass: null\n",
        "expected": 0.0,
    },
)

MIN_SCORE_TYPE_ERROR_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "c4_list_value", "yaml_fragment": "min_score_to_pass: [0.5]", "expected": 0.0},
    {
        "case_id": "c4_dict_value",
        "yaml_fragment": "min_score_to_pass: {nested: 0.5}",
        "expected": 0.0,
    },
)

MIN_SCORE_VALUE_ERROR_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "c5_ve_str_abc", "yaml_fragment": 'min_score_to_pass: "abc"', "expected": 0.0},
    {
        "case_id": "c5_ve_str_near_miss",
        "yaml_fragment": 'min_score_to_pass: "0.5x"',
        "expected": 0.0,
    },
    {
        "case_id": "c5_ve_str_double_dot",
        "yaml_fragment": 'min_score_to_pass: "0.5.6"',
        "expected": 0.0,
    },
)

MIN_SCORE_HAPPY_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "c5_happy_float_half", "yaml_fragment": "min_score_to_pass: 0.5", "expected": 0.5},
    {"case_id": "c5_happy_float_zero", "yaml_fragment": "min_score_to_pass: 0", "expected": 0.0},
    {"case_id": "c5_happy_int_one", "yaml_fragment": "min_score_to_pass: 1", "expected": 1.0},
    {
        "case_id": "c5_happy_float_boundary",
        "yaml_fragment": "min_score_to_pass: 1.0",
        "expected": 1.0,
    },
)

CROSS_FUNCTION_D1: dict[str, Any] = {
    "case_id": "d1_shared_path",
    "yaml_body": "version: 1\nenabled: true\nmin_score_to_pass: 0.75\n",
    "expected_emit": True,
    "expected_min_score": 0.75,
}

CROSS_FUNCTION_D2_STAGES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d2_absent",
        "yaml_body": None,
        "expected_emit": False,
        "expected_min_score": 0.0,
    },
    {
        "case_id": "d2_partial",
        "yaml_body": "version: 1\nenabled: true\n",
        "expected_emit": True,
        "expected_min_score": 0.0,
    },
)

NO_CLAMP_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "d3_noclamp_negative_small", "raw": "-0.5", "expected": -0.5},
    {"case_id": "d3_noclamp_over_one_small", "raw": "1.5", "expected": 1.5},
    {"case_id": "d3_noclamp_negative_large", "raw": "-100.0", "expected": -100.0},
    {"case_id": "d3_noclamp_over_one_large", "raw": "100.0", "expected": 100.0},
)

CROSS_FUNCTION_D4: dict[str, Any] = {
    "case_id": "d4_return_types",
    "thresholds_yaml": "version: 1\nenabled: true\n",
    "wf_profile": "d4_no_key",
    "wf_yaml_body": "version: 1\nintegrator_gate:\n  enabled: true\n",
}

CROSS_FUNCTION_D5_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d5_emit",
        "yaml_body": '"just a string"\n',
        "loader": "emit",
        "msg_contains": (YAML_ROOT_MAPPING_PREFIX,),
    },
    {
        "case_id": "d5_min_score",
        "yaml_body": '"just a string"\n',
        "loader": "min_score",
        "msg_contains": (YAML_ROOT_MAPPING_PREFIX,),
    },
)
