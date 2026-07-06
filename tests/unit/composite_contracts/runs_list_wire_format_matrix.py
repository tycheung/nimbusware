from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode

from api.schemas.openapi import (
    RUN_DETAIL_LINK_HEADER,
    RUN_FINDINGS_LINK_HEADER,
    RUN_TIMELINE_LINK_HEADER,
    format_run_detail_link_header,
    format_run_findings_link_header,
    format_run_timeline_link_header,
)

CANONICAL_RUN_ID = "11111111-1111-4111-8111-111111111111"
ALT_RUN_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
RFC5988_ENTRY_RE = re.compile(r'<(/v1/runs/[^>]+)>; rel="([a-z]+)"')

_BASE_QUERY_KWARGS: dict[str, Any] = {
    "limit": 50,
    "offset": None,
    "order": "newest_first",
    "include_summary": 0,
    "workflow_profile": None,
    "workflow_profile_prefix": None,
    "created_after": None,
    "created_before": None,
    "has_escalation": None,
}


def parse_link_entries(link_header: str) -> list[tuple[str, str]]:
    entries = link_header.split(", ")
    parsed: list[tuple[str, str]] = []
    for entry in entries:
        m = RFC5988_ENTRY_RE.fullmatch(entry)
        if m is None:
            msg = f"entry does not match RFC 5988 shape: {entry!r}"
            raise AssertionError(msg)
        parsed.append((m.group(1), m.group(2)))
    return parsed


