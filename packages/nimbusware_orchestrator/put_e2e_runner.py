"""PUT E2E flow runner — fo670–fo674 Playwright/HTTP flows against preview base_url."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml

from nimbusware_env import find_repo_root

PutE2EVerdict = Literal["PASS", "FAIL", "SKIP"]


@dataclass(frozen=True)
class PutE2EFinding:
    kind: str
    message: str
    surface_path: str | None = None
    severity: str = "operational"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "message": self.message,
            "severity": self.severity,
        }
        if self.surface_path:
            payload["surface_path"] = self.surface_path
        return payload


@dataclass
class PutE2EResult:
    verdict: PutE2EVerdict
    flow_id: str
    base_url: str
    detail: str = ""
    exit_code: int | None = None
    exercised_paths: set[str] = field(default_factory=set)
    findings: list[PutE2EFinding] = field(default_factory=list)
    capture: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool | None:
        if self.verdict == "PASS":
            return True
        if self.verdict == "FAIL":
            return False
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "flow_id": self.flow_id,
            "base_url": self.base_url,
            "detail": self.detail,
            "exit_code": self.exit_code,
            "exercised_paths": sorted(self.exercised_paths),
            "findings": [f.to_dict() for f in self.findings],
            "capture": self.capture,
            "passed": self.passed,
        }


def factory_flows_root(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "factory" / "flows"


def load_factory_flow_catalog(repo_root: Path | None = None) -> dict[str, Any]:
    path = factory_flows_root(repo_root) / "catalog.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_factory_flow_ids(repo_root: Path | None = None) -> tuple[str, ...]:
    doc = load_factory_flow_catalog(repo_root)
    return tuple(str(entry["id"]) for entry in doc.get("flows") or [] if entry.get("id"))


def load_factory_flow(flow_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    root = factory_flows_root(repo_root)
    catalog = load_factory_flow_catalog(repo_root)
    rel = ""
    for entry in catalog.get("flows") or []:
        if str(entry.get("id") or "").strip() == flow_id:
            rel = str(entry.get("path") or "").strip()
            break
    if not rel:
        raise KeyError(f"unknown factory flow id: {flow_id}")
    path = root / rel
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("id"):
        data["id"] = flow_id
    return data


def match_factory_flow_id(
    business_prompt: str,
    *,
    prompt_id: str | None = None,
    repo_root: Path | None = None,
) -> str | None:
    if prompt_id:
        catalog = load_factory_flow_catalog(repo_root)
        for entry in catalog.get("flows") or []:
            if str(entry.get("prompt_id") or "") == prompt_id:
                return str(entry.get("id") or "") or None
    text = business_prompt.strip().lower()
    if not text:
        return None
    for fid in list_factory_flow_ids(repo_root):
        if fid.replace("_", " ") in text or fid in text:
            return fid
    return None


def _playwright_available() -> bool:
    return shutil.which("playwright") is not None or shutil.which("npx") is not None


def _playwright_module_ready() -> tuple[bool, str]:
    if not _playwright_available():
        return False, "playwright CLI not on PATH"
    probe = subprocess.run(
        ["python", "-m", "playwright", "--version"],
        capture_output=True,
        text=True,
        timeout=30.0,
        check=False,
    )
    if probe.returncode != 0:
        return False, (probe.stderr or probe.stdout or "playwright module not installed")[:500]
    return True, (probe.stdout or probe.stderr or "ok").strip()


def stub_console_capture(*, enabled: bool) -> list[PutE2EFinding]:
    """Stub console capture — returns operational findings list."""
    if not enabled:
        return []
    return [
        PutE2EFinding(
            kind="console",
            message="console capture stub (no browser session)",
            severity="info",
        ),
    ]


def stub_network_capture(
    *,
    enabled: bool,
    exercised_paths: set[str],
) -> list[PutE2EFinding]:
    """Stub network capture — summarizes exercised HTTP paths."""
    if not enabled:
        return []
    findings: list[PutE2EFinding] = []
    for path in sorted(exercised_paths):
        findings.append(
            PutE2EFinding(
                kind="network",
                message=f"request observed: {path}",
                surface_path=path,
                severity="info",
            ),
        )
    if not findings:
        findings.append(
            PutE2EFinding(
                kind="network",
                message="network capture stub (no requests recorded)",
                severity="info",
            ),
        )
    return findings


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path if path.startswith('/') else '/' + path}"


def _run_http_step(
    client: httpx.Client,
    base_url: str,
    step: dict[str, Any],
    *,
    exercised: set[str],
    findings: list[PutE2EFinding],
) -> bool:
    action = str(step.get("action") or "").strip().lower()
    path = str(step.get("path") or "/")
    exercised.add(path)

    if action == "goto":
        try:
            resp = client.get(_url(base_url, path), follow_redirects=True)
        except httpx.HTTPError as exc:
            findings.append(
                PutE2EFinding(kind="step_fail", message=f"goto {path}: {exc}", surface_path=path),
            )
            return False
        if resp.status_code >= 500:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"goto {path}: status {resp.status_code}",
                    surface_path=path,
                ),
            )
            return False
        return True

    if action == "expect_status":
        expected = int(step.get("status") or 200)
        try:
            resp = client.get(_url(base_url, path), follow_redirects=True)
        except httpx.HTTPError as exc:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"expect_status {path}: {exc}",
                    surface_path=path,
                ),
            )
            return False
        if resp.status_code != expected:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"expect_status {path}: got {resp.status_code}, want {expected}",
                    surface_path=path,
                ),
            )
            return False
        return True

    if action == "api_check":
        method = str(step.get("method") or "GET").upper()
        expected = int(step.get("status") or 200)
        body = step.get("json_body")
        try:
            resp = client.request(
                method,
                _url(base_url, path),
                json=body if isinstance(body, dict) else None,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"api_check {method} {path}: {exc}",
                    surface_path=path,
                ),
            )
            return False
        if resp.status_code != expected:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"api_check {method} {path}: got {resp.status_code}, want {expected}",
                    surface_path=path,
                ),
            )
            return False
        keys = step.get("expect_json_keys")
        if isinstance(keys, list) and keys:
            try:
                payload = resp.json()
            except (json.JSONDecodeError, ValueError):
                findings.append(
                    PutE2EFinding(
                        kind="step_fail",
                        message=f"api_check {path}: response is not JSON",
                        surface_path=path,
                    ),
                )
                return False
            if not isinstance(payload, dict):
                findings.append(
                    PutE2EFinding(
                        kind="step_fail",
                        message=f"api_check {path}: JSON root is not object",
                        surface_path=path,
                    ),
                )
                return False
            missing = [k for k in keys if k not in payload]
            if missing:
                findings.append(
                    PutE2EFinding(
                        kind="step_fail",
                        message=f"api_check {path}: missing keys {missing}",
                        surface_path=path,
                    ),
                )
                return False
        return True

    findings.append(PutE2EFinding(kind="step_skip", message=f"unknown action: {action}"))
    return True


def run_put_e2e_flow(
    base_url: str,
    flow_id: str,
    *,
    repo_root: Path | None = None,
    timeout_seconds: float = 60.0,
    require_playwright: bool = False,
) -> PutE2EResult:
    """Execute a factory flow template against ``base_url``.

    Uses HTTP step runner; skips when ``require_playwright`` and Playwright is absent.
    """
    try:
        flow = load_factory_flow(flow_id, repo_root=repo_root)
    except (KeyError, OSError, yaml.YAMLError) as exc:
        return PutE2EResult(
            verdict="FAIL",
            flow_id=flow_id,
            base_url=base_url,
            detail=str(exc),
        )

    pw_ready, pw_detail = _playwright_module_ready()
    if require_playwright and not pw_ready:
        return PutE2EResult(
            verdict="SKIP",
            flow_id=flow_id,
            base_url=base_url,
            detail=pw_detail,
        )

    capture_cfg = flow.get("capture") if isinstance(flow.get("capture"), dict) else {}
    console_on = bool(capture_cfg.get("console", False))
    network_on = bool(capture_cfg.get("network", False))

    exercised: set[str] = set()
    findings: list[PutE2EFinding] = []
    steps = flow.get("steps") if isinstance(flow.get("steps"), list) else []

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if not _run_http_step(
                    client, base_url, step, exercised=exercised, findings=findings
                ):
                    capture = {
                        "console": [f.to_dict() for f in stub_console_capture(enabled=console_on)],
                        "network": [
                            f.to_dict()
                            for f in stub_network_capture(
                                enabled=network_on, exercised_paths=exercised
                            )
                        ],
                    }
                    detail = findings[-1].message if findings else "flow step failed"
                    return PutE2EResult(
                        verdict="FAIL",
                        flow_id=flow_id,
                        base_url=base_url,
                        detail=detail,
                        exercised_paths=exercised,
                        findings=findings,
                        capture=capture,
                    )
    except httpx.HTTPError as exc:
        return PutE2EResult(
            verdict="FAIL",
            flow_id=flow_id,
            base_url=base_url,
            detail=str(exc),
            exercised_paths=exercised,
            findings=findings,
        )

    findings.extend(stub_console_capture(enabled=console_on))
    findings.extend(stub_network_capture(enabled=network_on, exercised_paths=exercised))
    capture = {
        "console": [f.to_dict() for f in findings if f.kind == "console"],
        "network": [f.to_dict() for f in findings if f.kind == "network"],
        "playwright_ready": pw_ready,
        "playwright_detail": pw_detail,
    }
    return PutE2EResult(
        verdict="PASS",
        flow_id=flow_id,
        base_url=base_url,
        detail="all flow steps passed",
        exercised_paths=exercised,
        findings=findings,
        capture=capture,
    )
