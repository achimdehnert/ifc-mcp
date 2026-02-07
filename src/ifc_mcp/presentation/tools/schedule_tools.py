"""Schedule MCP Tools.

Tools for generating construction schedules (window, door, wall lists).
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.types import TextContent, Tool

from ifc_mcp.application.services import ScheduleService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def register_schedule_tools(server: Server) -> None:
    """Register schedule-related MCP tools.

    Args:
        server: MCP Server instance
    """

    @server.list_tools()
    async def list_schedule_tools() -> list[Tool]:
        """List available schedule tools."""
        return [
            Tool(
                name="ifc_window_schedule",
                description="Generate a window schedule (list of all windows with properties).",
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
                        "group_by": {
                            "type": "string",
                            "enum": ["storey", "type"],
                            "description": "Optional: Group results by field",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "markdown"],
                            "default": "markdown",
                            "description": "Output format",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_door_schedule",
                description="Generate a door schedule (list of all doors with fire/acoustic ratings).",
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
                        "group_by": {
                            "type": "string",
                            "enum": ["storey", "type"],
                            "description": "Optional: Group results by field",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "markdown"],
                            "default": "markdown",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_wall_schedule",
                description="Generate a wall schedule with material and structural info.",
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
                        "load_bearing_only": {
                            "type": "boolean",
                            "description": "Only show load-bearing walls",
                            "default": False,
                        },
                        "external_only": {
                            "type": "boolean",
                            "description": "Only show external walls",
                            "default": False,
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "markdown"],
                            "default": "markdown",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_drywall_schedule",
                description="Generate a drywall/partition schedule (Trockenbauliste).",
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
                        "format": {
                            "type": "string",
                            "enum": ["json", "markdown"],
                            "default": "markdown",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_room_schedule",
                description="Generate a room schedule (Raumbuch) with areas and finishes.",
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
                        "format": {
                            "type": "string",
                            "enum": ["json", "markdown"],
                            "default": "markdown",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_schedule_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle schedule tool calls."""
        try:
            if name == "ifc_window_schedule":
                return await _window_schedule(arguments)
            elif name == "ifc_door_schedule":
                return await _door_schedule(arguments)
            elif name == "ifc_wall_schedule":
                return await _wall_schedule(arguments)
            elif name == "ifc_drywall_schedule":
                return await _drywall_schedule(arguments)
            elif name == "ifc_room_schedule":
                return await _room_schedule(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error("Tool error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _window_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Generate window schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    group_by = args.get("group_by")
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ScheduleService(uow)
        result = await service.generate_window_schedule(
            project_id,
            storey_id=storey_id,
            group_by=group_by,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(_result_to_dict(result), cls=DecimalEncoder, indent=2)
        )]

    return [TextContent(type="text", text=_format_schedule_markdown(result, "Window Schedule"))]


async def _door_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Generate door schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    group_by = args.get("group_by")
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ScheduleService(uow)
        result = await service.generate_door_schedule(
            project_id,
            storey_id=storey_id,
            group_by=group_by,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(_result_to_dict(result), cls=DecimalEncoder, indent=2)
        )]

    return [TextContent(type="text", text=_format_schedule_markdown(result, "Door Schedule"))]


async def _wall_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Generate wall schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    load_bearing_only = args.get("load_bearing_only", False)
    external_only = args.get("external_only", False)
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ScheduleService(uow)
        result = await service.generate_wall_schedule(
            project_id,
            storey_id=storey_id,
            load_bearing_only=load_bearing_only,
            external_only=external_only,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(_result_to_dict(result), cls=DecimalEncoder, indent=2)
        )]

    return [TextContent(type="text", text=_format_wall_schedule_markdown(result))]


async def _drywall_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Generate drywall schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ScheduleService(uow)
        result = await service.generate_drywall_schedule(
            project_id,
            storey_id=storey_id,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(_result_to_dict(result), cls=DecimalEncoder, indent=2)
        )]

    return [TextContent(type="text", text=_format_schedule_markdown(result, "Drywall Schedule"))]


async def _room_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Generate room schedule."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ScheduleService(uow)
        result = await service.generate_room_schedule(
            project_id,
            storey_id=storey_id,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(_result_to_dict(result), cls=DecimalEncoder, indent=2)
        )]

    return [TextContent(type="text", text=_format_room_schedule_markdown(result))]


