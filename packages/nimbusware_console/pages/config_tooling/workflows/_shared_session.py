from __future__ import annotations

import csv
import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from nimbusware_console.pages.config_tooling._common import (  # noqa: E402
    API_BASE,
    _resolve_prune_status_path,
    rl,
)

from nimbusware_console.pages.config_tooling._common import (  # noqa: E402
    API_BASE,
    _resolve_prune_status_path,
    rl,
)
