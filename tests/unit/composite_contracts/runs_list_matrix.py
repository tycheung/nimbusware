from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from unit.composite_contract_fixtures import urlsafe_b64_encode

_SAMPLE_RID = UUID("11111111-1111-4111-8111-111111111111")
_SAMPLE_RID_ALT = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")

_EXPECTED_ERROR_SUFFIX = " must be a valid ISO-8601 datetime"
_UTC = timezone.utc
_SAMPLE_UUID_STR = "11111111-1111-4111-8111-111111111111"


def _validate_a3_non_string(_case: dict[str, Any], exc: BaseException) -> None:
    assert isinstance(exc, ValueError)
    assert "created_after" in str(exc)
    cause = exc.__cause__
    assert isinstance(cause, ValueError)
    assert "12345" in str(cause)


def _validate_d3_empty_field(_case: dict[str, Any], exc: BaseException) -> None:
    assert str(exc).startswith(" must be")


def _validate_d5_raise_from(_case: dict[str, Any], exc: BaseException) -> None:
    cause = exc.__cause__
    assert cause is not None
    assert isinstance(cause, ValueError)
    assert "not-a-date" in str(cause)
    assert "not-a-date" not in str(exc)
    assert "ISO-8601" in str(exc)


def _validate_c5_microsecond(case: dict[str, Any], actual: datetime) -> None:
    assert actual is not None
    assert actual.microsecond == case["expected_microsecond"]


def _cursor_with_uuid(template: bytes) -> str:
    return urlsafe_b64_encode(template % _SAMPLE_UUID_STR.encode())


