"""``GET /v1/runs`` RFC 5988 wire-format composite (fo113).

Four sibling helpers shape the user-visible HTTP wire format for
``GET /v1/runs`` and its sub-resources:

* ``format_run_detail_link_header`` -- ``GET /v1/runs/{id}`` -> children
  ``timeline`` + ``findings``
* ``format_run_timeline_link_header`` -- ``GET /v1/runs/{id}/timeline``
  -> parent ``run`` + sibling ``findings``
* ``format_run_findings_link_header`` -- ``GET /v1/runs/{id}/findings``
  -> parent ``run`` + sibling ``timeline``
* ``_runs_list_query_string`` -- builds the ``next``/``prev`` URL
  query string for the ``Link`` header on ``GET /v1/runs``

Today they are sampled only via end-to-end FastAPI substring
assertions in [tests/test_api.py](tests/test_api.py)
(``test_get_run_includes_rfc5988_link_header``,
``test_timeline_and_findings_include_rfc5988_link_headers``,
``test_list_runs_link_header_next_and_prev``,
``test_list_runs_keyset_cursor_walk``). None pin the exact RFC 5988
entry syntax (angle brackets, semicolon-space, quoted ``rel``,
comma-space separator), the navigation-triangle self-omission, the
``_runs_list_query_string`` param ordering (limit/order/include_summary
base + offset-at-index-1 insertion + optional-field append order),
or the ``list_status`` -> ``status`` key rename. A repo-wide
``Grep`` for the four helper names returns only their definition
site (formatters) or two route call sites (``_runs_list_query_string``).

fo113 closes the gap with 4 parts spanning 20 axes (no source
changes):

* **Part A** -- link-header trio structural shape (5 axes): ``str``
  return type, detail 2-entry ``rel=timeline``+``rel=findings``,
  timeline ``rel=run``+``rel=findings``, findings
  ``rel=run``+``rel=timeline``, RFC 5988 entry syntax regex.
* **Part B** -- trio navigation triangle + determinism (5 axes):
  verbatim ``run_id`` substitution, 3-distinct-URL union,
  self-omission, determinism, OpenAPI ``example`` cross-consistency.
* **Part C** -- ``_runs_list_query_string`` base + offset insertion
  (5 axes): base 3-key prefix, ``offset`` insertion at index 1,
  ``offset=0`` vs ``None`` divergence, ``str()`` coercion of
  ``limit``/``include_summary``, ``cursor`` append after the base
  prefix.
* **Part D** -- ``_runs_list_query_string`` optional appends + key
  transformations (5 axes): 6-field append order, ``list_status``
  -> ``status`` rename, ``has_escalation`` 0-vs-None divergence,
  ``urlencode`` special-char encoding, all-None excludes
  (no empty-value entries).

KEY DIVERGENCES pinned:

* **RFC 5988 entry separator** -- entries are joined by ``", "``
  (comma + ASCII space). A refactor that dropped the space or used
  ``";"`` would break clients that split on ``", "`` exactly.
  Pinned in Parts A5 and D1.
* **Navigation-triangle self-omission** -- each formatter omits the
  URL representing its own page resource so clients don't loop
  back to the current page when following ``Link`` rels. Pinned
  in Part B3.
* **offset insertion at index 1** -- ``pairs.insert(1, ("offset", ...))``
  places ``offset`` BETWEEN ``limit`` and ``order`` in the URL.
  A refactor to ``append`` would move ``offset`` to the end of
  the base prefix and silently shift URL parsers. Pinned in Part
  C2.
* **offset=0 vs None / has_escalation=0 vs None** -- both use
  ``is not None`` checks (NOT truthiness); both ``0`` values MUST
  appear in the URL. A refactor to ``if offset:`` / ``if
  has_escalation:`` would silently drop the falsy-int filter
  values. Pinned in Parts C3 and D3.
* **list_status -> status kwarg-to-param rename** -- the kwarg is
  ``list_status`` but the URL param is ``status``. A refactor
  that used ``list_status`` as the param would break URL clients
  expecting ``?status=running``. Pinned in Part D2.
* **OpenAPI example cross-consistency** -- the three
  ``RUN_*_LINK_HEADER`` dict ``example`` strings equal the
  corresponding formatter outputs for the canonical UUID
  byte-for-byte. A refactor that changed one side without the
  other would desynchronise the documented contract from runtime
  emission. Pinned in Part B5.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode

from nimbusware_api.routes.runs import _runs_list_query_string
from nimbusware_api.schemas.openapi import (
    RUN_DETAIL_LINK_HEADER,
    RUN_FINDINGS_LINK_HEADER,
    RUN_TIMELINE_LINK_HEADER,
    format_run_detail_link_header,
    format_run_findings_link_header,
    format_run_timeline_link_header,
)

_CANONICAL_RUN_ID = "11111111-1111-4111-8111-111111111111"
_ALT_RUN_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
_RFC5988_ENTRY_RE = re.compile(r'<(/v1/runs/[^>]+)>; rel="([a-z]+)"')


def _parse_link_entries(link_header: str) -> list[tuple[str, str]]:
    """Parse a 2-entry RFC 5988 Link string into ``[(uri, rel), ...]``.

    Splits on the canonical ``", "`` separator (comma + space) and
    applies ``_RFC5988_ENTRY_RE`` per entry. Used across Parts A
    and B; centralised so refactor pressure on the parsing
    heuristic stays in one place rather than scattered across 6
    axis blocks.
    """
    entries = link_header.split(", ")
    parsed: list[tuple[str, str]] = []
    for entry in entries:
        m = _RFC5988_ENTRY_RE.fullmatch(entry)
        if m is None:
            msg = f"entry does not match RFC 5988 shape: {entry!r}"
            raise AssertionError(msg)
        parsed.append((m.group(1), m.group(2)))
    return parsed


def test_link_header_trio_structural_shape_5_axis() -> None:
    """Pin link-header trio structural shape (5 axes).

    Implementations at [openapi.py:71-128](packages/nimbusware_api/schemas/openapi.py).

    A1 / A2 / A3 / A4 / A5 pin: ``str`` return type for all three,
    detail's 2-entry ``rel="timeline"`` + ``rel="findings"`` shape,
    timeline's ``rel="run"`` + ``rel="findings"`` shape, findings'
    ``rel="run"`` + ``rel="timeline"`` shape (mirror of A3), and
    the RFC 5988 per-entry syntax regex pinned across all three
    functions via the shared ``_parse_link_entries`` helper.
    """
    for run_id in (_CANONICAL_RUN_ID, _ALT_RUN_ID):
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

    detail = format_run_detail_link_header(_CANONICAL_RUN_ID)
    detail_entries = _parse_link_entries(detail)
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
        f"/v1/runs/{_CANONICAL_RUN_ID}/timeline",
        f"/v1/runs/{_CANONICAL_RUN_ID}/findings",
    }, (
        f"A2: detail URIs must equal exact child paths; got {detail_uris!r}"
    )

    timeline = format_run_timeline_link_header(_CANONICAL_RUN_ID)
    timeline_entries = _parse_link_entries(timeline)
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
        f"/v1/runs/{_CANONICAL_RUN_ID}",
        f"/v1/runs/{_CANONICAL_RUN_ID}/findings",
    }, (
        f"A3: timeline run-parent URL must be ``/v1/runs/{{id}}`` with NO "
        f"trailing slash and NO suffix; got {timeline_uris!r}"
    )

    findings = format_run_findings_link_header(_CANONICAL_RUN_ID)
    findings_entries = _parse_link_entries(findings)
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
        f"/v1/runs/{_CANONICAL_RUN_ID}",
        f"/v1/runs/{_CANONICAL_RUN_ID}/timeline",
    }, (
        f"A4: findings URIs must equal parent + sibling timeline; got "
        f"{findings_uris!r}"
    )

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
            assert _RFC5988_ENTRY_RE.fullmatch(entry) is not None, (
                f"A5 fn={label!r}: each entry must match "
                f"``<URI>; rel=\"...\"`` (angle brackets + semicolon-space "
                f"+ double-quoted rel); got {entry!r}"
            )


def test_link_header_trio_navigation_triangle_and_determinism_5_axis() -> None:
    """Pin link-header trio navigation triangle + determinism (5 axes).

    B1 / B2 / B3 / B4 / B5 pin: verbatim run_id substitution
    (no URL-encoding), the 3-resource navigation triangle (union of
    URIs is exactly 3), self-omission per page, determinism /
    purity, and OpenAPI ``example`` cross-consistency.
    """
    edge_run_ids = [
        "ffffffff-ffff-4fff-8fff-ffffffffffff",
        "00000000-0000-4000-8000-000000000000",
        _CANONICAL_RUN_ID,
        _ALT_RUN_ID,
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

    detail_t = _parse_link_entries(format_run_detail_link_header(_CANONICAL_RUN_ID))
    timeline_t = _parse_link_entries(format_run_timeline_link_header(_CANONICAL_RUN_ID))
    findings_t = _parse_link_entries(format_run_findings_link_header(_CANONICAL_RUN_ID))
    all_uris = {uri for uri, _rel in (*detail_t, *timeline_t, *findings_t)}
    expected_three = {
        f"/v1/runs/{_CANONICAL_RUN_ID}",
        f"/v1/runs/{_CANONICAL_RUN_ID}/timeline",
        f"/v1/runs/{_CANONICAL_RUN_ID}/findings",
    }
    assert all_uris == expected_three, (
        f"B2: navigation triangle -- union of URIs across all 3 formatters "
        f"must equal exactly 3 distinct URIs (run + timeline + findings); "
        f"got {all_uris!r}. A refactor that introduced a 4th resource "
        f"(e.g. ``/v1/runs/{{id}}/events``) without updating the triangle "
        f"would silently expand the navigation graph."
    )

    detail_self = f"</v1/runs/{_CANONICAL_RUN_ID}>"
    detail_str = format_run_detail_link_header(_CANONICAL_RUN_ID)
    assert detail_self not in detail_str, (
        f"B3: detail formatter must OMIT the run-parent URL "
        f"({detail_self!r}) because the detail page IS the run "
        f"resource. A refactor that included a self-link would loop "
        f"clients back. Got: {detail_str!r}"
    )

    timeline_str = format_run_timeline_link_header(_CANONICAL_RUN_ID)
    assert "/timeline" not in timeline_str, (
        f"B3: timeline formatter must OMIT the ``/timeline`` suffix in any "
        f"URI because the timeline page IS the timeline resource. Got: "
        f"{timeline_str!r}"
    )

    findings_str = format_run_findings_link_header(_CANONICAL_RUN_ID)
    assert "/findings" not in findings_str, (
        f"B3: findings formatter must OMIT the ``/findings`` suffix. Got: "
        f"{findings_str!r}"
    )

    for label, fn in (
        ("detail", format_run_detail_link_header),
        ("timeline", format_run_timeline_link_header),
        ("findings", format_run_findings_link_header),
    ):
        call_one = fn(_CANONICAL_RUN_ID)
        call_two = fn(_CANONICAL_RUN_ID)
        assert call_one == call_two, (
            f"B4 fn={label!r}: formatter must be a pure ``str -> str`` "
            f"function (no clock, no global state, no randomness). Got "
            f"divergent outputs: {call_one!r} vs {call_two!r}"
        )

    assert (
        RUN_DETAIL_LINK_HEADER["example"]
        == format_run_detail_link_header(_CANONICAL_RUN_ID)
    ), (
        f"B5: ``RUN_DETAIL_LINK_HEADER['example']`` must equal "
        f"``format_run_detail_link_header({_CANONICAL_RUN_ID!r})`` "
        f"byte-for-byte. A refactor that changed the formatter shape "
        f"without updating the OpenAPI example would desynchronise the "
        f"documented contract from runtime emission. example="
        f"{RUN_DETAIL_LINK_HEADER['example']!r} fn-output="
        f"{format_run_detail_link_header(_CANONICAL_RUN_ID)!r}"
    )
    assert (
        RUN_TIMELINE_LINK_HEADER["example"]
        == format_run_timeline_link_header(_CANONICAL_RUN_ID)
    ), (
        f"B5: ``RUN_TIMELINE_LINK_HEADER['example']`` must equal "
        f"``format_run_timeline_link_header({_CANONICAL_RUN_ID!r})`` "
        f"byte-for-byte; example="
        f"{RUN_TIMELINE_LINK_HEADER['example']!r}"
    )
    assert (
        RUN_FINDINGS_LINK_HEADER["example"]
        == format_run_findings_link_header(_CANONICAL_RUN_ID)
    ), (
        f"B5: ``RUN_FINDINGS_LINK_HEADER['example']`` must equal "
        f"``format_run_findings_link_header({_CANONICAL_RUN_ID!r})`` "
        f"byte-for-byte; example="
        f"{RUN_FINDINGS_LINK_HEADER['example']!r}"
    )


def test_runs_list_query_string_base_and_offset_5_axis() -> None:
    """Pin ``_runs_list_query_string`` base + offset insertion (5 axes).

    Implementation at [runs.py:211-246](packages/nimbusware_api/routes/runs.py):

    .. code-block:: python

        pairs = [("limit", str(limit)), ("order", order),
                 ("include_summary", str(include_summary))]
        if offset is not None:
            pairs.insert(1, ("offset", str(offset)))
        if cursor is not None:
            pairs.append(("cursor", cursor))
        ...
        return urlencode(pairs)

    C1 / C2 / C3 / C4 / C5 pin: base 3-key prefix order
    (limit/order/include_summary), ``offset`` insertion at index 1
    (between limit and order), the ``offset=0`` vs ``None``
    divergence catching truthiness-refactors, the ``str()`` coercion
    of ``limit`` / ``include_summary`` ints, and ``cursor`` append
    AFTER the base prefix.
    """
    base = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
    )
    assert base == "limit=50&order=newest_first&include_summary=0", (
        f"C1: base 3-key prefix (all optional kwargs ``None``) must equal "
        f"``limit=<x>&order=<x>&include_summary=<x>`` in that exact order "
        f"(NOT alphabetical, NOT reverse). A refactor that switched to "
        f"alphabetical ordering would shift clients' expected URL prefix. "
        f"Got: {base!r}"
    )

    with_offset = _runs_list_query_string(
        limit=50,
        offset=10,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
    )
    assert with_offset == "limit=50&offset=10&order=newest_first&include_summary=0", (
        f"C2: ``offset`` MUST be inserted at index 1 (between ``limit`` "
        f"and ``order``), NOT appended at the end. A refactor that used "
        f"``pairs.append(...)`` would produce "
        f"``limit&order&include_summary&offset`` -- a different URL prefix "
        f"that clients matching on ``limit=...&offset=...`` would fail to "
        f"recognise. Got: {with_offset!r}"
    )

    with_offset_zero = _runs_list_query_string(
        limit=50,
        offset=0,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
    )
    assert with_offset_zero == "limit=50&offset=0&order=newest_first&include_summary=0", (
        f"C3 KEY DIVERGENCE: ``offset=0`` (int zero, NOT ``None``) MUST "
        f"insert because the helper uses ``is not None`` (NOT truthiness). "
        f"A refactor to ``if offset:`` would silently drop offset=0 -- "
        f"the natural first-page value -- from the URL. Got: "
        f"{with_offset_zero!r}"
    )

    with_int_inputs = _runs_list_query_string(
        limit=20,
        offset=None,
        order="oldest_first",
        include_summary=1,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
    )
    assert "limit=20" in with_int_inputs, (
        f"C4: ``limit`` int must be coerced via ``str(limit)`` (urlencode "
        f"would crash on raw int in some Python versions, OR coerce "
        f"unexpectedly). Got: {with_int_inputs!r}"
    )
    assert "include_summary=1" in with_int_inputs, (
        f"C4: ``include_summary`` int must serialise as the bare digit "
        f"``1`` (NOT ``True``). A refactor that omitted ``str(...)`` and "
        f"passed a bool would emit ``include_summary=True``. Got: "
        f"{with_int_inputs!r}"
    )

    with_cursor_no_offset = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
        cursor="abc",
    )
    assert (
        with_cursor_no_offset
        == "limit=50&order=newest_first&include_summary=0&cursor=abc"
    ), (
        f"C5: ``cursor`` MUST append AFTER the base 3-key prefix when "
        f"``offset=None`` (NOT before, NOT inserted at index 1). Got: "
        f"{with_cursor_no_offset!r}"
    )

    with_cursor_and_offset = _runs_list_query_string(
        limit=50,
        offset=10,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
        cursor="abc",
    )
    assert (
        with_cursor_and_offset
        == "limit=50&offset=10&order=newest_first&include_summary=0&cursor=abc"
    ), (
        f"C5: with BOTH ``offset=10`` and ``cursor='abc'`` (degenerate "
        f"case the route layer guards against but the helper does not), "
        f"the ordering must be limit/offset/order/include_summary/cursor "
        f"-- offset inserted at index 1, cursor appended after the base "
        f"prefix. Got: {with_cursor_and_offset!r}"
    )


def test_runs_list_query_string_optional_appends_and_rename_5_axis() -> None:
    """Pin ``_runs_list_query_string`` optional appends + key transformations (5 axes).

    D1 / D2 / D3 / D4 / D5 pin: 6-field append order (workflow_profile
    .. list_status), the ``list_status -> status`` URL-param rename
    divergence, the ``has_escalation=0`` vs ``None`` divergence, the
    ``urlencode`` special-char coverage (space -> ``+``, ``+`` ->
    ``%2B``, ``:`` -> ``%3A``), and the all-None-excludes invariant
    (no empty-value entries leak into the URL).
    """
    full = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile="default",
        workflow_profile_prefix="def",
        created_after="2020-01-01",
        created_before="2026-12-31",
        has_escalation=1,
        cursor="c",
        list_status="running",
    )
    parsed_pairs = parse_qsl(full, keep_blank_values=True)
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

    with_status_only = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
        list_status="created",
    )
    assert "status=created" in with_status_only, (
        f"D2 KEY DIVERGENCE: ``list_status='created'`` kwarg must appear "
        f"as ``status=created`` in the URL (NOT ``list_status=created``). "
        f"The kwarg name and URL-param name differ. A refactor that used "
        f"``list_status`` as the param would break URL clients expecting "
        f"``?status=running``. Got: {with_status_only!r}"
    )
    assert "list_status=" not in with_status_only, (
        f"D2: ``list_status=`` must NOT appear in the URL at all; got: "
        f"{with_status_only!r}"
    )

    with_esc_zero = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=0,
    )
    assert "has_escalation=0" in with_esc_zero, (
        f"D3 KEY DIVERGENCE: ``has_escalation=0`` (int zero, NOT None) "
        f"MUST appear in the URL (helper uses ``is not None`` + "
        f"``str(has_escalation)``). A refactor to truthiness "
        f"``if has_escalation:`` would silently drop the no-escalation "
        f"filter and return ALL runs instead of just non-escalated ones. "
        f"Got: {with_esc_zero!r}"
    )

    with_esc_one = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=1,
    )
    assert "has_escalation=1" in with_esc_one, (
        f"D3: ``has_escalation=1`` must appear; got {with_esc_one!r}"
    )

    with_esc_none = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
    )
    assert "has_escalation" not in with_esc_none, (
        f"D3: ``has_escalation=None`` MUST be excluded from the URL "
        f"entirely (no ``has_escalation=None`` literal, no "
        f"``has_escalation=`` empty); got: {with_esc_none!r}"
    )

    with_special_chars = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile="my profile",
        workflow_profile_prefix="a+b",
        created_after="2020-01-01T00:00:00+00:00",
        created_before=None,
        has_escalation=None,
    )
    assert "workflow_profile=my+profile" in with_special_chars, (
        f"D4: spaces in ``workflow_profile`` must be encoded as ``+`` "
        f"(``urllib.parse.urlencode`` default uses ``quote_plus``). A "
        f"refactor to a custom encoder might leave literal spaces and "
        f"break URL parsing. Got: {with_special_chars!r}"
    )
    assert "workflow_profile_prefix=a%2Bb" in with_special_chars, (
        f"D4: literal ``+`` in values must be encoded as ``%2B`` (NOT "
        f"left as bare ``+`` which would be interpreted by parsers as a "
        f"space). Got: {with_special_chars!r}"
    )
    assert (
        "created_after=2020-01-01T00%3A00%3A00%2B00%3A00" in with_special_chars
    ), (
        f"D4: ISO-8601 datetime with ``:`` and ``+`` must be fully "
        f"percent-encoded (``:`` -> ``%3A``, ``+`` -> ``%2B``). Pins "
        f"that the encoder is ``urllib.parse.urlencode`` (which uses "
        f"``quote_plus``), NOT a partial-encoder that leaves ``:`` raw. "
        f"Got: {with_special_chars!r}"
    )

    rebuilt = urlencode(
        [
            ("workflow_profile", "my profile"),
            ("workflow_profile_prefix", "a+b"),
            ("created_after", "2020-01-01T00:00:00+00:00"),
        ]
    )
    assert rebuilt in with_special_chars, (
        f"D4: helper output must contain the ``urlencode``-generated "
        f"substring byte-for-byte (cross-check). Got: "
        f"{with_special_chars!r} expected substring: {rebuilt!r}"
    )

    all_none = _runs_list_query_string(
        limit=50,
        offset=None,
        order="newest_first",
        include_summary=0,
        workflow_profile=None,
        workflow_profile_prefix=None,
        created_after=None,
        created_before=None,
        has_escalation=None,
    )
    assert all_none == "limit=50&order=newest_first&include_summary=0", (
        f"D5: all-optional-None call must equal the C1 base string "
        f"exactly. A refactor that omitted the ``is not None`` checks and "
        f"unconditionally appended ``(key, str(value))`` would produce "
        f"entries like ``workflow_profile=None`` that clients would "
        f"misinterpret as the literal filter value ``None``. Got: "
        f"{all_none!r}"
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
        assert forbidden not in all_none, (
            f"D5: forbidden substring {forbidden!r} found in all-None "
            f"output ``{all_none!r}``; pins that excluded fields produce "
            f"no key=value entry at all"
        )
