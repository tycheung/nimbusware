"""Persona shelves (plan §3B, §14 #14, fo127 edit/instructions extension).

The minimal on-disk shape is ``{id, display_name}`` per entry (plan §14 #14). fo127 adds
seven OPTIONAL additive fields per entry so operators can author per-persona
instructions / capability profile / boundary statement / allowed tools /
success metrics / probation status — plus a monotonic ``version`` for
optimistic-concurrency on the new write API:

    - ``instructions``       str  (≤ 8000 chars, NFC-normalized)
    - ``capability_profile`` str  (≤ 2000)
    - ``boundary_statement`` str  (≤ 2000)
    - ``allowed_tools``      list[str]  (≤ 50 entries; each ≤ 100 chars)
    - ``success_metrics``    list[str]  (≤ 20 entries; each ≤ 200 chars)
    - ``probation_status``   Literal["probation", "promoted", "shelved"]
    - ``version``            int (≥ 1, default 1 when absent)

All new fields are OPTIONAL on disk so minimal ``shelves.yaml`` entries keep
loading unchanged.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from hermes_orchestrator.merge import load_yaml

ALLOWED_SHELVES: tuple[str, ...] = ("business_area", "development_role")
ALLOWED_PROBATION_STATUSES: tuple[str, ...] = ("probation", "promoted", "shelved")

PERSONA_INSTRUCTIONS_MAX_CHARS = 8000
PERSONA_CAPABILITY_PROFILE_MAX_CHARS = 2000
PERSONA_BOUNDARY_STATEMENT_MAX_CHARS = 2000
PERSONA_ALLOWED_TOOLS_MAX_ENTRIES = 50
PERSONA_ALLOWED_TOOL_MAX_CHARS = 100
PERSONA_SUCCESS_METRICS_MAX_ENTRIES = 20
PERSONA_SUCCESS_METRIC_MAX_CHARS = 200


def _validate_optional_str(
    value: Any,
    *,
    field: str,
    max_chars: int,
    where: str,
) -> str | None:
    """Return NFC-normalized string when present; raise on type / length errors."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{where}: {field!r} must be a string when present")
    normalized = unicodedata.normalize("NFC", value)
    if len(normalized) > max_chars:
        raise ValueError(
            f"{where}: {field!r} length {len(normalized)} exceeds cap of {max_chars}",
        )
    return normalized


