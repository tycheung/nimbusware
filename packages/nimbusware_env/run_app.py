from __future__ import annotations

import argparse
import atexit
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from nimbusware_env.admin_token import (
    require_non_default_admin_token_for_host,
    using_default_admin_token,
)
from nimbusware_env.desktop_common import (
    pick_webview_gui,
    repo_root,
    resolve_python_command,
    run_log_path,
    subprocess_spawn_kwargs,
    terminate_process,
)
from nimbusware_env.dotenv import load_dotenv
from nimbusware_env.linux_desktop_deps import ensure_linux_desktop_deps, linux_desktop_manual_hint
from nimbusware_maker.quick_mode import apply_quick_mode_env

_PROCS: list[subprocess.Popen[object]] = []


def _pick_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "timeout"
    while time.monotonic() < deadline:
        for proc in _PROCS:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"Process exited before {url} was ready (code {proc.returncode})",
                )
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if 200 <= resp.status < 500:
                    return
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return
            last_error = str(exc)
        except OSError as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {url}: {last_error}")


def _terminate_procs() -> None:
    for proc in reversed(_PROCS):
        terminate_process(proc)
    deadline = time.monotonic() + 8.0
    for proc in reversed(_PROCS):
        if proc.poll() is not None:
            continue
        if time.monotonic() > deadline:
            proc.kill()
        else:
            try:
                proc.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.kill()


def _spawn(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.Popen[object]:
    kwargs = subprocess_spawn_kwargs(detach=sys.platform != "win32", hide_window=True)
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, **kwargs)  # noqa: S603
    _PROCS.append(proc)
    return proc


def _ui_backend() -> str:
    from nimbusware_env.env_flags import env_str

    return env_str("NIMBUSWARE_UI_BACKEND", default="web").strip().lower()


def _web_console_url(*, api_host: str, api_port: int, ui_mode: str) -> str:
    if ui_mode == "admin":
        return f"http://{api_host}:{api_port}/v1/admin/app/"
    return f"http://{api_host}:{api_port}/v1/maker/app/"


def _resolve_ui_mode(*, ui: str | None = None) -> str:
    raw = (ui or os.environ.get("NIMBUSWARE_UI", "maker")).strip().lower()
    if raw in ("console", "operator", "admin"):
        return "admin"
    return "maker"


def _reject_legacy_streamlit_backend() -> None:
    if _ui_backend() == "streamlit":
        raise RuntimeError(
            "NIMBUSWARE_UI_BACKEND=streamlit is no longer supported. "
            "Use web (default) and open /v1/maker/app/ or /v1/admin/app/ from the API.",
        )


def start_servers(
    *,
    root: Path,
    api_host: str = "127.0.0.1",
    streamlit_host: str = "127.0.0.1",
    api_port: int | None = None,
    streamlit_port: int | None = None,
    ui_mode: str | None = None,
    quick_mode: bool = False,
) -> tuple[str, str, dict[str, str]]:
    load_dotenv(repo_root=root)
    os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(root))
    _reject_legacy_streamlit_backend()
    if quick_mode:
        apply_quick_mode_env()

    require_non_default_admin_token_for_host(api_host)

    mode = _resolve_ui_mode(ui=ui_mode)
    os.environ["NIMBUSWARE_UI"] = mode

    if api_port is None:
        env_port = os.environ.get("NIMBUSWARE_API_PORT", "").strip()
        api_port = int(env_port) if env_port else _pick_free_port(api_host)
    os.environ["NIMBUSWARE_API_HOST"] = api_host
    os.environ["PORT"] = str(api_port)
    os.environ["NIMBUSWARE_API_BASE"] = f"http://{api_host}:{api_port}/v1"
    os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

    py_cmd = resolve_python_command(root)
    env = os.environ.copy()

    _spawn([*py_cmd, "-m", "nimbusware_api.cli"], cwd=root, env=env)

    api_url = f"http://{api_host}:{api_port}/openapi.json"
    _wait_for_http(api_url)

    console_url = _web_console_url(api_host=api_host, api_port=api_port, ui_mode=mode)
    _wait_for_http(console_url)
    return console_url, api_url, env


