from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODELS = ("llama3.1:8b", "qwen2.5-coder:14b")
ENV_USE_LLM = "NIMBUSWARE_USE_LLM"


class OllamaSetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class OllamaSetupOption:
    key: str
    title: str
    explanation: str
    available: bool
    unavailable_reason: str = ""


def _which(name: str) -> str | None:
    return shutil.which(name)


def winget_available() -> bool:
    return _which("winget") is not None


def brew_available() -> bool:
    return _which("brew") is not None


def ollama_api_host(host: str | None = None) -> str:
    return (host or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")


def ollama_reachable(host: str | None = None, *, timeout_s: float = 2.0) -> bool:
    base = ollama_api_host(host)
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_for_ollama(
    host: str | None = None,
    *,
    attempts: int = 30,
    sleep_s: float = 2.0,
    log=print,
) -> bool:
    base = ollama_api_host(host)
    log(f"Waiting for Ollama at {base} ...")
    for i in range(attempts):
        if ollama_reachable(base):
            log("Ollama API is responding.")
            return True
        if i < attempts - 1:
            time.sleep(sleep_s)
    return False


def find_ollama_binary() -> str | None:
    on_path = _which("ollama")
    if on_path:
        return on_path
    if sys.platform == "win32":
        local = (
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        )
        if local.is_file():
            return str(local)
    return None


def prepend_ollama_to_path() -> str | None:
    binary = find_ollama_binary()
    if binary is None:
        return None
    bin_dir = str(Path(binary).parent)
    current = os.environ.get("PATH", "")
    if bin_dir.lower() not in current.lower():
        os.environ["PATH"] = bin_dir + os.pathsep + current
    return binary


def list_installed_models(host: str | None = None) -> list[str]:
    base = ollama_api_host(host)
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for item in models:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name:
                names.append(name)
    return names


def _model_present(model: str, installed: list[str]) -> bool:
    target = model.split(":")[0]
    for name in installed:
        if name == model or name.split(":")[0] == target:
            return True
    return False


def models_from_repo(repo: Path) -> list[str]:
    path = repo / "configs" / "model-routing.yaml"
    models: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s*-?\s*id:\s*(\S+)", line)
            if match:
                models.append(match.group(1))
    if not models:
        models = list(DEFAULT_MODELS)
    seen: set[str] = set()
    ordered: list[str] = []
    for model in models:
        if model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered


def build_ollama_setup_options(*, platform: str | None = None) -> list[OllamaSetupOption]:
    plat = platform or sys.platform
    options: list[OllamaSetupOption] = []

    if plat == "win32":
        winget_ok = winget_available()
        options.append(
            OllamaSetupOption(
                key="winget",
                title="winget (Ollama for Windows)",
                explanation=(
                    "Installs Ollama.Ollama via Windows Package Manager. "
                    "Runs in your user profile (no admin required). After install, "
                    "pulls Nimbusware agent default models from configs/model-routing.yaml."
                ),
                available=winget_ok,
                unavailable_reason="winget was not found on PATH.",
            ),
        )
        options.append(
            OllamaSetupOption(
                key="download",
                title="Open ollama.com download page",
                explanation=(
                    "Opens https://ollama.com/download in your browser to run OllamaSetup.exe. "
                    "Use this if winget is unavailable. Press Enter here when the API responds."
                ),
                available=True,
            ),
        )
    elif plat == "darwin":
        brew_ok = brew_available()
        options.append(
            OllamaSetupOption(
                key="brew",
                title="Homebrew (brew install ollama)",
                explanation=(
                    "Installs the ollama formula via Homebrew, then pulls default Nimbusware agent models."
                ),
                available=brew_ok,
                unavailable_reason="Homebrew (brew) was not found on PATH.",
            ),
        )
        options.append(
            OllamaSetupOption(
                key="script",
                title="Official install script (curl)",
                explanation=(
                    "Runs curl -fsSL https://ollama.com/install.sh | sh from ollama.com."
                ),
                available=_which("curl") is not None,
                unavailable_reason="curl was not found on PATH.",
            ),
        )
    else:
        options.append(
            OllamaSetupOption(
                key="script",
                title="Official install script (curl)",
                explanation=(
                    "Runs curl -fsSL https://ollama.com/install.sh | sh. "
                    "May require sudo. Then pulls default Nimbusware agent models."
                ),
                available=_which("curl") is not None,
                unavailable_reason="curl was not found on PATH.",
            ),
        )

    options.extend(
        [
            OllamaSetupOption(
                key="pull",
                title="Pull models only (Ollama already installed)",
                explanation=(
                    "Skips installation; runs ollama pull for models in "
                    "configs/model-routing.yaml that are not already present."
                ),
                available=True,
            ),
            OllamaSetupOption(
                key="manual",
                title="I already have Ollama running",
                explanation=(
                    "Use an existing Ollama install. Press Enter when http://127.0.0.1:11434 "
                    "responds. Optionally pull missing models afterward."
                ),
                available=True,
            ),
            OllamaSetupOption(
                key="skip",
                title="Skip Ollama for now",
                explanation=(
                    "Nimbusware setup continues without LLM. Set NIMBUSWARE_USE_LLM=1 later "
                    "after Ollama is running."
                ),
                available=True,
            ),
        ],
    )
    return options


def _wrap(text: str, *, indent: int, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = " " * indent
    for word in words:
        chunk = word if not current.strip() else f" {word}"
        if len(current) + len(chunk) > width and current.strip():
            lines.append(current.rstrip())
            current = " " * indent + word
        else:
            current += chunk if current.strip() else (" " * indent + word)
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _print_menu(options: list[OllamaSetupOption], host: str) -> None:
    print("", flush=True)
    print("=" * 72, flush=True)
    print("Ollama is not reachable", flush=True)
    print(f"  API: {host}/api/tags", flush=True)
    print("=" * 72, flush=True)
    print("", flush=True)
    print("Choose how to set up Ollama for Nimbusware agent LLM stages:", flush=True)
    print("", flush=True)
    for index, opt in enumerate(options, start=1):
        status = "available" if opt.available else f"NOT available - {opt.unavailable_reason}"
        print(f"  [{index}] {opt.title}", flush=True)
        for line in _wrap(opt.explanation, indent=6, width=70):
            print(line, flush=True)
        print(f"      ({status})", flush=True)
        print("", flush=True)
    keys = ", ".join(opt.key for opt in options)
    print(f"Enter a number [1-{len(options)}] or option key ({keys}): ", end="", flush=True)


def prompt_ollama_setup_choice(options: list[OllamaSetupOption], host: str) -> str:
    key_by_index = {str(i): opt.key for i, opt in enumerate(options, start=1)}
    key_by_name = {opt.key: opt.key for opt in options}
    while True:
        _print_menu(options, host)
        raw = input().strip().lower()
        if not raw:
            print("Please enter a choice.", flush=True)
            continue
        chosen_key = key_by_index.get(raw) or key_by_name.get(raw)
        if chosen_key is None:
            print(f"Invalid choice: {raw!r}. Try again.", flush=True)
            continue
        opt = next(o for o in options if o.key == chosen_key)
        if not opt.available:
            print(f"Option [{opt.title}] is not available: {opt.unavailable_reason}", flush=True)
            continue
        return chosen_key


def prompt_press_enter_when_ready(message: str) -> None:
    print("", flush=True)
    print(message, flush=True)
    print("Press Enter when Ollama is responding...", flush=True)
    try:
        input()
    except EOFError:
        pass


def _open_download_page(log) -> None:
    url = "https://ollama.com/download"
    log(f"Open {url} in your browser and run the installer.")
    if sys.platform == "win32":
        os.startfile(url)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", url], check=False)
    else:
        subprocess.run(["xdg-open", url], check=False)


def install_ollama_winget(*, log) -> None:
    log("Running: winget install -e --id Ollama.Ollama")
    subprocess.run(
        [
            "winget",
            "install",
            "-e",
            "--id",
            "Ollama.Ollama",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        check=False,
    )


def install_ollama_brew(*, log) -> None:
    log("Running: brew install ollama")
    subprocess.run(["brew", "install", "ollama"], check=False)


def install_ollama_unix_script(*, log) -> None:
    curl = _which("curl")
    sh = _which("sh") or "/bin/sh"
    if not curl:
        raise OllamaSetupError("curl is required for the Ollama install script.")
    log("Running: curl -fsSL https://ollama.com/install.sh | sh")
    subprocess.run(
        [sh, "-c", f"{curl} -fsSL https://ollama.com/install.sh | sh"],
        check=False,
    )


def _try_start_ollama(*, log) -> None:
    binary = prepend_ollama_to_path()
    if binary is None:
        return
    if ollama_reachable():
        return
    if sys.platform == "win32":
        app = Path(binary).parent / "Ollama.exe"
        if not app.is_file():
            app = Path(binary).parent / "ollama app.exe"
        if app.is_file():
            log(f"Starting Ollama app: {app}")
            subprocess.Popen(  # noqa: S603
                [str(app)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
    log("Starting: ollama serve")
    subprocess.Popen(  # noqa: S603
        [binary, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def pull_ollama_models(
    models: list[str],
    *,
    host: str | None = None,
    skip_existing: bool = True,
    log=print,
) -> list[str]:
    binary = prepend_ollama_to_path()
    if binary is None:
        raise OllamaSetupError(
            "ollama CLI not found. Install Ollama and ensure it is on PATH, then retry.",
        )
    if not wait_for_ollama(host, log=log):
        raise OllamaSetupError(
            f"Ollama API is not reachable at {ollama_api_host(host)}. "
            "Start Ollama and retry.",
        )
    installed = list_installed_models(host) if skip_existing else []
    pulled: list[str] = []
    for model in models:
        if skip_existing and _model_present(model, installed):
            log(f"Model already present: {model}")
            continue
        log(f"Pulling model {model} (this may take several minutes)...")
        subprocess.run([binary, "pull", model], check=True)
        pulled.append(model)
    return pulled


def enable_nimbusware_llm_in_env(repo_root: Path, *, log) -> None:
    packages = repo_root / "packages"
    if str(packages) not in sys.path:
        sys.path.insert(0, str(packages))
    from nimbusware_env import set_env_var  # noqa: PLC0415

    path = set_env_var(ENV_USE_LLM, "1", repo_root=repo_root)
    os.environ[ENV_USE_LLM] = "1"
    log(f"Enabled {ENV_USE_LLM}=1 in {path}")


def bootstrap_ollama(
    *,
    repo: Path,
    host: str,
    choice: str | None,
    non_interactive: bool,
    skip_pull: bool,
    models: list[str] | None,
    enable_llm: bool,
    log=print,
) -> bool:
    """Install/start Ollama and pull models. Returns True when API is reachable."""
    base = ollama_api_host(host)
    if ollama_reachable(base):
        log("Ollama is already reachable.")
    else:
        resolved = choice
        if resolved is None:
            if non_interactive:
                if sys.platform == "win32" and winget_available():
                    resolved = "winget"
                elif sys.platform == "darwin" and brew_available():
                    resolved = "brew"
                elif _which("curl"):
                    resolved = "script"
                else:
                    resolved = "skip"
            else:
                resolved = prompt_ollama_setup_choice(
                    build_ollama_setup_options(),
                    base,
                )

        log(f"\nOllama setup: {resolved}")
        if resolved == "skip":
            return False
        if resolved == "winget":
            install_ollama_winget(log=log)
        elif resolved == "brew":
            install_ollama_brew(log=log)
        elif resolved == "script":
            install_ollama_unix_script(log=log)
        elif resolved == "download":
            _open_download_page(log)
            prompt_press_enter_when_ready(
                "Complete the Ollama installer, then continue.",
            )
        elif resolved == "manual":
            prompt_press_enter_when_ready(
                f"Start Ollama and ensure {base} responds.",
            )
        elif resolved == "pull":
            pass
        else:
            raise OllamaSetupError(f"Unknown Ollama setup choice: {resolved!r}")

        if resolved not in ("manual", "download", "pull", "skip"):
            prepend_ollama_to_path()
            _try_start_ollama(log=log)

        if not wait_for_ollama(base, log=log):
            if resolved in ("manual", "download"):
                raise OllamaSetupError(
                    f"Ollama is not reachable at {base}. Start Ollama and re-run setup.",
                )
            raise OllamaSetupError(
                f"Ollama install finished but API is not reachable at {base}. "
                "Open the Ollama app or run `ollama serve`, then re-run setup.",
            )

    if not skip_pull:
        target_models = models if models is not None else models_from_repo(repo)
        if target_models:
            log("")
            log("Pulling Nimbusware agent model(s) for local LLM runs...")
            pull_ollama_models(target_models, host=base, log=log)

    if enable_llm:
        enable_nimbusware_llm_in_env(repo, log=log)

    return ollama_reachable(base)
