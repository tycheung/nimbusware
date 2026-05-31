"""Split pages/_state_run_list.py into query-param sync and render/fetch modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "packages/nimbusware_console/pages/_state_run_list.py"
text = path.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

header_end = next(i for i, line in enumerate(lines) if line.startswith("def _qp_get"))
render_start = next(i for i, line in enumerate(lines) if line.startswith("def _run_list_payload_to_csv"))

header = "".join(lines[:header_end])
qp_body = "".join(lines[header_end:render_start])
render_body = "".join(lines[render_start:])

key_import_block = header.split("from nimbusware_console.pages._state_keys import (")[1].split(")\nfrom nimbusware_console.run_list_pagination_display")[0]
pagination_block = header.split("from nimbusware_console.run_list_pagination_display import (")[1].split(")\nfrom nimbusware_console.settings import API_BASE")[0]

keys_import = (
    "from nimbusware_console.pages._state_keys import (\n"
    + key_import_block
    + ")\n"
)

common_header = (
    '''"""Run list helpers."""

from __future__ import annotations

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
'''
    + keys_import
    + f"""from nimbusware_console.run_list_pagination_display import (
{pagination_block})
from nimbusware_console.settings import API_BASE

"""
)

(ROOT / "packages/nimbusware_console/pages/_state_run_list_qp.py").write_text(
    common_header.replace('"""Run list helpers."""', '"""Run list query-param sync and defaults."""')
    + qp_body,
    encoding="utf-8",
)

(ROOT / "packages/nimbusware_console/pages/_state_run_list_render.py").write_text(
    common_header.replace('"""Run list helpers."""', '"""Run list fetch, CSV export, and display."""')
    + render_body,
    encoding="utf-8",
)

facade = '''"""Run list query-param sync, fetch, and display."""

from __future__ import annotations

import nimbusware_console.pages._state_run_list_qp as _state_run_list_qp
import nimbusware_console.pages._state_run_list_render as _state_run_list_render

globals().update(
    {k: v for k, v in vars(_state_run_list_qp).items() if not k.startswith("__")},
)
globals().update(
    {k: v for k, v in vars(_state_run_list_render).items() if not k.startswith("__")},
)
'''
path.write_text(facade, encoding="utf-8")
print("state_run_list split done")
