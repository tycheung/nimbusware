from __future__ import annotations

from typing import Any

INTEGRATOR_GATE_EMIT_DEFENSIVE_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "file_absent", "yaml_body": None, "expected": False},
    {
        "case_id": "key_missing",
        "yaml_body": "version: 1\nmin_score_to_pass: 0.5\n",
        "expected": False,
    },
    {"case_id": "explicit_null", "yaml_body": "version: 1\nenabled: null\n", "expected": False},
    {"case_id": "explicit_true", "yaml_body": "version: 1\nenabled: true\n", "expected": True},
    {"case_id": "explicit_false", "yaml_body": "version: 1\nenabled: false\n", "expected": False},
)

INTEGRATOR_GATE_EMIT_BOOL_LADDER_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "int_zero", "yaml_body": "version: 1\nenabled: 0\n", "expected": False},
    {"case_id": "int_one", "yaml_body": "version: 1\nenabled: 1\n", "expected": True},
    {"case_id": "int_two", "yaml_body": "version: 1\nenabled: 2\n", "expected": True},
    {"case_id": "int_negative", "yaml_body": "version: 1\nenabled: -1\n", "expected": True},
    {"case_id": "float_zero", "yaml_body": "version: 1\nenabled: 0.0\n", "expected": False},
    {"case_id": "float_half", "yaml_body": "version: 1\nenabled: 0.5\n", "expected": True},
    {"case_id": "float_one", "yaml_body": "version: 1\nenabled: 1.0\n", "expected": True},
    {"case_id": "str_false_literal", "yaml_body": 'version: 1\nenabled: "false"\n', "expected": True},
    {"case_id": "str_no_literal", "yaml_body": 'version: 1\nenabled: "no"\n', "expected": True},
    {"case_id": "str_off_literal", "yaml_body": 'version: 1\nenabled: "off"\n', "expected": True},
    {"case_id": "str_zero_literal", "yaml_body": 'version: 1\nenabled: "0"\n', "expected": True},
    {"case_id": "str_random", "yaml_body": 'version: 1\nenabled: "anything"\n', "expected": True},
    {"case_id": "str_empty", "yaml_body": 'version: 1\nenabled: ""\n', "expected": False},
    {"case_id": "list_empty", "yaml_body": "version: 1\nenabled: []\n", "expected": False},
    {"case_id": "dict_empty", "yaml_body": "version: 1\nenabled: {}\n", "expected": False},
    {"case_id": "list_nonempty", "yaml_body": 'version: 1\nenabled: ["any"]\n', "expected": True},
    {"case_id": "dict_nonempty", "yaml_body": "version: 1\nenabled: {key: val}\n", "expected": True},
)
