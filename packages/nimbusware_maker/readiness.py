from __future__ import annotations

import ctypes
import shutil
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

from hermes_store.memory import InMemoryEventStore
from nimbusware_env.edition import edition_manifest
from nimbusware_env.env_flags import hermes_skip_preflight_enabled

INSTALL_GUIDE = "python scripts/install_nimbusware.py  (see README Quick start)"


def _load_model_routing(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs" / "model-routing.yaml"
    if not path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _primary_model_id(models: dict[str, Any]) -> str:
    primary = models.get("primary")
    if isinstance(primary, dict):
        pid = primary.get("id")
        if isinstance(pid, str) and pid.strip():
            return pid.strip()
    if isinstance(primary, str) and primary.strip():
        return primary.strip()
    return ""


def _check_repo_root(repo_root: Path) -> dict[str, Any]:
    required = [
        repo_root / "configs" / "model-routing.yaml",
        repo_root / "configs" / "roles.yaml",
    ]
    missing = [str(p.relative_to(repo_root)) for p in required if not p.is_file()]
    if missing:
        return {
            "status": "fail",
            "message": f"Missing config files: {', '.join(missing)}",
            "repo_root": str(repo_root),
        }
    return {
        "status": "ok",
        "message": "Hermes config present",
        "repo_root": str(repo_root),
    }


def _check_database(store: Any) -> dict[str, Any]:
    if isinstance(store, InMemoryEventStore):
        return {
            "status": "degraded",
            "message": "In-memory event store (dev mode — runs are not durable)",
        }
    return {
        "status": "ok",
        "message": "PostgreSQL event store configured",
    }


def _check_ollama(repo_root: Path) -> dict[str, Any]:
    if hermes_skip_preflight_enabled():
        routing = _load_model_routing(repo_root)
        runtime = routing.get("runtime") if isinstance(routing.get("runtime"), dict) else {}
        models = routing.get("models") if isinstance(routing.get("models"), dict) else {}
        primary = _primary_model_id(models) or "unknown"
        return {
            "status": "degraded",
            "message": "Preflight skipped (HERMES_SKIP_PREFLIGHT) — model checks not run",
            "skipped": True,
            "primary_model": primary,
            "base_url": str(runtime.get("base_url") or "http://localhost:11434"),
        }

    routing = _load_model_routing(repo_root)
    runtime = routing.get("runtime") if isinstance(routing.get("runtime"), dict) else {}
    models = routing.get("models") if isinstance(routing.get("models"), dict) else {}
    base_url = str(runtime.get("base_url") or "http://localhost:11434")
    health_path = str(runtime.get("health_endpoint") or "/api/tags")
    primary = _primary_model_id(models)
    timeout = float(runtime.get("request_timeout_seconds") or 10.0)
    url = base_url.rstrip("/") + health_path

    try:
        t0 = httpx.get(url, timeout=timeout)
        t0.raise_for_status()
        data = t0.json()
    except (httpx.HTTPError, ValueError) as exc:
        out: dict[str, Any] = {
            "status": "fail",
            "message": f"Ollama not reachable at {base_url}: {exc}",
            "base_url": base_url,
            "primary_model": primary,
        }
        if primary:
            out["pull_command"] = f"ollama pull {primary}"
        return out

    names: set[str] = set()
    model_list = data.get("models") if isinstance(data, dict) else None
    if isinstance(model_list, list):
        for item in model_list:
            if isinstance(item, dict) and "name" in item:
                names.add(str(item["name"]))
            elif isinstance(item, str):
                names.add(item)

    if primary and names and primary not in names:
        return {
            "status": "degraded",
            "message": f"Primary model {primary!r} not loaded — pull it or pick a smaller preset",
            "base_url": base_url,
            "primary_model": primary,
            "loaded_models": sorted(names)[:12],
            "pull_command": f"ollama pull {primary}",
        }

    return {
        "status": "ok",
        "message": "Ollama reachable" + (f" — primary model {primary!r} loaded" if primary else ""),
        "base_url": base_url,
        "primary_model": primary,
        "loaded_models": sorted(names)[:12] if names else [],
    }


def _available_memory_gb() -> float | None:
    if sys.platform == "win32":
        try:

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return stat.ullAvailPhys / (1024**3)
        except (AttributeError, OSError, TypeError):
            return None
    elif sys.platform.startswith("linux"):
        try:
            meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
        except OSError:
            return None
        for line in meminfo.splitlines():
            if line.startswith("MemAvailable:"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) / (1024**2)
    return None


def _check_memory() -> dict[str, Any]:
    avail = _available_memory_gb()
    if avail is None:
        return {
            "status": "degraded",
            "message": "RAM check unavailable on this platform",
        }
    if avail < 4.0:
        return {
            "status": "fail",
            "message": f"Low available RAM ({avail:.1f} GB) — try the Fast preset",
            "available_gb": round(avail, 2),
        }
    if avail < 8.0:
        return {
            "status": "degraded",
            "message": f"Tight RAM ({avail:.1f} GB) — Fast preset recommended",
            "available_gb": round(avail, 2),
        }
    return {
        "status": "ok",
        "message": f"{avail:.1f} GB RAM available",
        "available_gb": round(avail, 2),
    }


def _check_disk(repo_root: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(repo_root)
    free_gb = usage.free / (1024**3)
    if free_gb < 1.0:
        return {
            "status": "fail",
            "message": f"Low disk space ({free_gb:.1f} GB free)",
            "free_gb": round(free_gb, 2),
        }
    if free_gb < 5.0:
        return {
            "status": "degraded",
            "message": f"Disk space is tight ({free_gb:.1f} GB free)",
            "free_gb": round(free_gb, 2),
        }
    return {
        "status": "ok",
        "message": f"{free_gb:.1f} GB free on workspace disk",
        "free_gb": round(free_gb, 2),
    }


def _overall_status(checks: dict[str, dict[str, Any]]) -> str:
    statuses = {c.get("status") for c in checks.values()}
    if "fail" in statuses:
        return "not_ready"
    if "degraded" in statuses:
        return "degraded"
    return "ready"


def build_platform_readiness(*, repo_root: Path, store: Any) -> dict[str, Any]:
    checks = {
        "database": _check_database(store),
        "repo_root": _check_repo_root(repo_root),
        "memory": _check_memory(),
        "ollama": _check_ollama(repo_root),
        "disk": _check_disk(repo_root),
    }
    manifest = edition_manifest()
    overall = _overall_status(checks)
    body: dict[str, Any] = {
        "status": overall,
        "checks": checks,
        "edition": manifest.get("edition"),
        "presets": {
            "fast": {
                "label": "Fast prototype",
                "hint": "Smaller model, fewer slices — good for weak hardware",
            },
            "careful": {
                "label": "Careful",
                "hint": "Primary model with full micro-slice gates",
            },
        },
    }
    if overall == "not_ready":
        body["install_guide"] = INSTALL_GUIDE
    return body
