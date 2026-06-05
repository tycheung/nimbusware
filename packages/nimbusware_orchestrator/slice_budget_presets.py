from __future__ import annotations

from dataclasses import dataclass

PRESET_NAMES = frozenset({"tiny", "standard", "careful"})


@dataclass(frozen=True)
class SliceBudgetPreset:
    name: str
    max_files: int
    max_loc: int
    replan_max: int


_PRESETS: dict[str, SliceBudgetPreset] = {
    "tiny": SliceBudgetPreset("tiny", max_files=1, max_loc=40, replan_max=1),
    "standard": SliceBudgetPreset("standard", max_files=3, max_loc=120, replan_max=3),
    "careful": SliceBudgetPreset("careful", max_files=2, max_loc=80, replan_max=5),
}


def normalize_preset_name(raw: str | None) -> str:
    name = (raw or "standard").strip().lower()
    if name not in PRESET_NAMES:
        return "standard"
    return name


def slice_budget_preset(name: str | None) -> SliceBudgetPreset:
    return _PRESETS[normalize_preset_name(name)]


def resolve_slice_budget_preset(
    *,
    operator_settings: dict[str, str] | None = None,
) -> SliceBudgetPreset:
    from nimbusware_env.settings_resolve import resolve_str

    raw = None
    if operator_settings:
        raw = operator_settings.get("NIMBUSWARE_SLICE_BUDGET_PRESET")
    if not raw:
        raw = resolve_str("NIMBUSWARE_SLICE_BUDGET_PRESET", default="standard")
    return slice_budget_preset(raw)