PARSE_DATETIME_VALUE_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "a1_tab", "field": "created_after", "raw": "\t", "expected": None},
    {"case_id": "a1_newline", "field": "created_after", "raw": "\n", "expected": None},
    {"case_id": "a1_crlf", "field": "created_after", "raw": "\r\n", "expected": None},
    {"case_id": "a1_mixed_ws", "field": "created_after", "raw": "   \t  \n  ", "expected": None},
    {"case_id": "a1_vtab", "field": "created_after", "raw": "\v", "expected": None},
    {"case_id": "a1_ff", "field": "created_after", "raw": "\f", "expected": None},
    {
        "case_id": "a2_upper",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00Z",
        "expected": datetime(2020, 1, 1, 0, 0, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "a4_bare_date",
        "field": "created_after",
        "raw": "2020-01-01",
        "expected": datetime(2020, 1, 1, 0, 0, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
        "assert_midnight": True,
    },
    {
        "case_id": "a5_strip_spaces",
        "field": "created_after",
        "raw": "  2020-01-01T00:00:00Z  ",
        "expected": datetime(2020, 1, 1, 0, 0, 0, tzinfo=_UTC),
    },
    {
        "case_id": "a5_strip_tabs",
        "field": "created_before",
        "raw": "\t2020-06-15T12:34:56Z\n",
        "expected": datetime(2020, 6, 15, 12, 34, 56, tzinfo=_UTC),
    },
    {
        "case_id": "b5_leap_2020",
        "field": "created_after",
        "raw": "2020-02-29",
        "expected": datetime(2020, 2, 29, 0, 0, 0, tzinfo=_UTC),
    },
    {
        "case_id": "b5_leap_2000",
        "field": "created_after",
        "raw": "2000-02-29",
        "expected": datetime(2000, 2, 29, 0, 0, 0, tzinfo=_UTC),
    },
    {
        "case_id": "c5_fractional",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00.123456",
        "expected": datetime(2020, 1, 1, 0, 0, 0, 123456, tzinfo=_UTC),
        "validate": _validate_c5_microsecond,
        "expected_microsecond": 123456,
    },
    {
        "case_id": "c5_max_micro",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00.999999",
        "expected": datetime(2020, 1, 1, 0, 0, 0, 999999, tzinfo=_UTC),
        "validate": _validate_c5_microsecond,
        "expected_microsecond": 999999,
    },
    {
        "case_id": "d2_z_literal",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00Z",
        "expected": datetime(2020, 1, 1, 0, 0, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "d2_offset_literal",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00+00:00",
        "expected": datetime(2020, 1, 1, 0, 0, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "d4_naive_wall_clock",
        "field": "created_after",
        "raw": "2020-06-15T12:34:56",
        "expected": datetime(2020, 6, 15, 12, 34, 56, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "d5_positive_offset",
        "field": "created_after",
        "raw": "2020-06-15T12:00:00+05:00",
        "expected": datetime(2020, 6, 15, 7, 0, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "d5_negative_offset",
        "field": "created_after",
        "raw": "2020-06-15T03:00:00-04:00",
        "expected": datetime(2020, 6, 15, 7, 0, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
)

PARSE_DATETIME_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a2_lower",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00z",
        "msg_contains": ("created_after", "ISO-8601"),
    },
    {
        "case_id": "a3_non_string",
        "field": "created_after",
        "raw": 12345,
        "validate": _validate_a3_non_string,
    },
    {
        "case_id": "b1_month_gt_12",
        "field": "created_after",
        "raw": "2020-13-01",
        "msg_contains": ("created_after", "ISO-8601"),
    },
    {
        "case_id": "b2_day_gt_31",
        "field": "created_after",
        "raw": "2020-01-32",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "b3_day_zero",
        "field": "created_after",
        "raw": "2020-01-00",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "b4_feb_30_leap",
        "field": "created_after",
        "raw": "2020-02-30",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "b4_feb_30_non_leap",
        "field": "created_after",
        "raw": "2021-02-30",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "b5_non_leap_2021",
        "field": "created_after",
        "raw": "2021-02-29",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "b5_century_non_leap_1900",
        "field": "created_after",
        "raw": "1900-02-29",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "c1_hour_gt_23",
        "field": "created_after",
        "raw": "2020-01-01T25:00:00",
        "msg_contains": ("created_after", "ISO-8601"),
    },
    {
        "case_id": "c2_minute_gt_59",
        "field": "created_after",
        "raw": "2020-01-01T00:60:00",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "c3_second_60",
        "field": "created_after",
        "raw": "2020-01-01T00:00:60",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "c4_offset_hour_oob",
        "field": "created_after",
        "raw": "2020-01-01T00:00:00+25:00",
        "msg_contains": ("created_after",),
    },
    {
        "case_id": "d1_created_after",
        "field": "created_after",
        "raw": "not-a-date",
        "msg_equals": "created_after" + _EXPECTED_ERROR_SUFFIX,
    },
    {
        "case_id": "d2_created_before",
        "field": "created_before",
        "raw": "not-a-date",
        "msg_equals": "created_before" + _EXPECTED_ERROR_SUFFIX,
    },
    {
        "case_id": "d3_empty_field",
        "field": "",
        "raw": "not-a-date",
        "msg_equals": "" + _EXPECTED_ERROR_SUFFIX,
        "validate": _validate_d3_empty_field,
    },
    {
        "case_id": "d4_arbitrary_field",
        "field": "custom_xyz_!!!",
        "raw": "not-a-date",
        "msg_contains": ("custom_xyz_!!!",),
        "msg_equals": "custom_xyz_!!!" + _EXPECTED_ERROR_SUFFIX,
    },
    {
        "case_id": "d5_raise_from",
        "field": "created_after",
        "raw": "not-a-date",
        "validate": _validate_d5_raise_from,
    },
)

DECODE_CURSOR_PART_A_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a1_single_a",
        "cursor": "a",
        "exc_type": binascii.Error,
        "msg_contains": ("data characters", "Invalid base64"),
        "msg_contains_any": True,
    },
    {"case_id": "a1_single_X", "cursor": "X", "exc_type": binascii.Error},
    {"case_id": "a1_single_z", "cursor": "z", "exc_type": binascii.Error},
    {
        "case_id": "a2_non_utf8",
        "cursor": urlsafe_b64_encode(b"\xff\xfe\xfd"),
        "exc_type": UnicodeDecodeError,
        "assert_encoding": "utf-8",
    },
    {
        "case_id": "a3_empty_json",
        "cursor": "=",
        "exc_type": json.JSONDecodeError,
        "msg_contains": ("line 1 column 1",),
    },
    {
        "case_id": "a4_non_json_text",
        "cursor": urlsafe_b64_encode(b"hello not json"),
        "exc_type": json.JSONDecodeError,
        "msg_contains": ("Expecting value",),
    },
    {
        "case_id": "a5_incomplete",
        "cursor": urlsafe_b64_encode(b"{incomplete"),
        "exc_type": json.JSONDecodeError,
    },
    {
        "case_id": "a5_comma",
        "cursor": urlsafe_b64_encode(b"{,}"),
        "exc_type": json.JSONDecodeError,
    },
    {
        "case_id": "a5_open_bracket",
        "cursor": urlsafe_b64_encode(b"["),
        "exc_type": json.JSONDecodeError,
    },
)

DECODE_CURSOR_PART_B_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "b1_int_json",
        "cursor": urlsafe_b64_encode(b"5"),
        "exc_type": TypeError,
        "msg_contains": ("subscriptable",),
    },
    {
        "case_id": "b2_null_json",
        "cursor": urlsafe_b64_encode(b"null"),
        "exc_type": TypeError,
        "msg_contains": ("NoneType",),
    },
    {
        "case_id": "b3_list_json",
        "cursor": urlsafe_b64_encode(b"[1, 2, 3]"),
        "exc_type": TypeError,
        "msg_contains": ("list indices", "integers or slices"),
        "msg_contains_any": True,
    },
    {
        "case_id": "b4_str_json",
        "cursor": urlsafe_b64_encode(b'"plain_string"'),
        "exc_type": TypeError,
        "msg_contains": ("string indices",),
    },
    {
        "case_id": "b5_missing_s",
        "cursor": urlsafe_b64_encode(b"{}"),
        "exc_type": KeyError,
        "exc_args": ("s",),
    },
    {
        "case_id": "b5_missing_r",
        "cursor": urlsafe_b64_encode(b'{"s": 1}'),
        "exc_type": KeyError,
        "exc_args": ("r",),
    },
    {
        "case_id": "b5_missing_s_with_r",
        "cursor": urlsafe_b64_encode(
            f'{{"r": "{_SAMPLE_UUID_STR}"}}'.encode(),
        ),
        "exc_type": KeyError,
        "exc_args": ("s",),
    },
)

DECODE_CURSOR_PART_C_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1_string_score",
        "cursor": _cursor_with_uuid(b'{"s": "abc", "r": "%s"}'),
        "msg_contains": ("invalid literal for int",),
        "assert_not_isinstance": TypeError,
    },
    {
        "case_id": "c2_list_score",
        "cursor": _cursor_with_uuid(b'{"s": [1, 2], "r": "%s"}'),
        "exc_type": TypeError,
        "msg_contains": ("int()", "non-string", "list"),
        "msg_contains_any": True,
        "assert_not_isinstance": ValueError,
    },
    {
        "case_id": "c3_bad_uuid",
        "cursor": urlsafe_b64_encode(b'{"s": 1, "r": "not-a-uuid"}'),
        "msg_contains": ("badly formed", "UUID"),
        "msg_contains_any": True,
    },
    {
        "case_id": "c4_int_run_id",
        "cursor": urlsafe_b64_encode(b'{"s": 1, "r": 5}'),
        "assert_not_isinstance": TypeError,
    },
    {
        "case_id": "c5_null_run_id",
        "cursor": urlsafe_b64_encode(b'{"s": 1, "r": null}'),
        "assert_not_isinstance": TypeError,
    },
)

