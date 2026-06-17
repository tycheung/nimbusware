from __future__ import annotations

import ctypes
import shutil
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env.edition import edition_manifest
from nimbusware_env.env_flags import env_str, nimbusware_skip_preflight_enabled
from nimbusware_store.memory import InMemoryEventStore

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
            "action": "install_guide",
            "action_label": "View install guide",
        }
    return {
        "status": "ok",
        "message": "Nimbusware config present",
        "repo_root": str(repo_root),
    }


def _check_database(store: Any) -> dict[str, Any]:
    if isinstance(store, InMemoryEventStore):
        return {
            "status": "degraded",
            "message": "In-memory event store (dev mode — runs are not durable)",
            "action": "quick_mode",
            "action_label": "Use quick mode",
        }
    return {
        "status": "ok",
        "message": "PostgreSQL event store configured",
    }


def _ollama_routing_sections(
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    routing = _load_model_routing(repo_root)
    return mapping_or_empty(routing.get("runtime")), mapping_or_empty(routing.get("models"))


def _check_ollama(repo_root: Path) -> dict[str, Any]:
    runtime, models = _ollama_routing_sections(repo_root)
    if nimbusware_skip_preflight_enabled():
        primary = _primary_model_id(models) or "unknown"
        return {
            "status": "degraded",
            "message": "Preflight skipped (NIMBUSWARE_SKIP_PREFLIGHT) — model checks not run",
            "skipped": True,
            "primary_model": primary,
            "base_url": str(runtime.get("base_url") or "http://localhost:11434"),
        }
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
        out["action"] = "model_hub_local"
        out["action_label"] = "Open Model Hub"
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
            "action": "model_hub_local",
            "action_label": f"Pull {primary} in Model Hub",
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
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return float(stat.ullAvailPhys / (1024**3))
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


def _tier_memory_message(tier: str, avail: float) -> str:
    if tier == "weak":
        return f"Low-tier machine ({avail:.1f} GB free) — use quick_local or Fast preset"
    if tier == "medium":
        return f"Medium tier ({avail:.1f} GB free) — micro_slice recommended"
    return f"Strong tier ({avail:.1f} GB free) — full production profile OK"


def _check_memory() -> dict[str, Any]:
    try:
        from nimbusware_hw.cache import get_cached_profile

        profile = get_cached_profile()
        avail = profile.ram_available_gb
        tier = profile.tier
    except ImportError:
        avail = _available_memory_gb()
        tier = "medium" if (avail or 0) >= 8 else "weak"
    if avail is None:
        return {
            "status": "degraded",
            "message": "RAM check unavailable on this platform",
        }
    if avail < 4.0:
        return {
            "status": "fail",
            "message": _tier_memory_message("weak", avail),
            "available_gb": round(avail, 2),
            "hardware_tier": tier,
        }
    if tier == "weak" or avail < 8.0:
        return {
            "status": "degraded",
            "message": _tier_memory_message(tier, avail),
            "available_gb": round(avail, 2),
            "hardware_tier": tier,
        }
    return {
        "status": "ok",
        "message": _tier_memory_message(tier, avail),
        "available_gb": round(avail, 2),
        "hardware_tier": tier,
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


def _check_model_bindings(repo_root: Path) -> dict[str, Any]:
    from nimbusware_orchestrator.binding_preflight import (
        build_binding_preflight_report,
        cloud_only_roles_satisfied,
    )

    try:
        report = build_binding_preflight_report(repo_root, work_type="patch", probe=True)
    except OSError as exc:
        return {
            "status": "degraded",
            "message": f"Binding preflight unavailable: {exc}",
        }
    missing = report.get("roles_without_provider") or []
    mode = str(report.get("inference_mode") or "degraded")
    label = str(report.get("inference_mode_label") or mode)
    if missing:
        status = "degraded" if cloud_only_roles_satisfied(report) else "fail"
        msg = f"{len(missing)} role(s) lack reachable providers: {', '.join(missing[:6])}"
    else:
        status = "ok"
        msg = label
    return {
        "status": status,
        "message": msg,
        "inference_mode": mode,
        "inference_mode_label": label,
        "roles_covered": report.get("roles_covered"),
        "roles_total": report.get("roles_total"),
        "roles_without_provider": missing,
        "providers_reachable": report.get("providers_reachable"),
        "ollama_required": report.get("ollama_required"),
    }


def _overall_status(checks: dict[str, dict[str, Any]]) -> str:
    statuses = {c.get("status") for c in checks.values()}
    if "fail" in statuses:
        return "not_ready"
    if "degraded" in statuses:
        return "degraded"
    return "ready"


def _check_campaign_backlog(repo_root: Path) -> dict[str, Any]:
    from nimbusware_orchestrator.backlog_generator import effective_backlog_generator_mode

    mode, reason = effective_backlog_generator_mode("stub")
    if mode == "llm":
        return {
            "status": "ok",
            "message": "Campaign backlog will use LLM generator",
            "generator_mode": "llm",
        }
    body: dict[str, Any] = {
        "status": "degraded" if reason else "ok",
        "message": reason or "Campaign backlog uses stub generator",
        "generator_mode": "stub",
    }
    return body


def build_platform_readiness(*, repo_root: Path, store: Any) -> dict[str, Any]:
    binding_check = _check_model_bindings(repo_root)
    checks = {
        "database": _check_database(store),
        "repo_root": _check_repo_root(repo_root),
        "memory": _check_memory(),
        "ollama": _check_ollama(repo_root),
        "model_bindings": binding_check,
        "disk": _check_disk(repo_root),
        "campaign_backlog": _check_campaign_backlog(repo_root),
    }
    ollama = checks.get("ollama") or {}
    if (
        ollama.get("status") == "fail"
        and binding_check.get("status") in {"ok", "degraded"}
        and not binding_check.get("ollama_required")
        and not binding_check.get("roles_without_provider")
    ):
        checks["ollama"] = {
            **ollama,
            "status": "degraded",
            "message": (ollama.get("message") or "Ollama down")
            + " — cloud bindings cover active roles",
            "skipped_for_cloud_only": True,
        }
    manifest = edition_manifest()
    overall = _overall_status(checks)
    install_profile = env_str("NIMBUSWARE_INSTALL_PROFILE").strip() or "recommended"
    body: dict[str, Any] = {
        "status": overall,
        "checks": checks,
        "edition": manifest.get("edition"),
        "install_profile": install_profile,
        "inference_mode": binding_check.get("inference_mode"),
        "inference_mode_label": binding_check.get("inference_mode_label"),
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
    if install_profile == "barebones" and checks.get("ollama", {}).get("status") == "fail":
        body["model_hub_cta"] = "Set up local or API LLM in Model Hub"
        body["model_hub_action"] = "setup_llm"
    return body