def _validate_link_header_structural(_case: dict[str, Any], _actual: Any) -> None:
    for run_id in (CANONICAL_RUN_ID, ALT_RUN_ID):
        detail_out = format_run_detail_link_header(run_id)
        timeline_out = format_run_timeline_link_header(run_id)
        findings_out = format_run_findings_link_header(run_id)
        for label, out in (
            ("detail", detail_out),
            ("timeline", timeline_out),
            ("findings", findings_out),
        ):
            assert isinstance(out, str), (
                f"A1 fn={label!r} run_id={run_id!r}: formatter must return "
                f"``str`` (server emits it as an HTTP header value); got "
                f"{type(out).__name__}. A refactor that dropped a "
                f"``.decode()`` or wrapped the result in a tuple would "
                f"break ``response.headers['Link'] = ...`` assignment."
            )
            assert not isinstance(out, bytes), f"A1 fn={label!r}: not bytes"

    detail = format_run_detail_link_header(CANONICAL_RUN_ID)
    detail_entries = parse_link_entries(detail)
    assert len(detail_entries) == 2, (
        f"A2: detail formatter must emit exactly 2 RFC 5988 entries "
        f"(timeline + findings); got {len(detail_entries)}: {detail_entries!r}"
    )
    detail_rels = {rel for _uri, rel in detail_entries}
    assert detail_rels == {"timeline", "findings"}, (
        f"A2: detail rels must be {{'timeline', 'findings'}} (children of "
        f"the run detail page); got {detail_rels!r}. ``rel='run'`` MUST "
        f"NOT appear here because the detail page IS the run resource."
    )
    detail_uris = {uri for uri, _rel in detail_entries}
    assert detail_uris == {
        f"/v1/runs/{CANONICAL_RUN_ID}/timeline",
        f"/v1/runs/{CANONICAL_RUN_ID}/findings",
    }, f"A2: detail URIs must equal exact child paths; got {detail_uris!r}"

    timeline = format_run_timeline_link_header(CANONICAL_RUN_ID)
    timeline_entries = parse_link_entries(timeline)
    assert len(timeline_entries) == 2, (
        f"A3: timeline formatter must emit exactly 2 entries; got "
        f"{len(timeline_entries)}: {timeline_entries!r}"
    )
    timeline_rels = {rel for _uri, rel in timeline_entries}
    assert timeline_rels == {"run", "findings"}, (
        f"A3: timeline rels must be {{'run', 'findings'}} (parent + "
        f"sibling); got {timeline_rels!r}. ``rel='timeline'`` MUST NOT "
        f"appear because the timeline page IS the timeline resource."
    )
    timeline_uris = {uri for uri, _rel in timeline_entries}
    assert timeline_uris == {
        f"/v1/runs/{CANONICAL_RUN_ID}",
        f"/v1/runs/{CANONICAL_RUN_ID}/findings",
    }, (
        f"A3: timeline run-parent URL must be ``/v1/runs/{{id}}`` with NO "
        f"trailing slash and NO suffix; got {timeline_uris!r}"
    )

    findings = format_run_findings_link_header(CANONICAL_RUN_ID)
    findings_entries = parse_link_entries(findings)
    assert len(findings_entries) == 2, (
        f"A4: findings formatter must emit exactly 2 entries; got "
        f"{len(findings_entries)}: {findings_entries!r}"
    )
    findings_rels = {rel for _uri, rel in findings_entries}
    assert findings_rels == {"run", "timeline"}, (
        f"A4: findings rels must be {{'run', 'timeline'}} (mirror of "
        f"timeline with findings<->timeline swap); got {findings_rels!r}. "
        f"``rel='findings'`` MUST NOT appear because findings IS the "
        f"findings resource."
    )
    findings_uris = {uri for uri, _rel in findings_entries}
    assert findings_uris == {
        f"/v1/runs/{CANONICAL_RUN_ID}",
        f"/v1/runs/{CANONICAL_RUN_ID}/timeline",
    }, f"A4: findings URIs must equal parent + sibling timeline; got {findings_uris!r}"

    for label, out in (
        ("detail", detail),
        ("timeline", timeline),
        ("findings", findings),
    ):
        for sep in (",,", ";,", "\n", "\t", ",  "):
            assert sep not in out, (
                f"A5 fn={label!r}: forbidden separator {sep!r} found in "
                f"output {out!r}. A refactor that used double-comma, "
                f"semicolon-comma, newline, tab, or double-space "
                f"separators would break RFC 5988 clients."
            )
        assert ", " in out, (
            f"A5 fn={label!r}: canonical ``', '`` separator (comma + "
            f"single space) must join the 2 entries; got {out!r}"
        )
        entries = out.split(", ")
        assert len(entries) == 2, (
            f"A5 fn={label!r}: splitting on ``', '`` must yield exactly 2 "
            f"entries; got {len(entries)}: {entries!r}"
        )
        for entry in entries:
            assert RFC5988_ENTRY_RE.fullmatch(entry) is not None, (
                f"A5 fn={label!r}: each entry must match "
                f'``<URI>; rel="..."`` (angle brackets + semicolon-space '
                f"+ double-quoted rel); got {entry!r}"
            )