CATCH_TUPLE_PREFLIGHT: tuple[dict[str, Any], ...] = (
    {
        "case_id": "json_decode",
        "subclass": json.JSONDecodeError,
        "base": ValueError,
        "expect_subclass": True,
    },
    {
        "case_id": "binascii",
        "subclass": binascii.Error,
        "base": ValueError,
        "expect_subclass": True,
    },
    {
        "case_id": "unicode_decode",
        "subclass": UnicodeDecodeError,
        "base": ValueError,
        "expect_subclass": True,
    },
    {
        "case_id": "key_error",
        "subclass": KeyError,
        "base": ValueError,
        "expect_subclass": False,
    },
    {
        "case_id": "type_error",
        "subclass": TypeError,
        "base": ValueError,
        "expect_subclass": False,
    },
)

ROUTE_INVALID_CURSOR_422_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d1_binascii",
        "cursor": "a",
        "expected_status": 422,
        "expected_code": "invalid_cursor",
        "expected_message": "cursor is not a valid keyset token",
        "assert_details_reason": True,
    },
    {
        "case_id": "d2_unicode",
        "cursor": base64.urlsafe_b64encode(b"\xff\xfe\xfd").decode().rstrip("="),
        "expected_status": 422,
        "expected_code": "invalid_cursor",
    },
    {
        "case_id": "d3_json",
        "cursor": base64.urlsafe_b64encode(b"not_json").decode().rstrip("="),
        "expected_status": 422,
        "expected_code": "invalid_cursor",
    },
    {
        "case_id": "d4_keyerror",
        "cursor": base64.urlsafe_b64encode(b"{}").decode().rstrip("="),
        "expected_status": 422,
        "expected_code": "invalid_cursor",
    },
    {
        "case_id": "d4_typeerror",
        "cursor": base64.urlsafe_b64encode(b"5").decode().rstrip("="),
        "expected_status": 422,
        "expected_code": "invalid_cursor",
    },
)

