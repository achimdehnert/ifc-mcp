"""MCP Tools registration.

All tool modules register their tools with the MCP server.
"""
from __future__ import annotations

from ifc_mcp.presentation.tools.analysis_tools import register_analysis_tools
from ifc_mcp.presentation.tools.ex_protection_tools import register_ex_protection_tools
from ifc_mcp.presentation.tools.export_tools import register_export_tools
from ifc_mcp.presentation.tools.fire_plan_tools import register_fire_plan_tools
from ifc_mcp.presentation.tools.project_tools import register_project_tools
from ifc_mcp.presentation.tools.schedule_tools import register_schedule_tools

__all__ = [
    "register_analysis_tools",
    "register_ex_protection_tools",
    "register_export_tools",
    "register_fire_plan_tools",
    "register_project_tools",
    "register_schedule_tools",
]