def _validate_link_header_navigation(_case: dict[str, Any], _actual: Any) -> None:
    edge_run_ids = [
        "ffffffff-ffff-4fff-8fff-ffffffffffff",
        "00000000-0000-4000-8000-000000000000",
        CANONICAL_RUN_ID,
        ALT_RUN_ID,
    ]
    for run_id in edge_run_ids:
        detail_out = format_run_detail_link_header(run_id)
        timeline_out = format_run_timeline_link_header(run_id)
        findings_out = format_run_findings_link_header(run_id)
        for label, out in (
            ("detail", detail_out),
            ("timeline", timeline_out),
            ("findings", findings_out),
        ):
            assert run_id in out, (
                f"B1 fn={label!r} run_id={run_id!r}: input ``run_id`` must "
                f"appear verbatim in the output (NO URL-encoding, NO "
                f"normalisation). A refactor that wrapped with "
                f"``urllib.parse.quote(run_id)`` would re-encode dashes "
                f"and break URL templates. Got: {out!r}"
            )

    detail_t = parse_link_entries(format_run_detail_link_header(CANONICAL_RUN_ID))
    timeline_t = parse_link_entries(format_run_timeline_link_header(CANONICAL_RUN_ID))
    findings_t = parse_link_entries(format_run_findings_link_header(CANONICAL_RUN_ID))
    all_uris = {uri for uri, _rel in (*detail_t, *timeline_t, *findings_t)}
    expected_three = {
        f"/v1/runs/{CANONICAL_RUN_ID}",
        f"/v1/runs/{CANONICAL_RUN_ID}/timeline",
        f"/v1/runs/{CANONICAL_RUN_ID}/findings",
    }
    assert all_uris == expected_three, (
        f"B2: navigation triangle -- union of URIs across all 3 formatters "
        f"must equal exactly 3 distinct URIs (run + timeline + findings); "
        f"got {all_uris!r}. A refactor that introduced a 4th resource "
        f"(e.g. ``/v1/runs/{{id}}/events``) without updating the triangle "
        f"would silently expand the navigation graph."
    )

    detail_self = f"</v1/runs/{CANONICAL_RUN_ID}>"
    detail_str = format_run_detail_link_header(CANONICAL_RUN_ID)
    assert detail_self not in detail_str, (
        f"B3: detail formatter must OMIT the run-parent URL "
        f"({detail_self!r}) because the detail page IS the run "
        f"resource. A refactor that included a self-link would loop "
        f"clients back. Got: {detail_str!r}"
    )

    timeline_str = format_run_timeline_link_header(CANONICAL_RUN_ID)
    assert "/timeline" not in timeline_str, (
        f"B3: timeline formatter must OMIT the ``/timeline`` suffix in any "
        f"URI because the timeline page IS the timeline resource. Got: "
        f"{timeline_str!r}"
    )

    findings_str = format_run_findings_link_header(CANONICAL_RUN_ID)
    assert "/findings" not in findings_str, (
        f"B3: findings formatter must OMIT the ``/findings`` suffix. Got: {findings_str!r}"
    )

    for label, fn in (
        ("detail", format_run_detail_link_header),
        ("timeline", format_run_timeline_link_header),
        ("findings", format_run_findings_link_header),
    ):
        call_one = fn(CANONICAL_RUN_ID)
        call_two = fn(CANONICAL_RUN_ID)
        assert call_one == call_two, (
            f"B4 fn={label!r}: formatter must be a pure ``str -> str`` "
            f"function (no clock, no global state, no randomness). Got "
            f"divergent outputs: {call_one!r} vs {call_two!r}"
        )

    assert RUN_DETAIL_LINK_HEADER["example"] == format_run_detail_link_header(CANONICAL_RUN_ID), (
        f"B5: ``RUN_DETAIL_LINK_HEADER['example']`` must equal "
        f"``format_run_detail_link_header({CANONICAL_RUN_ID!r})`` "
        f"byte-for-byte. A refactor that changed the formatter shape "
        f"without updating the OpenAPI example would desynchronise the "
        f"documented contract from runtime emission. example="
        f"{RUN_DETAIL_LINK_HEADER['example']!r} fn-output="
        f"{format_run_detail_link_header(CANONICAL_RUN_ID)!r}"
    )
    assert RUN_TIMELINE_LINK_HEADER["example"] == format_run_timeline_link_header(
        CANONICAL_RUN_ID
    ), (
        f"B5: ``RUN_TIMELINE_LINK_HEADER['example']`` must equal "
        f"``format_run_timeline_link_header({CANONICAL_RUN_ID!r})`` "
        f"byte-for-byte; example="
        f"{RUN_TIMELINE_LINK_HEADER['example']!r}"
    )
    assert RUN_FINDINGS_LINK_HEADER["example"] == format_run_findings_link_header(
        CANONICAL_RUN_ID
    ), (
        f"B5: ``RUN_FINDINGS_LINK_HEADER['example']`` must equal "
        f"``format_run_findings_link_header({CANONICAL_RUN_ID!r})`` "
        f"byte-for-byte; example="
        f"{RUN_FINDINGS_LINK_HEADER['example']!r}"
    )


