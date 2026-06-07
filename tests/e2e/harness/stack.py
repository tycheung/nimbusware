from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass
class StackProcess:
    proc: subprocess.Popen[bytes]
    port: int
    base_url: str

    def wait_ready(self, *, timeout_sec: float = 60.0) -> None:
        deadline = time.monotonic() + timeout_sec
        url = f"{self.base_url}/v1/maker/app/"
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"API process exited early code={self.proc.returncode}")
            try:
                resp = httpx.get(url, timeout=2.0)
                if resp.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise TimeoutError(f"API not ready at {url}")


def start_api_subprocess(
    repo_root: Path,
    *,
    env: dict[str, str] | None = None,
    port: int | None = None,
) -> StackProcess:
    chosen = port or free_port()
    merged = os.environ.copy()
    merged.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    merged.setdefault("NIMBUSWARE_REPO_ROOT", str(repo_root))
    if env:
        merged.update(env)
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "nimbusware_api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(chosen),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        env=merged,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    stack = StackProcess(proc=proc, port=chosen, base_url=f"http://127.0.0.1:{chosen}")
    stack.wait_ready()
    return stack


@dataclass
class InProcessDispatchWorker:
    thread: threading.Thread
    stop: threading.Event

    def join(self, timeout: float = 15.0) -> None:
        self.stop.set()
        self.thread.join(timeout=timeout)


def start_inprocess_dispatch_worker(
    orchestrator: object,
    queue: object,
    *,
    idle_sleep_seconds: float = 0.05,
) -> InProcessDispatchWorker:
    from nimbusware_orchestrator.run_worker import start_embedded_dispatch_worker

    worker = start_embedded_dispatch_worker(
        orchestrator,  # type: ignore[arg-type]
        queue,  # type: ignore[arg-type]
        idle_sleep_seconds=idle_sleep_seconds,
    )
    return InProcessDispatchWorker(thread=worker.thread, stop=worker.stop)


def stop_api_subprocess(stack: StackProcess) -> None:
    if stack.proc.poll() is None:
        stack.proc.terminate()
        try:
            stack.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            stack.proc.kill()
            stack.proc.wait(timeout=5)
