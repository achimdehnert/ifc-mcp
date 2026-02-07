"""IFC MCP Server.

An MCP server for processing IFC (Industry Foundation Classes) files
with PostgreSQL backend for construction and explosion protection use cases.
"""
from __future__ import annotations

__version__ = "0.1.0"
__author__ = "IFC-MCP Team"

# Re-export main entry point
from ifc_mcp.presentation import main

__all__ = ["main", "__version__"]