def run_desktop(
    *,
    root: Path | None = None,
    api_host: str = "127.0.0.1",
    streamlit_host: str = "127.0.0.1",
    api_port: int | None = None,
    streamlit_port: int | None = None,
    window_title: str | None = None,
    smoke_test: bool = False,
    ui_mode: str | None = None,
    quick_mode: bool = False,
) -> int:
    repo = (root or repo_root()).resolve()
    mode = _resolve_ui_mode(ui=ui_mode)
    if window_title is None:
        window_title = "Nimbusware Maker" if mode == "maker" else "Nimbusware Admin Console"
    log_file = run_log_path(repo)

    def _log(msg: str) -> None:
        print(msg, flush=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(msg + "\n")

    log_file.write_text("", encoding="utf-8")

    atexit.register(_terminate_procs)

    def _handle_signal(signum: int, _frame: object) -> None:
        _terminate_procs()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    api_port_display = api_port or os.environ.get("NIMBUSWARE_API_PORT", "8000")
    _log(f"Nimbusware repo: {repo}")
    _log(f"Log file: {log_file}")
    if using_default_admin_token():
        _log(
            "NOTE: Using dev default NIMBUSWARE_ADMIN_TOKEN — "
            "set a unique token before production or non-local API bind.",
        )
    _log(f"API: http://{api_host}:{api_port_display}/v1 (local only)")

    try:
        console_url, api_url, _env = start_servers(
            root=repo,
            api_host=api_host,
            streamlit_host=streamlit_host,
            api_port=api_port,
            streamlit_port=streamlit_port,
            ui_mode=mode,
            quick_mode=quick_mode,
        )
    except (TimeoutError, RuntimeError, FileNotFoundError) as exc:
        _log(f"ERROR: {exc}")
        _terminate_procs()
        return 1

    _log(f"Console server: {console_url} ({mode} UI, pywebview shell)")
    _log(f"API ready: {api_url}")

    if smoke_test:
        _log("Smoke test passed: API and web UI are reachable.")
        _terminate_procs()
        return 0

    py_cmd = resolve_python_command(repo)
    if sys.platform.startswith("linux"):
        ok, msg = ensure_linux_desktop_deps(repo, py_cmd, log=_log)
        if not ok:
            _log(f"ERROR: {msg}")
            _log(f"Manual: {linux_desktop_manual_hint()}")
            _terminate_procs()
            return 1
        if msg and "skipped" not in msg.lower():
            _log(msg)

    try:
        import webview
    except ImportError:
        _log("ERROR: pywebview is not installed. Run Install / setup or: poetry install")
        _terminate_procs()
        return 1

    gui = pick_webview_gui()
    _log(f"Opening desktop window (pywebview backend={gui!r})...")
    webview.create_window(
        window_title,
        console_url,
        width=1280,
        height=860,
        resizable=True,
        confirm_close=True,
    )
    try:
        webview.start(gui=gui)
    except Exception as exc:  # noqa: BLE001
        hint = ""
        if sys.platform == "win32":
            hint = " Install Microsoft Edge WebView2 Runtime if missing."
        elif sys.platform.startswith("linux"):
            hint = f" Try: {linux_desktop_manual_hint()}"
        elif sys.platform == "darwin":
            hint = " On macOS, pywebview uses Cocoa (no extra browser required)."
        _log(f"ERROR: pywebview failed to start: {exc}.{hint}")
        _terminate_procs()
        return 1
    finally:
        _terminate_procs()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Nimbusware (API + web UI) in a desktop window.",
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=None)
    parser.add_argument("--streamlit-host", default="127.0.0.1")
    parser.add_argument("--streamlit-port", type=int, default=None)
    parser.add_argument("--title", default=None, help="Window title (default: Maker or Console)")
    ui_group = parser.add_mutually_exclusive_group()
    ui_group.add_argument(
        "--console",
        action="store_true",
        help="Open the Admin Console instead of the maker app.",
    )
    ui_group.add_argument(
        "--admin",
        action="store_true",
        help="Alias for --console (Admin Console + API).",
    )
    ui_group.add_argument(
        "--maker",
        action="store_true",
        help="Open the maker app (default when neither flag is set).",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Start API + web UI backends, verify health, exit (no GUI window).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="In-memory store + stub critics + quick_local workflow.",
    )
    args = parser.parse_args(argv)
    ui_mode = "admin" if (args.console or args.admin) else "maker"
    return run_desktop(
        root=args.repo_root,
        api_host=args.api_host,
        api_port=args.api_port,
        streamlit_host=args.streamlit_host,
        streamlit_port=args.streamlit_port,
        window_title=args.title,
        smoke_test=args.smoke,
        ui_mode=ui_mode,
        quick_mode=args.quick,
    )


if __name__ == "__main__":
    raise SystemExit(main())
