"""Explosion Protection MCP Tools.

Tools for ATEX zone analysis, fire ratings, room volumes, and hazardous areas.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.types import TextContent, Tool

from ifc_mcp.application.services import ExProtectionService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def register_ex_protection_tools(server: Server) -> None:
    """Register explosion protection MCP tools.

    Args:
        server: MCP Server instance
    """

    @server.list_tools()
    async def list_ex_protection_tools() -> list[Tool]:
        """List available ex-protection tools."""
        return [
            Tool(
                name="ifc_ex_zone_analysis",
                description="Perform ATEX explosion protection zone classification analysis.",
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
                name="ifc_fire_rating_report",
                description="Generate a fire rating report for all elements with fire classifications.",
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
                name="ifc_room_volume_analysis",
                description="Analyze room volumes for ventilation and safety calculations.",
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
                name="ifc_hazardous_areas",
                description="Identify hazardous areas and safety issues in the building model.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
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
    async def call_ex_protection_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle ex-protection tool calls."""
        try:
            if name == "ifc_ex_zone_analysis":
                return await _ex_zone_analysis(arguments)
            elif name == "ifc_fire_rating_report":
                return await _fire_rating_report(arguments)
            elif name == "ifc_room_volume_analysis":
                return await _room_volume_analysis(arguments)
            elif name == "ifc_hazardous_areas":
                return await _hazardous_areas(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error("Ex-protection tool error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _ex_zone_analysis(args: dict[str, Any]) -> list[TextContent]:
    """Perform ATEX zone analysis."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        result = await service.analyze_ex_zones(
            project_id, storey_id=storey_id,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(result.to_dict(), cls=DecimalEncoder, indent=2),
        )]

    # Markdown
    lines = [
        f"# ATEX Zone Analysis: {result.project_name}",
        "",
        f"**Total Spaces Analyzed:** {result.total_spaces}",
        f"**Hazardous Spaces:** {result.hazardous_count}",
        "",
    ]

    if result.zones:
        lines.extend(["## Zone Classification", ""])
        lines.append("| Space | Zone | Classification | Substances |")
        lines.append("|-------|------|----------------|------------|")

        for zone in result.zones:
            lines.append(
                f"| {zone.space_name} | {zone.zone_type} | "
                f"{zone.classification} | {zone.substances or '-'} |"
            )

    if result.recommendations:
        lines.extend(["", "## Recommendations"])
        for rec in result.recommendations:
            lines.append(f"- {rec}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _fire_rating_report(args: dict[str, Any]) -> list[TextContent]:
    """Generate fire rating report."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        result = await service.generate_fire_rating_report(
            project_id, storey_id=storey_id,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(result.to_dict(), cls=DecimalEncoder, indent=2),
        )]

    lines = [
        f"# Fire Rating Report: {result.project_name}",
        "",
        f"**Elements with Fire Rating:** {result.rated_count} / {result.total_count}",
        "",
    ]

    if result.rating_summary:
        lines.extend(["## Fire Ratings Summary", ""])
        lines.append("| Rating | Count | Element Types |")
        lines.append("|--------|-------|---------------|")

        for rating, info in result.rating_summary.items():
            lines.append(
                f"| {rating} | {info['count']} | {', '.join(info['types'])} |"
            )

    return [TextContent(type="text", text="\n".join(lines))]


async def _room_volume_analysis(args: dict[str, Any]) -> list[TextContent]:
    """Analyze room volumes."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        result = await service.analyze_room_volumes(
            project_id, storey_id=storey_id,
        )

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(result.to_dict(), cls=DecimalEncoder, indent=2),
        )]

    lines = [
        f"# Room Volume Analysis: {result.project_name}",
        "",
        f"**Total Rooms:** {result.total_rooms}",
        f"**Total Volume:** {result.total_volume_m3:.2f} m\u00b3",
        f"**Total Area:** {result.total_area_m2:.2f} m\u00b2",
        "",
        "| Room | Area (m\u00b2) | Height (m) | Volume (m\u00b3) |",
        "|------|-----------|------------|-------------|",
    ]

    for room in result.rooms[:50]:
        lines.append(
            f"| {room.name} | {room.area_m2:.2f} | "
            f"{room.height_m:.2f} | {room.volume_m3:.2f} |"
        )

    if result.total_rooms > 50:
        lines.append(f"\n*... and {result.total_rooms - 50} more rooms*")

    return [TextContent(type="text", text="\n".join(lines))]


async def _hazardous_areas(args: dict[str, Any]) -> list[TextContent]:
    """Identify hazardous areas."""
    project_id = UUID(args["project_id"])
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        result = await service.identify_hazardous_areas(project_id)

    if fmt == "json":
        return [TextContent(
            type="text",
            text=json.dumps(result.to_dict(), cls=DecimalEncoder, indent=2),
        )]

    lines = [
        f"# Hazardous Areas Analysis: {result.project_name}",
        "",
        f"**Total Hazardous Areas:** {result.hazardous_count}",
        f"**Risk Level:** {result.overall_risk_level}",
        "",
    ]

    if result.areas:
        lines.extend(["## Identified Areas", ""])
        for area in result.areas:
            lines.append(f"### {area.name}")
            lines.append(f"- **Type:** {area.hazard_type}")
            lines.append(f"- **Risk:** {area.risk_level}")
            if area.mitigation:
                lines.append(f"- **Mitigation:** {area.mitigation}")
            lines.append("")

    if result.recommendations:
        lines.extend(["## Recommendations"])
        for rec in result.recommendations:
            lines.append(f"- {rec}")

    return [TextContent(type="text", text="\n".join(lines))]
