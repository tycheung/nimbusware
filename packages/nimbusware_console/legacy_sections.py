from __future__ import annotations


def render_config_tooling_section() -> None:
    raise RuntimeError("Config tooling UI moved to /v1/admin/app/.")


def render_run_detail_section() -> None:
    raise RuntimeError("Run detail UI moved to /v1/admin/app/.")


__all__ = ["render_config_tooling_section", "render_run_detail_section"]
