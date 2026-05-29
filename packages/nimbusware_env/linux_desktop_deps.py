"""Linux GTK / WebKit system dependencies for pywebview desktop shell."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

LogFn = Callable[[str], None]


def _noop_log(_msg: str) -> None:
    return None


def gtk_import_ok(python_cmd: list[str], *, cwd: Path | None = None) -> bool:
    """Return True when the given interpreter can ``import gi`` (PyGObject)."""
    proc = subprocess.run(
        [*python_cmd, "-c", "import gi; gi.require_version('Gtk', '3.0')"],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _read_os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"')
    return data


def linux_package_manager() -> str | None:
    """Best-effort package manager id: ``apt``, ``dnf``, ``pacman``, ``zypper``."""
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("yum"):
        return "yum"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("zypper"):
        return "zypper"
    return None


def linux_desktop_system_packages(manager: str) -> list[str]:
    """Native packages for GTK3 + WebKit2 (pywebview ``gtk`` backend)."""
    if manager == "apt":
        return [
            "python3-gi",
            "python3-gi-cairo",
            "gir1.2-gtk-3.0",
            "libgtk-3-0",
            "libwebkit2gtk-4.1-0",
            "libgirepository-2.0-dev",
            "libcairo2-dev",
            "pkg-config",
        ]
    if manager in ("dnf", "yum"):
        return [
            "python3-gobject",
            "gtk3",
            "webkit2gtk4.1",
            "gobject-introspection-devel",
            "cairo-gobject-devel",
            "pkgconf-pkg-config",
        ]
    if manager == "pacman":
        return [
            "python-gobject",
            "gtk3",
            "webkit2gtk-4.1",
            "gobject-introspection",
            "cairo",
            "pkgconf",
        ]
    if manager == "zypper":
        return [
            "python3-gobject",
            "gtk3",
            "webkit2gtk4.1",
            "gobject-introspection-devel",
            "cairo-devel",
            "pkg-config",
        ]
    return []


def _privilege_prefix() -> list[str]:
    if os.geteuid() == 0:
        return []
    sudo = shutil.which("sudo")
    if sudo:
        return [sudo]
    return []


def _install_system_packages(
    manager: str,
    packages: list[str],
    *,
    log: LogFn,
) -> tuple[bool, str]:
    prefix = _privilege_prefix()
    if not prefix and os.geteuid() != 0:
        return (
            False,
            "Need root or sudo to install system packages. Re-run with sudo or use "
            "Install / setup from the launcher after configuring sudo.",
        )

    if manager == "apt":
        cmd = [*prefix, "apt-get", "install", "-y", *packages]
    elif manager == "dnf":
        cmd = [*prefix, "dnf", "install", "-y", *packages]
    elif manager == "yum":
        cmd = [*prefix, "yum", "install", "-y", *packages]
    elif manager == "pacman":
        cmd = [*prefix, "pacman", "-S", "--noconfirm", *packages]
    elif manager == "zypper":
        cmd = [*prefix, "zypper", "--non-interactive", "install", *packages]
    else:
        return False, f"Unsupported package manager: {manager}"

    log(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        return False, out or f"{manager} install failed (exit {proc.returncode})"
    return True, "System packages installed."


def _pip_install_pygobject(python_cmd: list[str], *, cwd: Path, log: LogFn) -> tuple[bool, str]:
    cmd = [*python_cmd, "-m", "pip", "install", "PyGObject"]
    log(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        return False, out or "pip install PyGObject failed"
    return True, "PyGObject installed in the active environment."


def ensure_linux_desktop_deps(
    root: Path,
    python_cmd: list[str],
    *,
    log: LogFn | None = None,
    install_system: bool = True,
    install_pip: bool = True,
) -> tuple[bool, str]:
    """Install GTK/WebKit deps on Linux when ``gi`` is not importable.

    Returns ``(ok, message)``. No-op on non-Linux platforms.
    """
    if not sys.platform.startswith("linux"):
        return True, "Not Linux; desktop GTK deps skipped."

    log = log or _noop_log

    if gtk_import_ok(python_cmd, cwd=root):
        return True, "GTK (PyGObject) already available."

    release = _read_os_release()
    distro = release.get("NAME") or release.get("ID") or "Linux"
    log(f"Linux desktop: installing GTK/WebKit dependencies ({distro})...")

    if install_system:
        manager = linux_package_manager()
        if manager is None:
            return (
                False,
                "Could not detect apt, dnf, yum, pacman, or zypper. Install manually: "
                "python3-gi, gir1.2-gtk-3.0, libwebkit2gtk-4.1-0 (Debian/Ubuntu).",
            )
        packages = linux_desktop_system_packages(manager)
        ok, msg = _install_system_packages(manager, packages, log=log)
        if not ok:
            return False, msg
        log(msg)

    if install_pip:
        ok, msg = _pip_install_pygobject(python_cmd, cwd=root, log=log)
        if not ok:
            return False, msg
        log(msg)

    if gtk_import_ok(python_cmd, cwd=root):
        return True, "Linux desktop dependencies are ready."

    return (
        False,
        "GTK packages were installed but `import gi` still fails. "
        "Try: poetry run pip install PyGObject, or recreate the venv after apt install.",
    )


def linux_desktop_manual_hint() -> str:
    manager = linux_package_manager()
    if manager == "apt":
        return (
            "sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 "
            "libwebkit2gtk-4.1-0"
        )
    if manager in ("dnf", "yum"):
        return "sudo dnf install -y python3-gobject gtk3 webkit2gtk4.1"
    if manager == "pacman":
        return "sudo pacman -S python-gobject gtk3 webkit2gtk-4.1"
    return "Install python3-gi / PyGObject and GTK3 + WebKit2 for your distribution."