def _validate_c4_int_inputs(_case: dict[str, Any], actual: str) -> None:
    assert "limit=20" in actual, (
        f"C4: ``limit`` int must be coerced via ``str(limit)`` (urlencode "
        f"would crash on raw int in some Python versions, OR coerce "
        f"unexpectedly). Got: {actual!r}"
    )
    assert "include_summary=1" in actual, (
        f"C4: ``include_summary`` int must serialise as the bare digit "
        f"``1`` (NOT ``True``). A refactor that omitted ``str(...)`` and "
        f"passed a bool would emit ``include_summary=True``. Got: "
        f"{actual!r}"
    )


def _validate_d1_key_order(_case: dict[str, Any], actual: str) -> None:
    parsed_pairs = parse_qsl(actual, keep_blank_values=True)
    actual_keys = [k for k, _v in parsed_pairs]
    expected_keys = [
        "limit",
        "order",
        "include_summary",
        "cursor",
        "workflow_profile",
        "workflow_profile_prefix",
        "created_after",
        "created_before",
        "has_escalation",
        "status",
    ]
    assert actual_keys == expected_keys, (
        f"D1: optional appends must follow exact order "
        f"limit/order/include_summary/cursor/workflow_profile/"
        f"workflow_profile_prefix/created_after/created_before/"
        f"has_escalation/status. A refactor that reordered any of the "
        f"6 conditional appends would change URL prefix matching. "
        f"Got: {actual_keys!r}"
    )


def _validate_d2_status_rename(_case: dict[str, Any], actual: str) -> None:
    assert "status=created" in actual, (
        f"D2 KEY DIVERGENCE: ``list_status='created'`` kwarg must appear "
        f"as ``status=created`` in the URL (NOT ``list_status=created``). "
        f"The kwarg name and URL-param name differ. A refactor that used "
        f"``list_status`` as the param would break URL clients expecting "
        f"``?status=running``. Got: {actual!r}"
    )
    assert "list_status=" not in actual, (
        f"D2: ``list_status=`` must NOT appear in the URL at all; got: {actual!r}"
    )


def _validate_d4_special_chars(_case: dict[str, Any], actual: str) -> None:
    assert "workflow_profile=my+profile" in actual, (
        f"D4: spaces in ``workflow_profile`` must be encoded as ``+`` "
        f"(``urllib.parse.urlencode`` default uses ``quote_plus``). A "
        f"refactor to a custom encoder might leave literal spaces and "
        f"break URL parsing. Got: {actual!r}"
    )
    assert "workflow_profile_prefix=a%2Bb" in actual, (
        f"D4: literal ``+`` in values must be encoded as ``%2B`` (NOT "
        f"left as bare ``+`` which would be interpreted by parsers as a "
        f"space). Got: {actual!r}"
    )
    assert "created_after=2020-01-01T00%3A00%3A00%2B00%3A00" in actual, (
        f"D4: ISO-8601 datetime with ``:`` and ``+`` must be fully "
        f"percent-encoded (``:`` -> ``%3A``, ``+`` -> ``%2B``). Pins "
        f"that the encoder is ``urllib.parse.urlencode`` (which uses "
        f"``quote_plus``), NOT a partial-encoder that leaves ``:`` raw. "
        f"Got: {actual!r}"
    )
    rebuilt = urlencode(
        [
            ("workflow_profile", "my profile"),
            ("workflow_profile_prefix", "a+b"),
            ("created_after", "2020-01-01T00:00:00+00:00"),
        ]
    )
    assert rebuilt in actual, (
        f"D4: helper output must contain the ``urlencode``-generated "
        f"substring byte-for-byte (cross-check). Got: "
        f"{actual!r} expected substring: {rebuilt!r}"
    )


