"""Analysis MCP Tools.

Tools for model quality checks, material takeoffs, and accessibility.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.types import TextContent, Tool

from ifc_mcp.application.services.accessibility_check_service import (
    AccessibilityCheckService,
    AccessibilityStandard,
    ComplianceLevel,
)
from ifc_mcp.application.services.material_takeoff_service import MaterialTakeoffService
from ifc_mcp.application.services.model_check_service import CheckSeverity, ModelCheckService
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


def register_analysis_tools(server: Server) -> None:
    """Register analysis MCP tools.

    Args:
        server: MCP Server instance
    """

    @server.list_tools()
    async def list_analysis_tools() -> list[Tool]:
        """List available analysis tools."""
        return [
            Tool(
                name="ifc_material_takeoff",
                description="Generate a material takeoff (Mengenermittlung) from the IFC model with DIN 276 cost groups.",
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
                        "detail_level": {
                            "type": "string",
                            "enum": ["summary", "detailed", "full"],
                            "default": "detailed",
                            "description": "Level of detail in output",
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
                name="ifc_model_check",
                description="Run quality checks on the IFC model (geometry, properties, relationships, naming, consistency).",
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
                        "severity_filter": {
                            "type": "string",
                            "enum": ["all", "errors", "warnings", "errors_and_warnings"],
                            "default": "all",
                            "description": "Filter results by severity",
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
                name="ifc_accessibility_check",
                description="Check IFC model for accessibility compliance (DIN 18040-1 public / DIN 18040-2 residential).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID",
                        },
                        "standard": {
                            "type": "string",
                            "enum": ["DIN 18040-1", "DIN 18040-2"],
                            "default": "DIN 18040-1",
                            "description": "Accessibility standard to check against",
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
    async def call_analysis_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle analysis tool calls."""
        try:
            if name == "ifc_material_takeoff":
                return await _material_takeoff(arguments)
            elif name == "ifc_model_check":
                return await _model_check(arguments)
            elif name == "ifc_accessibility_check":
                return await _accessibility_check(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error("Analysis tool error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _material_takeoff(args: dict[str, Any]) -> list[TextContent]:
    """Generate material takeoff."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    detail_level = args.get("detail_level", "detailed")
    fmt = args.get("format", "markdown")

    include_breakdown = detail_level in ("detailed", "full")

    async with UnitOfWork() as uow:
        service = MaterialTakeoffService(uow)
        result = await service.generate_takeoff(
            project_id,
            storey_id=storey_id,
            include_breakdown=include_breakdown,
        )

    if fmt == "json":
        data = {
            "project_name": result.project_name,
            "total_elements": result.total_elements,
            "total_positions": result.total_positions,
            "summary": {
                "wall_area_m2": result.total_wall_area_m2,
                "floor_area_m2": result.total_floor_area_m2,
                "window_area_m2": result.total_window_area_m2,
                "door_count": result.total_door_count,
                "room_volume_m3": result.total_room_volume_m3,
            },
            "categories": [
                {
                    "name": cat.name,
                    "cost_group": cat.cost_group.value if cat.cost_group else None,
                    "total_quantity": cat.total_quantity,
                    "element_count": cat.element_count,
                    "items": [
                        {
                            "position": item.position,
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit": item.unit.value,
                            "element_count": item.element_count,
                        }
                        for item in cat.items
                    ] if detail_level != "summary" else [],
                }
                for cat in result.categories
            ],
        }
        return [TextContent(
            type="text",
            text=json.dumps(data, cls=DecimalEncoder, indent=2),
        )]

    # Markdown format
    lines = [
        f"# Material Takeoff: {result.project_name}",
        "",
        f"**Total Elements:** {result.total_elements}",
        f"**Total Positions:** {result.total_positions}",
        "",
        "## Summary",
        f"- **Wall Area:** {result.total_wall_area_m2:.2f} m\u00b2",
        f"- **Floor Area:** {result.total_floor_area_m2:.2f} m\u00b2",
        f"- **Window Area:** {result.total_window_area_m2:.2f} m\u00b2",
        f"- **Door Count:** {result.total_door_count}",
        f"- **Room Volume:** {result.total_room_volume_m3:.2f} m\u00b3",
    ]

    for cat in result.categories:
        lines.extend([
            "",
            f"## {cat.name}",
            f"**Elements:** {cat.element_count} | "
            f"**Total:** {cat.total_quantity:.2f}",
        ])

        if detail_level != "summary" and cat.items:
            lines.extend(["", "| Pos | Description | Qty | Unit | Count |"])
            lines.append("|-----|-------------|-----|------|-------|") 
            for item in cat.items:
                lines.append(
                    f"| {item.position} | {item.description} | "
                    f"{item.quantity:.2f} | {item.unit.value} | {item.element_count} |"
                )

    return [TextContent(type="text", text="\n".join(lines))]


async def _model_check(args: dict[str, Any]) -> list[TextContent]:
    """Run model quality checks."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    severity_filter = args.get("severity_filter", "all")
    fmt = args.get("format", "markdown")

    async with UnitOfWork() as uow:
        service = ModelCheckService(uow)
        result = await service.run_all_checks(project_id, storey_id=storey_id)

    # Filter results
    filtered = result.results
    if severity_filter == "errors":
        filtered = [r for r in filtered if r.severity == CheckSeverity.ERROR]
    elif severity_filter == "warnings":
        filtered = [r for r in filtered if r.severity == CheckSeverity.WARNING]
    elif severity_filter == "errors_and_warnings":
        filtered = [
            r for r in filtered
            if r.severity in (CheckSeverity.ERROR, CheckSeverity.WARNING)
        ]

    if fmt == "json":
        data = {
            "project_name": result.project_name,
            "summary": {
                "total_checks": result.summary.total_checks,
                "passed": result.summary.passed,
                "errors": result.summary.errors,
                "warnings": result.summary.warnings,
                "info": result.summary.info,
                "pass_rate": result.summary.pass_rate,
            },
            "results": [
                {
                    "check_id": r.check_id,
                    "name": r.name,
                    "category": r.category.value,
                    "severity": r.severity.value,
                    "message": r.message,
                    "element_count": r.element_count,
                }
                for r in filtered
            ],
        }
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    # Markdown
    severity_icons = {
        "error": "\u274c",
        "warning": "\u26a0\ufe0f",
        "info": "\u2139\ufe0f",
        "passed": "\u2705",
    }

    lines = [
        f"# Model Check: {result.project_name}",
        "",
        f"**Pass Rate:** {result.summary.pass_rate:.0f}%",
        f"**Results:** {result.summary.passed} passed, "
        f"{result.summary.errors} errors, "
        f"{result.summary.warnings} warnings, "
        f"{result.summary.info} info",
        "",
    ]

    current_category = None
    for r in filtered:
        if r.category != current_category:
            current_category = r.category
            lines.extend(["", f"## {r.category.value.title()}"])

        icon = severity_icons.get(r.severity.value, "")
        lines.append(f"- {icon} **{r.check_id}** {r.name}: {r.message}")

        if r.element_count > 0:
            lines.append(f"  - Affected elements: {r.element_count}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _accessibility_check(args: dict[str, Any]) -> list[TextContent]:
    """Run accessibility check."""
    project_id = UUID(args["project_id"])
    storey_id = UUID(args["storey_id"]) if args.get("storey_id") else None
    standard_str = args.get("standard", "DIN 18040-1")
    fmt = args.get("format", "markdown")

    standard = AccessibilityStandard(standard_str)

    async with UnitOfWork() as uow:
        service = AccessibilityCheckService(uow)
        result = await service.check_accessibility(
            project_id,
            standard=standard,
            storey_id=storey_id,
        )

    if fmt == "json":
        data = {
            "project_name": result.project_name,
            "standard": result.standard.value,
            "summary": {
                "total_checks": result.summary.total_checks,
                "compliant": result.summary.compliant,
                "non_compliant": result.summary.non_compliant,
                "partially_compliant": result.summary.partially_compliant,
                "insufficient_data": result.summary.insufficient_data,
                "compliance_rate": result.summary.compliance_rate,
            },
            "checks": [
                {
                    "check_id": c.check_id,
                    "name": c.name,
                    "section": c.section,
                    "compliance": c.compliance.value,
                    "message": c.message,
                    "measured_value": c.measured_value,
                    "required_value": c.required_value,
                    "unit": c.unit,
                    "recommendations": c.recommendations,
                }
                for c in result.checks
            ],
        }
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    # Markdown
    compliance_icons = {
        ComplianceLevel.COMPLIANT: "\u2705",
        ComplianceLevel.NON_COMPLIANT: "\u274c",
        ComplianceLevel.PARTIALLY_COMPLIANT: "\u26a0\ufe0f",
        ComplianceLevel.INSUFFICIENT_DATA: "\u2753",
        ComplianceLevel.NOT_APPLICABLE: "\u2796",
    }

    lines = [
        f"# Accessibility Check: {result.project_name}",
        f"**Standard:** {result.standard.value}",
        "",
        f"**Compliance Rate:** {result.summary.compliance_rate:.0f}%",
        f"**Results:** {result.summary.compliant} compliant, "
        f"{result.summary.non_compliant} non-compliant, "
        f"{result.summary.partially_compliant} partial, "
        f"{result.summary.insufficient_data} insufficient data",
        "",
    ]

    for check in result.checks:
        icon = compliance_icons.get(check.compliance, "")
        lines.append(f"### {icon} {check.name} ({check.section})")
        lines.append(f"**Requirement:** {check.requirement}")
        lines.append(f"**Status:** {check.message}")

        if check.measured_value is not None and check.required_value is not None:
            lines.append(
                f"**Measured:** {check.measured_value} {check.unit or ''} "
                f"(Required: {check.required_value} {check.unit or ''})"
            )

        if check.recommendations:
            lines.append("\n**Recommendations:**")
            for rec in check.recommendations:
                lines.append(f"- {rec}")

        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]
