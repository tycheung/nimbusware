from __future__ import annotations

import os
from pathlib import Path

from nimbusware_console.pages.run_detail._imports_common import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_display_a import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_display_b import *  # noqa: F403

_iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