def _result_to_dict(result: Any) -> dict[str, Any]:
    """Convert ScheduleResult to dict."""
    return {
        "schedule_type": result.schedule_type,
        "project_id": str(result.project_id),
        "total_count": result.total_count,
        "total_area_m2": result.total_area_m2,
        "total_length_m": result.total_length_m,
        "total_volume_m3": result.total_volume_m3,
        "items": [
            {
                "id": str(item.id),
                "name": item.name,
                "type_name": item.type_name,
                "storey_name": item.storey_name,
                "tag": item.tag,
                "width_m": item.width_m,
                "height_m": item.height_m,
                "area_m2": item.area_m2,
                "properties": item.properties,
            }
            for item in result.items
        ],
    }


def _format_schedule_markdown(result: Any, title: str) -> str:
    """Format schedule as markdown table."""
    lines = [
        f"# {title}",
        "",
        f"**Total Items:** {result.total_count}",
    ]

    if result.total_area_m2:
        lines.append(f"**Total Area:** {result.total_area_m2:.2f} m\u00b2")

    lines.extend(["", "| Name | Type | Storey | Width (m) | Height (m) | Area (m\u00b2) |"])
    lines.append("|------|------|--------|-----------|------------|-----------|")

    for item in result.items[:100]:  # Limit to 100 rows
        width = f"{item.width_m:.2f}" if item.width_m else "-"
        height = f"{item.height_m:.2f}" if item.height_m else "-"
        area = f"{item.area_m2:.2f}" if item.area_m2 else "-"
        lines.append(
            f"| {item.name or '-'} | {item.type_name or '-'} | "
            f"{item.storey_name or '-'} | {width} | {height} | {area} |"
        )

    if result.total_count > 100:
        lines.append(f"\n*... and {result.total_count - 100} more items*")

    return "\n".join(lines)


def _format_wall_schedule_markdown(result: Any) -> str:
    """Format wall schedule as markdown."""
    lines = [
        "# Wall Schedule",
        "",
        f"**Total Walls:** {result.total_count}",
    ]

    if result.total_area_m2:
        lines.append(f"**Total Area:** {result.total_area_m2:.2f} m\u00b2")
    if result.total_length_m:
        lines.append(f"**Total Length:** {result.total_length_m:.2f} m")

    lines.extend([
        "",
        "| Name | Type | Storey | Length (m) | Height (m) | External | Load-Bearing | Drywall |"
    ])
    lines.append("|------|------|--------|------------|------------|----------|--------------|---------|")

    for item in result.items[:100]:
        length = f"{item.length_m:.2f}" if item.length_m else "-"
        height = f"{item.height_m:.2f}" if item.height_m else "-"
        external = "Yes" if item.properties.get("is_external") else "No"
        load_bearing = "Yes" if item.properties.get("is_load_bearing") else "No"
        drywall = "Yes" if item.properties.get("is_drywall") else "No"

        lines.append(
            f"| {item.name or '-'} | {item.type_name or '-'} | "
            f"{item.storey_name or '-'} | {length} | {height} | "
            f"{external} | {load_bearing} | {drywall} |"
        )

    return "\n".join(lines)


def _format_room_schedule_markdown(result: Any) -> str:
    """Format room schedule as markdown."""
    lines = [
        "# Room Schedule (Raumbuch)",
        "",
        f"**Total Rooms:** {result.total_count}",
    ]

    if result.total_area_m2:
        lines.append(f"**Total Area:** {result.total_area_m2:.2f} m\u00b2")
    if result.total_volume_m3:
        lines.append(f"**Total Volume:** {result.total_volume_m3:.2f} m\u00b3")

    lines.extend([
        "",
        "| Number | Name | Storey | Area (m\u00b2) | Volume (m\u00b3) | Floor Finish |"
    ])
    lines.append("|--------|------|--------|-----------|-------------|--------------|")

    for item in result.items[:100]:
        area = f"{item.area_m2:.2f}" if item.area_m2 else "-"
        volume = f"{item.volume_m3:.2f}" if item.volume_m3 else "-"
        finish = item.properties.get("finish_floor", "-")

        lines.append(
            f"| {item.tag or '-'} | {item.name or '-'} | "
            f"{item.storey_name or '-'} | {area} | {volume} | {finish} |"
        )

    return "\n".join(lines)
