"""Split pages/_state.py into keys + run_list modules."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "packages/nimbusware_console/pages/_state.py"

# Restore monolith from git if facade-only (re-run safe).
text = path.read_text(encoding="utf-8")
if "from nimbusware_console.pages._state_keys import" in text:
    import subprocess

    text = subprocess.check_output(
        ["git", "show", "HEAD:packages/nimbusware_console/pages/_state.py"],
        cwd=ROOT,
        text=True,
    )

lines = text.splitlines(keepends=True)

# 1-based line numbers from original monolith (git HEAD).
keys_block_a = "".join(lines[32:73])  # _RUN_LIST_QP_KEYS … _LIST_OPTIONAL_ORDER
keys_block_b = "".join(lines[205:212])  # _LAST_LIST_PAGE … merge dry keys
funcs = "".join(lines[75:205]) + "".join(lines[212:])

key_names = sorted(
    set(re.findall(r"^(_[A-Z0-9_]+)\s*=", keys_block_a + keys_block_b, re.M)),
    key=str.lower,
)

keys_content = (
    "from __future__ import annotations\n\n"
    + keys_block_a
    + keys_block_b
)
(ROOT / "packages/nimbusware_console/pages/_state_keys.py").write_text(
    keys_content,
    encoding="utf-8",
)

pagination_block = text.split(
    "from nimbusware_console.run_list_pagination_display import (",
)[1].split(")\nfrom nimbusware_console.settings import API_BASE")[0]

key_import = ",\n    ".join(key_names)
run_list_content = f'''from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import streamlit as st

from nimbusware_client.http import HTTPError, get_response
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.pages._state_keys import (
    {key_import},
)
from nimbusware_console.run_list_pagination_display import (
{pagination_block})
from nimbusware_console.settings import API_BASE

{funcs}'''
(ROOT / "packages/nimbusware_console/pages/_state_run_list.py").write_text(
    run_list_content,
    encoding="utf-8",
)

facade = '''from __future__ import annotations

import nimbusware_console.pages._state_keys as _state_keys
import nimbusware_console.pages._state_run_list as _state_run_list

globals().update(
    {k: v for k, v in vars(_state_keys).items() if not k.startswith("__")},
)
globals().update(
    {k: v for k, v in vars(_state_run_list).items() if not k.startswith("__")},
)
'''
path.write_text(facade, encoding="utf-8")
print("split complete")
