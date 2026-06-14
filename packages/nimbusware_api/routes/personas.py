"""Persona catalog HTTP API (read open; writes require admin token)."""

from nimbusware_api.routes.personas_handlers import router

__all__ = ["router"]