def _validate_optional_str_list(
    value: Any,
    *,
    field: str,
    max_entries: int,
    per_entry_max_chars: int,
    where: str,
) -> list[str] | None:
    """Return NFC-normalized list of strings when present; raise on shape errors."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{where}: {field!r} must be a list of strings when present")
    if len(value) > max_entries:
        raise ValueError(
            f"{where}: {field!r} has {len(value)} entries (cap is {max_entries})",
        )
    out: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{where}: {field!r}[{i}] must be a string")
        normalized = unicodedata.normalize("NFC", item)
        if len(normalized) > per_entry_max_chars:
            raise ValueError(
                f"{where}: {field!r}[{i}] length {len(normalized)} exceeds cap "
                f"of {per_entry_max_chars}",
            )
        out.append(normalized)
    return out


def collect_persona_entry_validation_errors(
    entry: Mapping[str, Any],
    *,
    where: str = "entry",
) -> list[str]:
    """Return human-readable validation messages (empty when the entry is valid)."""
    try:
        _validate_entry_optional_fields(entry, where=where)
    except ValueError as exc:
        return [str(exc)]
    return []


def _validate_entry_optional_fields(entry: Mapping[str, Any], *, where: str) -> None:
    """Raise ``ValueError`` if any fo127 optional field has the wrong shape."""
    _validate_optional_str(
        entry.get("instructions"),
        field="instructions",
        max_chars=PERSONA_INSTRUCTIONS_MAX_CHARS,
        where=where,
    )
    _validate_optional_str(
        entry.get("capability_profile"),
        field="capability_profile",
        max_chars=PERSONA_CAPABILITY_PROFILE_MAX_CHARS,
        where=where,
    )
    _validate_optional_str(
        entry.get("boundary_statement"),
        field="boundary_statement",
        max_chars=PERSONA_BOUNDARY_STATEMENT_MAX_CHARS,
        where=where,
    )
    _validate_optional_str_list(
        entry.get("allowed_tools"),
        field="allowed_tools",
        max_entries=PERSONA_ALLOWED_TOOLS_MAX_ENTRIES,
        per_entry_max_chars=PERSONA_ALLOWED_TOOL_MAX_CHARS,
        where=where,
    )
    _validate_optional_str_list(
        entry.get("success_metrics"),
        field="success_metrics",
        max_entries=PERSONA_SUCCESS_METRICS_MAX_ENTRIES,
        per_entry_max_chars=PERSONA_SUCCESS_METRIC_MAX_CHARS,
        where=where,
    )
    ps = entry.get("probation_status")
    if ps is not None and ps not in ALLOWED_PROBATION_STATUSES:
        raise ValueError(
            f"{where}: 'probation_status' must be one of "
            f"{ALLOWED_PROBATION_STATUSES!r} when present (got {ps!r})",
        )
    ver = entry.get("version")
    if ver is not None:
        if isinstance(ver, bool) or not isinstance(ver, int):
            raise ValueError(f"{where}: 'version' must be an int when present")
        if ver < 1:
            raise ValueError(f"{where}: 'version' must be >= 1 when present (got {ver})")


def normalize_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Return a fresh dict with NFC-normalized strings + defaults populated.

    Legacy ``{id, display_name}`` entries pass through unchanged except for the
    NFC normalization on string fields. ``version`` defaults to 1 when absent.
    Caller is responsible for `validate_structure`-level invariants (e.g. id
    is non-empty); this helper assumes the input is structurally valid.
    """
    out: dict[str, Any] = {}
    for key in ("id", "display_name"):
        v = entry.get(key)
        if v is not None:
            out[key] = unicodedata.normalize("NFC", str(v))
    for str_field in ("instructions", "capability_profile", "boundary_statement"):
        v = entry.get(str_field)
        if v is not None:
            out[str_field] = unicodedata.normalize("NFC", str(v))
    for list_field in ("allowed_tools", "success_metrics"):
        v = entry.get(list_field)
        if isinstance(v, list):
            out[list_field] = [unicodedata.normalize("NFC", str(item)) for item in v]
    ps = entry.get("probation_status")
    if ps is not None:
        out["probation_status"] = str(ps)
    raw_ver = entry.get("version")
    if isinstance(raw_ver, int) and not isinstance(raw_ver, bool):
        out["version"] = int(raw_ver)
    else:
        out["version"] = 1
    return out