ROUTE_EMPTY_CURSOR_200_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "d5a_empty", "params": {"cursor": "", "limit": 5}},
    {"case_id": "d5b_omitted", "params": {"limit": 5}},
    {"case_id": "d5c_whitespace", "params": {"cursor": "   ", "limit": 5}},
)

SANITIZE_PROFILE_PREFIX_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "none", "raw": None, "expected": None},
    {"case_id": "empty", "raw": "", "expected": None},
    {"case_id": "spaces", "raw": "   ", "expected": None},
    {"case_id": "tab", "raw": "\t", "expected": None},
    {"case_id": "newline", "raw": "\n", "expected": None},
    {"case_id": "mixed_ws", "raw": "  \t\n  ", "expected": None},
    {"case_id": "lowercase", "raw": "default", "expected": "default"},
    {"case_id": "uppercase", "raw": "ADMIN", "expected": "ADMIN"},
    {"case_id": "digits", "raw": "12345", "expected": "12345"},
    {"case_id": "leading_digit", "raw": "1abc", "expected": "1abc"},
    {"case_id": "hyphens", "raw": "abc-def", "expected": "abc-def"},
    {"case_id": "underscores", "raw": "abc_def", "expected": "abc_def"},
    {"case_id": "dots", "raw": "abc.def", "expected": "abc.def"},
    {"case_id": "strip_padded", "raw": "  default  ", "expected": "default"},
    {"case_id": "leading_underscore", "raw": "_foo", "expected": None},
    {"case_id": "leading_dot", "raw": ".foo", "expected": None},
    {"case_id": "leading_hyphen", "raw": "-foo", "expected": None},
    {"case_id": "space_mid", "raw": "foo bar", "expected": None},
    {"case_id": "slash_mid", "raw": "foo/bar", "expected": None},
    {"case_id": "len_64", "raw": "a" + "b" * 63, "expected": "a" + "b" * 63},
    {"case_id": "len_65", "raw": "a" + "b" * 64, "expected": None},
)

ENCODE_CURSOR_ROUNDTRIP_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "seq_1", "seq": 1, "rid": _SAMPLE_RID},
    {"case_id": "seq_42", "seq": 42, "rid": _SAMPLE_RID_ALT},
    {"case_id": "seq_large", "seq": 9_999_999_999, "rid": _SAMPLE_RID_ALT},
)
