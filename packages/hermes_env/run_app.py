"""Start Hermes API + Streamlit operator console inside a pywebview window."""

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

from hermes_env.desktop_common import (
    pick_webview_gui,
    repo_root,
    resolve_python_command,
    subprocess_spawn_kwargs,
    terminate_process,
)
from hermes_env.dotenv import load_dotenv
from hermes_env.linux_desktop_deps import ensure_linux_desktop_deps, linux_desktop_manual_hint

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
    kwargs = subprocess_spawn_kwargs(detach=sys.platform != "win32")
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, **kwargs)  # noqa: S603
    _PROCS.append(proc)
    return proc


def _streamlit_command(py_cmd: list[str], console_script: Path, host: str, port: int) -> list[str]:
    return [
        *py_cmd,
        "-m",
        "streamlit",
        "run",
        str(console_script),
        "--server.headless",
        "true",
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--browser.gatherUsageStats",
        "false",
        "--global.developmentMode",
        "false",
    ]


def start_servers(
    *,
    root: Path,
    api_host: str = "127.0.0.1",
    streamlit_host: str = "127.0.0.1",
    api_port: int | None = None,
    streamlit_port: int | None = None,
) -> tuple[str, str, dict[str, str]]:
    """Start API + Streamlit; return console URL, API OpenAPI URL, and child env."""
    load_dotenv(repo_root=root)
    os.environ.setdefault("HERMES_REPO_ROOT", str(root))

    api_port = api_port or int(os.environ.get("HERMES_API_PORT", "8000"))
    streamlit_port = streamlit_port or _pick_free_port(streamlit_host)

    os.environ["HERMES_API_HOST"] = api_host
    os.environ["PORT"] = str(api_port)
    os.environ["HERMES_API_BASE"] = f"http://{api_host}:{api_port}/v1"
    os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

    py_cmd = resolve_python_command(root)
    env = os.environ.copy()

    console_script = root / "packages" / "hermes_console" / "app.py"
    if not console_script.is_file():
        raise FileNotFoundError(f"Streamlit app not found: {console_script}")

    _spawn([*py_cmd, "-m", "hermes_api.cli"], cwd=root, env=env)
    _spawn(
        _streamlit_command(py_cmd, console_script, streamlit_host, streamlit_port),
        cwd=root,
        env=env,
    )

    console_url = f"http://{streamlit_host}:{streamlit_port}"
    api_url = f"http://{api_host}:{api_port}/openapi.json"
    _wait_for_http(f"{console_url}/_stcore/health")
    _wait_for_http(api_url)
    return console_url, api_url, env


def run_desktop(
    *,
    root: Path | None = None,
    api_host: str = "127.0.0.1",
    streamlit_host: str = "127.0.0.1",
    api_port: int | None = None,
    streamlit_port: int | None = None,
    window_title: str = "Hermes",
    smoke_test: bool = False,
) -> int:
    repo = (root or repo_root()).resolve()

    atexit.register(_terminate_procs)

    def _handle_signal(signum: int, _frame: object) -> None:
        _terminate_procs()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    api_port_display = api_port or os.environ.get("HERMES_API_PORT", "8000")
    print(f"Hermes repo: {repo}")
    print(f"API: http://{api_host}:{api_port_display}/v1 (local only)")

    try:
        console_url, api_url, _env = start_servers(
            root=repo,
            api_host=api_host,
            streamlit_host=streamlit_host,
            api_port=api_port,
            streamlit_port=streamlit_port,
        )
    except (TimeoutError, RuntimeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _terminate_procs()
        return 1

    print(f"Console server: {console_url} (pywebview shell)")
    print(f"API ready: {api_url}")

    if smoke_test:
        print("Smoke test passed: API and Streamlit are reachable.")
        _terminate_procs()
        return 0

    py_cmd = resolve_python_command(repo)
    if sys.platform.startswith("linux"):
        ok, msg = ensure_linux_desktop_deps(repo, py_cmd, log=print)
        if not ok:
            print(f"ERROR: {msg}", file=sys.stderr)
            print(f"Manual: {linux_desktop_manual_hint()}", file=sys.stderr)
            _terminate_procs()
            return 1
        if msg and "skipped" not in msg.lower():
            print(msg)

    try:
        import webview
    except ImportError:
        print(
            "ERROR: pywebview is not installed. Run: poetry install",
            file=sys.stderr,
        )
        _terminate_procs()
        return 1

    gui = pick_webview_gui()
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
    except Exception as exc:  # noqa: BLE001 — surface backend install hints
        hint = ""
        if sys.platform.startswith("linux"):
            hint = f" Try: {linux_desktop_manual_hint()}"
        elif sys.platform == "darwin":
            hint = " On macOS, pywebview uses Cocoa (no extra browser required)."
        print(f"ERROR: pywebview failed to start: {exc}.{hint}", file=sys.stderr)
        _terminate_procs()
        return 1
    finally:
        _terminate_procs()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Hermes API and operator console in a desktop window.",
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=None)
    parser.add_argument("--streamlit-host", default="127.0.0.1")
    parser.add_argument("--streamlit-port", type=int, default=None)
    parser.add_argument("--title", default="Hermes")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Start API + Streamlit, verify health, exit (no GUI window).",
    )
    args = parser.parse_args(argv)
    return run_desktop(
        root=args.repo_root,
        api_host=args.api_host,
        api_port=args.api_port,
        streamlit_host=args.streamlit_host,
        streamlit_port=args.streamlit_port,
        window_title=args.title,
        smoke_test=args.smoke,
    )


if __name__ == "__main__":
    raise SystemExit(main())
