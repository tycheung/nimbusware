# -*- mode: python ; coding: utf-8 -*-
# Built by scripts/build_launcher.ps1 | build_launcher.sh

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
LAUNCHER = os.path.join(ROOT, "launcher.py")

a = Analysis(
    [LAUNCHER],
    pathex=[os.path.join(ROOT, "packages")],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