def _validate_d5_all_none(_case: dict[str, Any], actual: str) -> None:
    assert actual == "limit=50&order=newest_first&include_summary=0", (
        f"D5: all-optional-None call must equal the C1 base string "
        f"exactly. A refactor that omitted the ``is not None`` checks and "
        f"unconditionally appended ``(key, str(value))`` would produce "
        f"entries like ``workflow_profile=None`` that clients would "
        f"misinterpret as the literal filter value ``None``. Got: "
        f"{actual!r}"
    )
    for forbidden in (
        "workflow_profile=",
        "workflow_profile_prefix=",
        "created_after=",
        "created_before=",
        "has_escalation=",
        "cursor=",
        "status=",
        "=None",
    ):
        assert forbidden not in actual, (
            f"D5: forbidden substring {forbidden!r} found in all-None "
            f"output ``{actual!r}``; pins that excluded fields produce "
            f"no key=value entry at all"
        )


LINK_HEADER_STRUCTURAL_CASE: dict[str, Any] = {
    "case_id": "link_header_structural",
    "validate": _validate_link_header_structural,
}

LINK_HEADER_NAVIGATION_CASE: dict[str, Any] = {
    "case_id": "link_header_navigation",
    "validate": _validate_link_header_navigation,
}

QUERY_STRING_BASE_OFFSET_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1_base",
        "kwargs": dict(_BASE_QUERY_KWARGS),
        "expected": "limit=50&order=newest_first&include_summary=0",
    },
    {
        "case_id": "c2_with_offset",
        "kwargs": {**_BASE_QUERY_KWARGS, "offset": 10},
        "expected": "limit=50&offset=10&order=newest_first&include_summary=0",
    },
    {
        "case_id": "c3_offset_zero",
        "kwargs": {**_BASE_QUERY_KWARGS, "offset": 0},
        "expected": "limit=50&offset=0&order=newest_first&include_summary=0",
    },
    {
        "case_id": "c4_int_inputs",
        "kwargs": {
            **_BASE_QUERY_KWARGS,
            "limit": 20,
            "order": "oldest_first",
            "include_summary": 1,
        },
        "validate": _validate_c4_int_inputs,
    },
    {
        "case_id": "c5_cursor_no_offset",
        "kwargs": {**_BASE_QUERY_KWARGS, "cursor": "abc"},
        "expected": "limit=50&order=newest_first&include_summary=0&cursor=abc",
    },
    {
        "case_id": "c5_cursor_and_offset",
        "kwargs": {**_BASE_QUERY_KWARGS, "offset": 10, "cursor": "abc"},
        "expected": ("limit=50&offset=10&order=newest_first&include_summary=0&cursor=abc"),
    },
)

QUERY_STRING_OPTIONAL_APPEND_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d1_full",
        "kwargs": {
            **_BASE_QUERY_KWARGS,
            "workflow_profile": "default",
            "workflow_profile_prefix": "def",
            "created_after": "2020-01-01",
            "created_before": "2026-12-31",
            "has_escalation": 1,
            "cursor": "c",
            "list_status": "running",
        },
        "validate": _validate_d1_key_order,
    },
    {
        "case_id": "d2_status_only",
        "kwargs": {**_BASE_QUERY_KWARGS, "list_status": "created"},
        "validate": _validate_d2_status_rename,
    },
    {
        "case_id": "d3_esc_zero",
        "kwargs": {**_BASE_QUERY_KWARGS, "has_escalation": 0},
        "expected_contains": "has_escalation=0",
    },
    {
        "case_id": "d3_esc_one",
        "kwargs": {**_BASE_QUERY_KWARGS, "has_escalation": 1},
        "expected_contains": "has_escalation=1",
    },
    {
        "case_id": "d3_esc_none",
        "kwargs": dict(_BASE_QUERY_KWARGS),
        "forbidden_contains": "has_escalation",
    },
    {
        "case_id": "d4_special_chars",
        "kwargs": {
            **_BASE_QUERY_KWARGS,
            "workflow_profile": "my profile",
            "workflow_profile_prefix": "a+b",
            "created_after": "2020-01-01T00:00:00+00:00",
        },
        "validate": _validate_d4_special_chars,
    },
    {
        "case_id": "d5_all_none",
        "kwargs": dict(_BASE_QUERY_KWARGS),
        "validate": _validate_d5_all_none,
    },
)
