"""Shared module.

Cross-cutting concerns: configuration, logging, result pattern.
"""
from ifc_mcp.shared.config import Settings, get_settings, settings

__all__ = [
    "Settings",
    "get_settings",
    "settings",
]