class PersonaShelf:
    """Business-area vs development-role shelves from YAML."""

    def __init__(self, shelves_path: Path) -> None:
        self._raw = load_yaml(shelves_path)

    @classmethod
    def from_content(cls, raw: dict[str, Any]) -> PersonaShelf:
        """Build shelf from an in-memory mapping (Postgres materialization)."""
        if not isinstance(raw, dict):
            msg = "persona shelves content must be a mapping"
            raise ValueError(msg)
        shelf = cls.__new__(cls)
        shelf._raw = raw
        return shelf

    @property
    def raw(self) -> Any:
        """Mutable backing mapping. Use ``write_entry`` / ``delete_entry`` for safe edits."""
        return self._raw

    def validate_structure(self) -> None:
        """Raise ``ValueError`` if shelves YAML is not a valid persona catalog.

        Legacy invariants (plan §14 #14): root mapping, ``business_area`` and
        ``development_role`` non-empty lists, each entry a mapping with
        non-empty string ``id``. fo127 additionally type-checks the seven new
        OPTIONAL fields when present (length caps + literal enum + version >= 1).
        """
        if not isinstance(self._raw, dict):
            raise ValueError("persona shelves: root must be a mapping")
        for rk in ALLOWED_SHELVES:
            entries = self._raw.get(rk)
            if not isinstance(entries, list) or not entries:
                raise ValueError(
                    f"persona shelves: {rk!r} must be a non-empty list of persona entries",
                )
            for i, p in enumerate(entries):
                if not isinstance(p, dict):
                    raise ValueError(f"persona shelves: {rk!r}[{i}] must be a mapping")
                pid = str(p.get("id", "")).strip()
                if not pid:
                    raise ValueError(
                        f"persona shelves: {rk!r}[{i}] must include a non-empty string id",
                    )
                _validate_entry_optional_fields(p, where=f"persona shelves: {rk!r}[{i}]")

    def list_personas(self, shelf: str) -> list[dict[str, Any]]:
        key = shelf.strip().lower()
        raw = self._raw.get(key)
        if not isinstance(raw, list):
            return []
        return [p for p in raw if isinstance(p, dict)]

    def all_persona_ids(self) -> frozenset[str]:
        """Non-empty ``id`` values from ``business_area`` + ``development_role`` shelves."""
        out: set[str] = set()
        if not isinstance(self._raw, dict):
            return frozenset()
        for rk in ALLOWED_SHELVES:
            entries = self._raw.get(rk)
            if not isinstance(entries, list):
                continue
            for p in entries:
                if isinstance(p, dict):
                    pid = str(p.get("id", "")).strip()
                    if pid:
                        out.add(pid)
        return frozenset(out)

    def find_entry(self, shelf: str, persona_id: str) -> dict[str, Any] | None:
        """Return a deep-enough copy of the entry, or ``None`` when missing."""
        for entry in self.list_personas(shelf):
            if str(entry.get("id", "")).strip() == persona_id:
                return dict(entry)
        return None

    def to_public_catalog(self) -> dict[str, Any]:
        """Read-only catalog shape for HTTP API (plan §14 #14, fo127 extended).

        Each entry surfaces every present optional field plus a ``version`` that
        defaults to 1 when absent on disk. Absent optional fields are omitted
        from the wire payload (additive forward-compat).
        """
        ver: int | None = None
        if isinstance(self._raw, dict):
            raw_v = self._raw.get("version")
            if isinstance(raw_v, int) and not isinstance(raw_v, bool):
                ver = raw_v
            elif isinstance(raw_v, float) and raw_v == int(raw_v):
                ver = int(raw_v)

        def _project(entry: dict[str, Any]) -> dict[str, Any]:
            out: dict[str, Any] = {}
            for k in ("id", "display_name"):
                if k in entry:
                    out[k] = entry[k]
            for k in (
                "instructions",
                "capability_profile",
                "boundary_statement",
                "allowed_tools",
                "success_metrics",
                "probation_status",
            ):
                if entry.get(k) is not None:
                    out[k] = entry[k]
            raw_ver = entry.get("version")
            out["version"] = (
                int(raw_ver)
                if isinstance(raw_ver, int) and not isinstance(raw_ver, bool)
                else 1
            )
            return out

        return {
            "version": ver,
            "business_area": [_project(p) for p in self.list_personas("business_area")],
            "development_role": [
                _project(p) for p in self.list_personas("development_role")
            ],
        }

    def write_entry(self, shelf: str, entry: Mapping[str, Any]) -> dict[str, Any]:
        """Upsert ``entry`` into ``shelf`` and return the resulting raw mapping.

        Caller MUST have validated ``entry`` already (e.g. via
        ``_validate_entry_optional_fields`` + non-empty ``id``). Replaces the
        existing entry with matching ``id`` in place when present (preserving
        list order) or appends to the shelf when new.
        """
        if shelf not in ALLOWED_SHELVES:
            raise ValueError(f"unknown shelf {shelf!r}; expected one of {ALLOWED_SHELVES!r}")
        pid = str(entry.get("id", "")).strip()
        if not pid:
            raise ValueError("write_entry: entry must include a non-empty string id")
        if not isinstance(self._raw, dict):
            raise ValueError("persona shelves: root must be a mapping")
        entries = self._raw.setdefault(shelf, [])
        if not isinstance(entries, list):
            raise ValueError(f"persona shelves: {shelf!r} must be a list")
        new_entry = normalize_entry(entry)
        for i, existing in enumerate(entries):
            if isinstance(existing, dict) and str(existing.get("id", "")).strip() == pid:
                entries[i] = new_entry
                return self._raw
        entries.append(new_entry)
        return self._raw

    def delete_entry(self, shelf: str, persona_id: str) -> dict[str, Any]:
        """Remove the entry with matching ``id``; raise ``KeyError`` when missing."""
        if shelf not in ALLOWED_SHELVES:
            raise ValueError(f"unknown shelf {shelf!r}; expected one of {ALLOWED_SHELVES!r}")
        if not isinstance(self._raw, dict):
            raise ValueError("persona shelves: root must be a mapping")
        entries = self._raw.get(shelf)
        if not isinstance(entries, list):
            raise KeyError(f"{shelf}/{persona_id}")
        for i, existing in enumerate(entries):
            if isinstance(existing, dict) and str(existing.get("id", "")).strip() == persona_id:
                entries.pop(i)
                return self._raw
        raise KeyError(f"{shelf}/{persona_id}")
