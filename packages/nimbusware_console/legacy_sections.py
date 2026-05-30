"""Backward-compatible shim — use ``nimbusware_console.pages`` modules."""

from nimbusware_console.pages.config_tooling import render_config_tooling_section
from nimbusware_console.pages.run_detail import render_run_detail_section

__all__ = ["render_config_tooling_section", "render_run_detail_section"]
