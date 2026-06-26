from __future__ import annotations


def is_strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def as_int(value: object) -> int | None:
    return value if is_strict_int(value) else None


def as_float(value: object) -> float | None:
    return float(value) if is_number(value) else None


def as_stripped_str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
