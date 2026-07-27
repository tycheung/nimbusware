# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_all

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
LAUNCHER = os.path.join(REPO_ROOT, "launcher.py")
ASSETS_DIR = os.path.join(REPO_ROOT, "packages", "env", "assets")
INSTALL_SCRIPT = os.path.join(REPO_ROOT, "scripts", "install", "install_nimbusware.py")
SETTINGS_CATALOG_DIR = os.path.join(REPO_ROOT, "configs", "settings_catalog")

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

a = Analysis(
    [LAUNCHER],
    pathex=[os.path.join(REPO_ROOT, "packages")],
    binaries=ctk_binaries,
    datas=[
        (INSTALL_SCRIPT, "install"),
        (ASSETS_DIR, "assets"),
        # Eagerly loaded via env.settings_catalog at import time (frozen launcher).
        (SETTINGS_CATALOG_DIR, "configs/settings_catalog"),
        *ctk_datas,
    ],
    hiddenimports=[
        "env.launcher_fetch",
        "env.launcher_theme",
        "env.launcher_manage",
        "env.launcher_dialogs",
        "env.desktop_common",
        "env.dotenv",
        "customtkinter",
        "PIL",
        *ctk_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NimbuswareLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
