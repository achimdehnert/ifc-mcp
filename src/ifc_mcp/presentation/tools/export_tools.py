"""Excel Export MCP Tools.

Tools for exporting IFC schedules to Excel files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.types import TextContent, Tool

from ifc_mcp.application.services import ExcelExportService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.config import settings
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)

# Default output directory
OUTPUT_DIR = Path("/tmp/ifc_exports")


def register_export_tools(server: Server) -> None:
    """Register Excel export MCP tools.

    Args:
        server: MCP Server instance
    """

    @server.list_tools()
    async def list_export_tools() -> list[Tool]:
        """List available export tools."""
        return [
            Tool(
                name="ifc_export_all_excel",
                description="Export all schedules (windows, doors, walls, drywalls, rooms) to a single Excel file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename (without path). Default: schedules_<project_id>.xlsx",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_export_window_excel",
                description="Export window schedule to Excel file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "storey_id": {
                            "type": "string",
                            "description": "Optional: Filter by storey UUID",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_export_door_excel",
                description="Export door schedule to Excel file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "storey_id": {
                            "type": "string",
                            "description": "Optional: Filter by storey UUID",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_export_room_excel",
                description="Export room schedule (Raumbuch) to Excel file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "storey_id": {
                            "type": "string",
                            "description": "Optional: Filter by storey UUID",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_export_ex_protection_excel",
                description="Export explosion protection report (Ex-Zones, Fire Ratings) to Excel file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_export_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle export tool calls."""
        try:
            if name == "ifc_export_all_excel":
                return await _export_all(arguments)
            elif name == "ifc_export_window_excel":
                return await _export_windows(arguments)
            elif name == "ifc_export_door_excel":
                return await _export_doors(arguments)
            elif name == "ifc_export_room_excel":
                return await _export_rooms(arguments)
            elif name == "ifc_export_ex_protection_excel":
                return await _export_ex_protection(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error("Export tool error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {str(e)}")]


def _ensure_output_dir() -> Path:
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _get_output_path(args: dict[str, Any], default_prefix: str) -> Path:
    """Get output file path."""
    output_dir = _ensure_output_dir()
    project_id = args["project_id"]

    if "filename" in args and args["filename"]:
        filename = args["filename"]
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
    else:
        # Generate default filename
        short_id = project_id[:8]
        filename = f"{default_prefix}_{short_id}.xlsx"

    return output_dir / filename


async def _export_all(args: dict[str, Any]) -> list[TextContent]:
    """Export all schedules."""
    project_id = UUID(args["project_id"])
    output_path = _get_output_path(args, "schedules")

    async with UnitOfWork() as uow:
        service = ExcelExportService(uow)
        result = await service.export_all_schedules(project_id, output_path)

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "sheets": result.sheet_count,
        "total_rows": result.row_count,
        "file_size_kb": result.file_size_kb,
        "message": f"Exported {result.row_count} items to {result.sheet_count} sheets",
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def _export_windows(args: dict[str, Any]) -> list[TextContent]:
    """Export window schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    output_path = _get_output_path(args, "windows")

    async with UnitOfWork() as uow:
        service = ExcelExportService(uow)
        result = await service.export_window_schedule(
            project_id, output_path, storey_id=storey_id
        )

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "rows": result.row_count,
        "file_size_kb": result.file_size_kb,
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def _export_doors(args: dict[str, Any]) -> list[TextContent]:
    """Export door schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    output_path = _get_output_path(args, "doors")

    async with UnitOfWork() as uow:
        service = ExcelExportService(uow)
        result = await service.export_door_schedule(
            project_id, output_path, storey_id=storey_id
        )

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "rows": result.row_count,
        "file_size_kb": result.file_size_kb,
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def _export_rooms(args: dict[str, Any]) -> list[TextContent]:
    """Export room schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    output_path = _get_output_path(args, "rooms")

    async with UnitOfWork() as uow:
        service = ExcelExportService(uow)
        result = await service.export_room_schedule(
            project_id, output_path, storey_id=storey_id
        )

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "rows": result.row_count,
        "file_size_kb": result.file_size_kb,
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def _export_ex_protection(args: dict[str, Any]) -> list[TextContent]:
    """Export Ex-Protection report."""
    project_id = UUID(args["project_id"])
    output_path = _get_output_path(args, "ex_protection")

    async with UnitOfWork() as uow:
        service = ExcelExportService(uow)
        result = await service.export_ex_protection_report(project_id, output_path)

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "sheets": result.sheet_count,
        "total_rows": result.row_count,
        "file_size_kb": result.file_size_kb,
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]
