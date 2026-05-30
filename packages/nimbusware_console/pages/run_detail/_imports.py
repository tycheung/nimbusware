from __future__ import annotations

from nimbusware_console.pages.run_detail._imports_common import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_display_a import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_display_b import *  # noqa: F403
from nimbusware_console.settings import API_BASE
from nimbusware_console.pages import _state as rl

_iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
