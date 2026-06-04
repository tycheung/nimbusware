"""Normalize, validate, and merge hardware model catalog documents."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_CATALOG_MODELS = 500


def _coerce_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return default
    return default


def normalize_model_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Map Odysseus/hf_models-style rows to catalog schema."""
    if not isinstance(raw, dict):
        return None
    model_id = (
        str(raw.get("id") or raw.get("model_id") or raw.get("name") or raw.get("ollama_tag") or "")
        .strip()
    )
    if not model_id:
        return None
    params_b = _coerce_float(
        raw.get("params_b") or raw.get("params") or raw.get("parameters_b") or raw.get("size_b"),
        0.0,
    )
    if params_b <= 0 and isinstance(raw.get("params_billions"), (int, float)):
        params_b = float(raw["params_billions"])
    if params_b <= 0:
        low = model_id.lower()
        for suffix, val in (("70b", 70.0), ("34b", 34.0), ("14b", 14.0), ("13b", 13.0), ("8b", 8.0), ("7b", 7.0), ("3b", 3.0)):
            if suffix in low:
                params_b = val
                break
    if params_b <= 0:
        params_b = 4.0
    context = _coerce_int(
        raw.get("context") or raw.get("context_length") or raw.get("ctx") or raw.get("max_context"),
        8192,
    )
    out: dict[str, Any] = {
        "id": model_id,
        "params_b": params_b,
        "context": max(512, context),
    }
    if raw.get("moe") is not None:
        out["moe"] = bool(raw.get("moe"))
    tags = raw.get("quant_tags") or raw.get("tags")
    if isinstance(tags, list):
        out["quant_tags"] = [str(t) for t in tags[:20]]
    return out


def validate_catalog(doc: dict[str, Any]) -> list[str]:
    """Return validation errors; empty list means valid."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["catalog must be a JSON object"]
    version = doc.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("version must be a positive integer")
    models = doc.get("models")
    if not isinstance(models, list) or not models:
        errors.append("models must be a non-empty array")
        return errors
    if len(models) > MAX_CATALOG_MODELS:
        errors.append(f"models exceeds max {MAX_CATALOG_MODELS}")
    seen: set[str] = set()
    for i, row in enumerate(models):
        if not isinstance(row, dict):
            errors.append(f"models[{i}] must be an object")
            continue
        mid = str(row.get("id") or "").strip()
        if not mid:
            errors.append(f"models[{i}] missing id")
            continue
        if mid in seen:
            errors.append(f"duplicate model id: {mid}")
        seen.add(mid)
        params_b = row.get("params_b")
        if not isinstance(params_b, (int, float)) or float(params_b) <= 0:
            errors.append(f"models[{i}] params_b must be positive")
        context = row.get("context")
        if not isinstance(context, int) or context < 512:
            errors.append(f"models[{i}] context must be int >= 512")
    return errors


def merge_catalog(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    """Merge by model id; incoming rows override existing with same id."""
    base_models: list[dict[str, Any]] = []
    if isinstance(existing, dict):
        raw = existing.get("models")
        if isinstance(raw, list):
            base_models = [dict(m) for m in raw if isinstance(m, dict)]
    by_id: dict[str, dict[str, Any]] = {str(m["id"]): m for m in base_models if m.get("id")}
    inc_models = incoming.get("models")
    if isinstance(inc_models, list):
        for row in inc_models:
            if isinstance(row, dict) and row.get("id"):
                by_id[str(row["id"])] = dict(row)
    merged = sorted(by_id.values(), key=lambda r: str(r.get("id", "")))
    version = int(incoming.get("version") or (existing or {}).get("version") or 1)
    return {"version": version, "models": merged}


def load_catalog_doc(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    import json

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def catalog_info_from_path(path: Path, *, source: str = "bundled") -> dict[str, Any]:
    doc = load_catalog_doc(path)
    models = doc.get("models") if isinstance(doc, dict) else []
    count = len(models) if isinstance(models, list) else 0
    version = int(doc.get("version") or 1) if isinstance(doc, dict) else 1
    mtime = path.stat().st_mtime if path.is_file() else 0.0
    updated_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat() if mtime else None
    return {
        "version": version,
        "model_count": count,
        "path": str(path),
        "updated_at": updated_at,
        "source": source,
    }


def build_catalog_from_source(
    raw_doc: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
    merge: bool = False,
) -> dict[str, Any]:
    """Normalize source document (models array or top-level list) into catalog."""
    rows_raw: list[Any] = []
    if isinstance(raw_doc.get("models"), list):
        rows_raw = raw_doc["models"]
    elif isinstance(raw_doc, list):
        rows_raw = raw_doc
    normalized: list[dict[str, Any]] = []
    for raw in rows_raw:
        if isinstance(raw, dict):
            row = normalize_model_row(raw)
            if row:
                normalized.append(row)
    incoming = {
        "version": int(raw_doc.get("version") or 1) if isinstance(raw_doc, dict) else 1,
        "models": normalized,
    }
    if merge and existing:
        return merge_catalog(existing, incoming)
    return incoming
