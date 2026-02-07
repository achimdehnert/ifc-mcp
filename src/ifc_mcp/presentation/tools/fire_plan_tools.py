"""Fire Plan MCP Tools.

Tools for generating SVG-based fire safety plans.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.types import TextContent, Tool

from ifc_mcp.application.services.fire_compartment_service import (
    FireCompartmentMapConfig,
    FireCompartmentMapService,
)
from ifc_mcp.application.services.fire_escape_plan_service import (
    FireEscapePlanConfig,
    FireEscapePlanService,
)
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)

SVG_OUTPUT_DIR = Path("/tmp/ifc_svg")


def register_fire_plan_tools(server: Server) -> None:
    """Register fire plan MCP tools.

    Args:
        server: MCP Server instance
    """

    @server.list_tools()
    async def list_fire_plan_tools() -> list[Tool]:
        """List available fire plan tools."""
        return [
            Tool(
                name="ifc_floor_plan_svg",
                description="Generate an SVG floor plan from IFC model data for a specific storey.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "storey_id": {
                            "type": "string",
                            "description": "Storey UUID",
                        },
                        "width": {
                            "type": "number",
                            "description": "SVG width in pixels (default: 1200)",
                            "default": 1200,
                        },
                        "height": {
                            "type": "number",
                            "description": "SVG height in pixels (default: 900)",
                            "default": 900,
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename (default: auto-generated)",
                        },
                    },
                    "required": ["project_id", "storey_id"],
                },
            ),
            Tool(
                name="ifc_fire_escape_plan",
                description="Generate a fire escape plan (Flucht- und Rettungsplan) according to DIN ISO 23601.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "storey_id": {
                            "type": "string",
                            "description": "Storey UUID",
                        },
                        "title": {
                            "type": "string",
                            "description": "Plan title (default: Flucht- und Rettungsplan)",
                        },
                        "show_behavior_instructions": {
                            "type": "boolean",
                            "description": "Include behavior instructions panel",
                            "default": True,
                        },
                        "you_are_here_x": {
                            "type": "number",
                            "description": "X coordinate for 'You are here' marker",
                        },
                        "you_are_here_y": {
                            "type": "number",
                            "description": "Y coordinate for 'You are here' marker",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename",
                        },
                    },
                    "required": ["project_id", "storey_id"],
                },
            ),
            Tool(
                name="ifc_fire_compartment_map",
                description="Generate a fire compartment map (Brandabschnittsplan) showing fire-rated walls and doors.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "storey_id": {
                            "type": "string",
                            "description": "Storey UUID",
                        },
                        "show_fire_ratings": {
                            "type": "boolean",
                            "description": "Show fire rating labels on elements",
                            "default": True,
                        },
                        "highlight_critical": {
                            "type": "boolean",
                            "description": "Highlight F90+ critical fire elements",
                            "default": True,
                        },
                        "filename": {
                            "type": "string",
                            "description": "Output filename",
                        },
                    },
                    "required": ["project_id", "storey_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_fire_plan_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle fire plan tool calls."""
        try:
            if name == "ifc_floor_plan_svg":
                return await _floor_plan_svg(arguments)
            elif name == "ifc_fire_escape_plan":
                return await _fire_escape_plan(arguments)
            elif name == "ifc_fire_compartment_map":
                return await _fire_compartment_map(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error("Fire plan tool error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {str(e)}")]


def _ensure_svg_dir() -> Path:
    """Ensure SVG output directory exists."""
    SVG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return SVG_OUTPUT_DIR


async def _floor_plan_svg(args: dict[str, Any]) -> list[TextContent]:
    """Generate floor plan SVG."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"])

    output_dir = _ensure_svg_dir()
    filename = args.get("filename", f"floor_plan_{str(storey_id)[:8]}.svg")
    if not filename.endswith(".svg"):
        filename += ".svg"
    output_path = output_dir / filename

    config = FireEscapePlanConfig(
        width=args.get("width", 1200),
        height=args.get("height", 900),
        title="Floor Plan",
        show_escape_routes=False,
        show_assembly_point=False,
        show_fire_extinguishers=False,
        show_fire_alarms=False,
        show_first_aid=False,
        show_you_are_here=False,
        show_behavior_instructions=False,
    )

    async with UnitOfWork() as uow:
        service = FireEscapePlanService(uow)
        result = await service.generate_escape_plan(
            project_id, storey_id, config=config, output_path=output_path,
        )

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "storey_name": result.storey_name,
        "svg_length": len(result.svg_content),
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def _fire_escape_plan(args: dict[str, Any]) -> list[TextContent]:
    """Generate fire escape plan."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"])

    output_dir = _ensure_svg_dir()
    filename = args.get("filename", f"escape_plan_{str(storey_id)[:8]}.svg")
    if not filename.endswith(".svg"):
        filename += ".svg"
    output_path = output_dir / filename

    config = FireEscapePlanConfig(
        title=args.get("title", "Flucht- und Rettungsplan"),
        show_behavior_instructions=args.get("show_behavior_instructions", True),
    )

    if args.get("you_are_here_x") is not None:
        config.you_are_here_x = args["you_are_here_x"]
    if args.get("you_are_here_y") is not None:
        config.you_are_here_y = args["you_are_here_y"]

    async with UnitOfWork() as uow:
        service = FireEscapePlanService(uow)
        result = await service.generate_escape_plan(
            project_id, storey_id, config=config, output_path=output_path,
        )

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "storey_name": result.storey_name,
        "escape_route_count": result.escape_route_count,
        "equipment_count": result.equipment_count,
        "svg_length": len(result.svg_content),
        "message": (
            f"Fire escape plan generated with {result.escape_route_count} routes "
            f"and {result.equipment_count} safety equipment items"
        ),
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def _fire_compartment_map(args: dict[str, Any]) -> list[TextContent]:
    """Generate fire compartment map."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"])

    output_dir = _ensure_svg_dir()
    filename = args.get("filename", f"compartment_map_{str(storey_id)[:8]}.svg")
    if not filename.endswith(".svg"):
        filename += ".svg"
    output_path = output_dir / filename

    config = FireCompartmentMapConfig(
        show_fire_ratings=args.get("show_fire_ratings", True),
        highlight_critical=args.get("highlight_critical", True),
    )

    async with UnitOfWork() as uow:
        service = FireCompartmentMapService(uow)
        result = await service.generate_compartment_map(
            project_id, storey_id, config=config, output_path=output_path,
        )

    response = {
        "status": "success",
        "file_path": str(result.file_path),
        "storey_name": result.storey_name,
        "compartment_count": result.compartment_count,
        "fire_wall_count": result.fire_wall_count,
        "fire_door_count": result.fire_door_count,
        "svg_length": len(result.svg_content),
        "message": (
            f"Fire compartment map: {result.compartment_count} compartments, "
            f"{result.fire_wall_count} fire walls, {result.fire_door_count} fire doors"
        ),
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]
