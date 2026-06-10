"""Backward-compatible shim — model routes live in platform.py."""

from nimbusware_api.routes.platform import router

__all__ = ["router"]
