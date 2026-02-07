"""Project MCP Tools.

Tools for managing IFC projects.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.types import TextContent, Tool

from ifc_mcp.infrastructure.ifc.import_service import IfcImportService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


def register_project_tools(server: Server) -> None:
    """Register project-related MCP tools.

    Args:
        server: MCP Server instance
    """

    @server.list_tools()
    async def list_project_tools() -> list[Tool]:
        """List available project tools."""
        return [
            Tool(
                name="ifc_import_file",
                description="Import an IFC file into the database. Returns project ID on success.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the IFC file to import",
                        },
                        "project_name": {
                            "type": "string",
                            "description": "Optional custom project name (defaults to filename)",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="ifc_list_projects",
                description="List all imported IFC projects.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_deleted": {
                            "type": "boolean",
                            "description": "Include soft-deleted projects",
                            "default": False,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 50,
                        },
                    },
                },
            ),
            Tool(
                name="ifc_get_project",
                description="Get detailed information about a specific project.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            Tool(
                name="ifc_delete_project",
                description="Delete an IFC project and all its data.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID to delete",
                        },
                        "hard_delete": {
                            "type": "boolean",
                            "description": "Permanently delete (default: soft delete)",
                            "default": False,
                        },
                    },
                    "required": ["project_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_project_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle project tool calls."""
        try:
            if name == "ifc_import_file":
                return await _import_file(arguments)
            elif name == "ifc_list_projects":
                return await _list_projects(arguments)
            elif name == "ifc_get_project":
                return await _get_project(arguments)
            elif name == "ifc_delete_project":
                return await _delete_project(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error("Tool error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _import_file(args: dict[str, Any]) -> list[TextContent]:
    """Import an IFC file."""
    file_path = Path(args["file_path"])
    project_name = args.get("project_name")

    if not file_path.exists():
        return [TextContent(type="text", text=f"File not found: {file_path}")]

    async with UnitOfWork() as uow:
        service = IfcImportService(uow)
        project = await service.import_file(
            file_path=file_path,
            project_name=project_name,
        )
        await uow.commit()

    result = {
        "status": "success",
        "project_id": str(project.id),
        "project_name": project.name,
        "schema_version": project.schema_version.value,
        "storey_count": len(project.storeys),
        "element_count": project.element_count,
        "space_count": project.space_count,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _list_projects(args: dict[str, Any]) -> list[TextContent]:
    """List all projects."""
    include_deleted = args.get("include_deleted", False)
    limit = args.get("limit", 50)

    async with UnitOfWork() as uow:
        projects = await uow.projects.list_all(
            include_deleted=include_deleted,
            limit=limit,
        )

    result = {
        "total": len(projects),
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "schema_version": p.schema_version.value,
                "storey_count": len(p.storeys),
                "imported_at": p.imported_at.isoformat(),
                "is_deleted": p.is_deleted,
            }
            for p in projects
        ],
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_project(args: dict[str, Any]) -> list[TextContent]:
    """Get project details."""
    project_id = UUID(args["project_id"])

    async with UnitOfWork() as uow:
        project = await uow.projects.get_by_id(project_id)

        if project is None:
            return [TextContent(type="text", text=f"Project not found: {project_id}")]

        # Get counts
        element_count = await uow.elements.count_by_project(project_id)
        space_count = await uow.spaces.count_by_project(project_id)

    result = {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "schema_version": project.schema_version.value,
        "authoring_app": project.authoring_app,
        "author": project.author,
        "organization": project.organization,
        "original_file_path": project.original_file_path,
        "imported_at": project.imported_at.isoformat(),
        "storeys": [
            {
                "id": str(s.id),
                "name": s.name,
                "elevation": s.elevation,
            }
            for s in project.storeys
        ],
        "element_count": element_count,
        "space_count": space_count,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _delete_project(args: dict[str, Any]) -> list[TextContent]:
    """Delete a project."""
    project_id = UUID(args["project_id"])
    hard_delete = args.get("hard_delete", False)

    async with UnitOfWork() as uow:
        success = await uow.projects.delete(project_id, hard=hard_delete)
        await uow.commit()

    if success:
        delete_type = "permanently deleted" if hard_delete else "soft-deleted"
        return [TextContent(type="text", text=f"Project {project_id} {delete_type}")]
    else:
        return [TextContent(type="text", text=f"Project not found: {project_id}")]
