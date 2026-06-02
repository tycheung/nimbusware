from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hermes_extensions.personas import collect_persona_entry_validation_errors

EDITABLE_FIELDS: tuple[str, ...] = (
    "display_name",
    "instructions",
    "capability_profile",
    "boundary_statement",
    "allowed_tools",
    "success_metrics",
    "probation_status",
)


def persona_editor_validation_issues(
    edited: Mapping[str, Any],
    *,
    require_non_empty_id: bool = False,
) -> list[str]:
    issues: list[str] = []
    if require_non_empty_id:
        raw_id = edited.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            issues.append("id: must be non-empty before Create (POST).")
    entry: dict[str, Any] = {}
    for key in ("id", *EDITABLE_FIELDS):
        if key in edited:
            entry[key] = edited[key]
    issues.extend(collect_persona_entry_validation_errors(entry, where="persona editor"))
    return issues


def persona_editor_validation_table_rows(
    issues: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for msg in issues:
        rows.append({"field": "validation", "message": msg})
    return rows


def persona_editor_validation_blocking_caption(
    issues: list[str] | None,
) -> str | None:
    if not issues:
        return None
    n = len(issues)
    word = "issue" if n == 1 else "issues"
    return f"Persona editor: fix **{n}** validation {word} before Save / Replace / Create."


def persona_list_field_line_counts_caption(
    allowed_tools_raw: object,
    success_metrics_raw: object,
) -> str | None:
    def _nonblank_lines(raw: object) -> int:
        if not isinstance(raw, str):
            return 0
        return sum(1 for ln in raw.splitlines() if ln.strip())

    at = _nonblank_lines(allowed_tools_raw)
    sm = _nonblank_lines(success_metrics_raw)
    if at == 0 and sm == 0:
        return None
    return f"List fields (non-blank lines): allowed_tools={at}, success_metrics={sm}."


def persona_editor_selected_shelf_caption(shelf: str | None) -> str | None:
    if not isinstance(shelf, str):
        return None
    text = shelf.strip()
    if not text:
        return None
    return f"Persona editor: shelf=**{text}**."


def persona_editor_display_name_draft_caption(
    display_name_raw: object,
) -> str | None:
    m = persona_field_metrics(display_name_raw)
    if not m["non_empty"]:
        return None
    return f"display_name draft: **{m['char_len']}** char(s), **{m['utf8_bytes']}** UTF-8 byte(s)."


def persona_editor_instructions_metrics_caption(
    instructions_raw: object,
) -> str | None:
    m = persona_field_metrics(instructions_raw)
    if not m["non_empty"]:
        return None
    return (
        "instructions draft (non-whitespace): "
        f"{m['char_len']} char(s), {m['utf8_bytes']} UTF-8 byte(s), "
        f"{m['line_count']} line(s)."
    )


def persona_editor_multiline_field_metrics_caption(
    capability_profile_raw: object,
    boundary_statement_raw: object,
) -> str | None:
    cp = persona_field_metrics(capability_profile_raw)
    bs = persona_field_metrics(boundary_statement_raw)
    parts: list[str] = []
    if cp["non_empty"]:
        parts.append(
            f"capability_profile: {cp['char_len']} char(s), {cp['line_count']} line(s)",
        )
    if bs["non_empty"]:
        parts.append(
            f"boundary_statement: {bs['char_len']} char(s), {bs['line_count']} line(s)",
        )
    if not parts:
        return None
    return "Multiline fields (non-whitespace): " + "; ".join(parts) + "."


def persona_field_metrics(value: object) -> dict[str, Any]:
    if not isinstance(value, str):
        return {
            "non_empty": False,
            "char_len": 0,
            "utf8_bytes": 0,
            "line_count": 0,
        }
    stripped = value.strip()
    if not stripped:
        return {
            "non_empty": False,
            "char_len": 0,
            "utf8_bytes": 0,
            "line_count": 0,
        }
    raw = stripped.encode("utf-8")
    return {
        "non_empty": True,
        "char_len": len(stripped),
        "utf8_bytes": len(raw),
        "line_count": len(stripped.splitlines()),
    }


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value == "":
        return None
    if isinstance(value, list) and not value:
        return None
    return value


def build_patch_request(
    snapshot: Mapping[str, Any],
    edited: Mapping[str, Any],
    *,
    actor: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"expected_version": int(snapshot.get("version", 1) or 1)}
    if actor:
        payload["actor"] = actor
    for field in EDITABLE_FIELDS:
        if field not in edited:
            continue
        before = _normalize_value(snapshot.get(field))
        after = _normalize_value(edited.get(field))
        if before != after:
            payload[field] = edited[field]
    return payload


_DIFF_SUMMARY_FIELD_CAP = 6

_CANONICAL_PROBATION_STATUSES = frozenset({"probation", "promoted", "shelved"})


def persona_editor_probation_status_draft_caption(
    probation_status_raw: object,
) -> str | None:
    if not isinstance(probation_status_raw, str):
        return None
    text = probation_status_raw.strip()
    if not text:
        return None
    return f"probation_status draft: **{text}**."


def persona_editor_probation_status_caption(
    snapshot: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(snapshot, Mapping):
        return None
    raw = snapshot.get("probation_status")
    if not isinstance(raw, str):
        return None
    status = raw.strip()
    if status not in _CANONICAL_PROBATION_STATUSES:
        return None
    return f"Persona editor: probation_status=**{status}** (catalog row)."


def persona_editor_expected_version_caption(
    snapshot: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(snapshot, Mapping):
        return None
    ver = snapshot.get("version")
    if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
        return None
    return f"Persona editor: saves use expected_version=**{ver}** (catalog version {ver})."


def persona_editor_diff_summary_caption(
    snapshot: Mapping[str, Any],
    edited: Mapping[str, Any],
) -> str | None:
    changed: list[str] = []
    for field in EDITABLE_FIELDS:
        if field not in edited:
            continue
        before = _normalize_value(snapshot.get(field))
        after = _normalize_value(edited.get(field))
        if before != after:
            changed.append(field)
    if not changed:
        return None
    ordered = sorted(changed)
    n = len(ordered)
    if n <= _DIFF_SUMMARY_FIELD_CAP:
        names = ", ".join(ordered)
    else:
        head = ordered[:_DIFF_SUMMARY_FIELD_CAP]
        rest = n - _DIFF_SUMMARY_FIELD_CAP
        names = ", ".join(head) + f", +{rest} more"
    suffix = "field" if n == 1 else "fields"
    return f"Persona editor: {n} {suffix} changed ({names})."


def diff_summary(
    snapshot: Mapping[str, Any],
    edited: Mapping[str, Any],
) -> list[str]:
    out: list[str] = []
    for field in EDITABLE_FIELDS:
        before = _normalize_value(snapshot.get(field))
        after = _normalize_value(edited.get(field))
        if before == after:
            continue
        out.append(f"{field}: {before!r} -> {after!r}")
    return out


def parse_write_response(
    status_code: int,
    body: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if 200 <= status_code < 300:
        return {"ok": True, "catalog": dict(body or {})}
    detail = (body or {}).get("detail") or {}
    code = str(detail.get("code") or "error")
    message = str(detail.get("message") or "unknown error")
    return {
        "ok": False,
        "status": status_code,
        "code": code,
        "message": message,
        "version_conflict": status_code == 409 and code == "persona_version_conflict",
        "details": detail.get("details"),
    }


def find_persona_in_catalog(
    catalog: Mapping[str, Any] | None,
    shelf: str,
    persona_id: str,
) -> dict[str, Any] | None:
    if not catalog:
        return None
    entries = catalog.get(shelf)
    if not isinstance(entries, list):
        return None
    for e in entries:
        if isinstance(e, dict) and str(e.get("id", "")).strip() == persona_id:
            return dict(e)
    return None
