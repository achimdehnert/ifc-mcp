"""Fire Escape Plan Service.

Generates fire escape plans (Flucht- und Rettungspläne) according to DIN ISO 23601.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from ifc_mcp.application.services.svg_generator import (
    BoundingBox,
    Point2D,
    SVGCircle,
    SVGDocument,
    SVGGroup,
    SVGLine,
    SVGPath,
    SVGPolygon,
    SVGRect,
    SVGStyle,
    SVGText,
    STYLE_DOOR,
    STYLE_DOOR_FIRE,
    STYLE_ESCAPE_ROUTE,
    STYLE_SPACE,
    STYLE_SPACE_EX,
    STYLE_WALL,
    STYLE_WALL_FIRE,
    STYLE_WINDOW,
)
from ifc_mcp.application.services.fire_symbols import (
    FIRE_SYMBOLS,
    get_symbols_defs,
    use_symbol,
)
from ifc_mcp.domain import BuildingElement, ElementCategory, Space
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# DIN ISO 23601 Color Standards
# =============================================================================

COLOR_ESCAPE_GREEN = "#009639"  # RAL 6032 - Escape routes
COLOR_FIRE_RED = "#CC0000"  # RAL 3001 - Fire equipment
COLOR_WARNING_YELLOW = "#FFB800"  # RAL 1003 - Warnings
COLOR_INFO_BLUE = "#0066B3"  # RAL 5015 - Information
COLOR_BACKGROUND = "#FFFFFF"
COLOR_WALL = "#333333"
COLOR_SPACE = "#F0F0F0"


@dataclass
class EscapeRoute:
    """Escape route definition."""

    id: str
    points: list[Point2D]
    is_primary: bool = True
    width_m: float = 1.2  # Min 1.2m according to regulations


@dataclass
class SafetyEquipment:
    """Safety equipment location."""

    id: str
    symbol_id: str  # Reference to fire_symbols
    position: Point2D
    label: str | None = None


@dataclass
class FireEscapePlanConfig:
    """Configuration for fire escape plan generation."""

    # Output size (DIN ISO 23601: A3 or A4)
    width: float = 1189  # A3 landscape width in mm (scaled to px)
    height: float = 841  # A3 landscape height in mm

    # Scale
    scale: float = 100.0  # pixels per meter

    # Margins
    margin: float = 80.0

    # Content options
    show_escape_routes: bool = True
    show_assembly_point: bool = True
    show_fire_extinguishers: bool = True
    show_fire_alarms: bool = True
    show_first_aid: bool = True
    show_you_are_here: bool = True

    # Position for "You are here" marker
    you_are_here_x: float | None = None
    you_are_here_y: float | None = None

    # Labels
    title: str = "Flucht- und Rettungsplan"
    subtitle: str = ""
    building_name: str = ""
    floor_name: str = ""

    # Behavior instructions
    show_behavior_instructions: bool = True


@dataclass
class FireEscapePlanResult:
    """Result of fire escape plan generation."""

    svg_content: str
    file_path: Path | None = None
    storey_name: str | None = None
    escape_route_count: int = 0
    equipment_count: int = 0


class FireEscapePlanService:
    """Service for generating fire escape plans."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service."""
        self._uow = uow

    async def generate_escape_plan(
        self,
        project_id: UUID,
        storey_id: UUID,
        config: FireEscapePlanConfig | None = None,
        output_path: Path | None = None,
    ) -> FireEscapePlanResult:
        """Generate fire escape plan for a storey.

        Args:
            project_id: Project UUID
            storey_id: Storey UUID
            config: Optional configuration
            output_path: Optional output file path

        Returns:
            FireEscapePlanResult with SVG content
        """
        if config is None:
            config = FireEscapePlanConfig()

        # Get storey info
        storeys = await self._uow.storeys.get_by_project(project_id)
        storey = next((s for s in storeys if s.id == storey_id), None)
        storey_name = storey.name if storey else "Unknown"

        if not config.floor_name:
            config.floor_name = storey_name

        # Get project info
        project = await self._uow.projects.get(project_id)
        if project and not config.building_name:
            config.building_name = project.name

        # Get elements for this storey
        elements = await self._uow.elements.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=10000,
        )

        # Get spaces
        spaces = await self._uow.spaces.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=1000,
        )

        # Calculate bounding box
        bbox = self._calculate_bounding_box(elements, spaces)
        if not bbox:
            bbox = BoundingBox(0, 0, 30, 20)

        # Create SVG document
        svg = self._create_escape_plan_document(bbox, config)

        # Add symbol definitions
        svg.add_def(get_symbols_defs())

        # Track counts
        escape_route_count = 0
        equipment_count = 0

        # 1. Background floor plan
        floor_plan_group = SVGGroup(element_id="floor_plan")
        await self._add_floor_plan(floor_plan_group, elements, spaces, bbox, config)
        svg.add(floor_plan_group)

        # 2. Escape routes
        if config.show_escape_routes:
            routes_group = SVGGroup(element_id="escape_routes")
            escape_route_count = await self._add_escape_routes(
                routes_group, elements, spaces, bbox, config
            )
            svg.add(routes_group)

        # 3. Safety equipment
        equipment_group = SVGGroup(element_id="safety_equipment")
        equipment_count = await self._add_safety_equipment(
            equipment_group, elements, bbox, config
        )
        svg.add(equipment_group)

        # 4. "You are here" marker
        if config.show_you_are_here:
            self._add_you_are_here_marker(svg, bbox, config)

        # 5. Title block
        self._add_title_block(svg, config)

        # 6. Legend
        self._add_escape_plan_legend(svg, config)

        # 7. Behavior instructions
        if config.show_behavior_instructions:
            self._add_behavior_instructions(svg, config)

        # Render SVG
        svg_content = svg.render()

        # Save to file
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(svg_content, encoding="utf-8")

        return FireEscapePlanResult(
            svg_content=svg_content,
            file_path=output_path,
            storey_name=storey_name,
            escape_route_count=escape_route_count,
            equipment_count=equipment_count,
        )

    def _calculate_bounding_box(
        self,
        elements: list[BuildingElement],
        spaces: list[Space],
    ) -> BoundingBox | None:
        """Calculate bounding box from elements and spaces."""
        points = []

        for elem in elements:
            if elem.position_x is not None and elem.position_y is not None:
                x = float(elem.position_x)
                y = float(elem.position_y)
                points.append(Point2D(x, y))

                if elem.length_m:
                    points.append(Point2D(x + float(elem.length_m), y))
                if elem.width_m:
                    points.append(Point2D(x, y + float(elem.width_m)))

        if not points:
            return None

        return BoundingBox.from_points(points)

    def _create_escape_plan_document(
        self,
        bbox: BoundingBox,
        config: FireEscapePlanConfig,
    ) -> SVGDocument:
        """Create SVG document for escape plan."""
        # Calculate viewbox with margins
        expanded = bbox.expand(config.margin / config.scale)

        viewbox = BoundingBox(
            min_x=expanded.min_x,
            min_y=-expanded.max_y,
            max_x=expanded.max_x,
            max_y=-expanded.min_y,
        )

        return SVGDocument(
            width=config.width,
            height=config.height,
            viewbox=viewbox,
            title=config.title,
            background_color=COLOR_BACKGROUND,
        )

    async def _add_floor_plan(
        self,
        group: SVGGroup,
        elements: list[BuildingElement],
        spaces: list[Space],
        bbox: BoundingBox,
        config: FireEscapePlanConfig,
    ) -> None:
        """Add simplified floor plan."""
        # Add spaces first (background)
        for space in spaces:
            self._add_space(group, space, bbox)

        # Add walls
        walls = [e for e in elements if e.category in (
            ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE
        )]
        for wall in walls:
            self._add_wall(group, wall, config)

        # Add doors (important for escape routes)
        doors = [e for e in elements if e.category == ElementCategory.DOOR]
        for door in doors:
            self._add_door(group, door, config)

    def _add_space(self, group: SVGGroup, space: Space, bbox: BoundingBox) -> None:
        """Add space to floor plan."""
        if space.net_floor_area:
            side = float(space.net_floor_area) ** 0.5
            x = bbox.center.x - side / 2
            y = bbox.center.y - side / 2

            # Hazardous spaces get different color
            fill_color = "#FFCCCC" if space.is_hazardous else COLOR_SPACE

            rect = SVGRect(
                x=x,
                y=-y - side,
                width=side,
                height=side,
                style=SVGStyle(fill=fill_color, stroke="#CCCCCC", stroke_width=0.3),
                title=space.display_name,
            )
            group.add(rect)

            # Space label
            if space.space_number or space.name:
                label = SVGText(
                    x=x + side / 2,
                    y=-y - side / 2,
                    text=space.space_number or space.name or "",
                    anchor="middle",
                    style=SVGStyle(font_size=6, fill="#333333"),
                )
                group.add(label)

    def _add_wall(
        self,
        group: SVGGroup,
        wall: BuildingElement,
        config: FireEscapePlanConfig,
    ) -> None:
        """Add wall to floor plan."""
        if wall.position_x is None or wall.position_y is None:
            return

        x = float(wall.position_x)
        y = float(wall.position_y)
        length = float(wall.length_m) if wall.length_m else 1.0
        width = float(wall.width_m) if wall.width_m else 0.2

        # Fire-rated walls shown differently
        has_fire_rating = wall.fire_rating is not None
        style = STYLE_WALL_FIRE if has_fire_rating else STYLE_WALL

        rect = SVGRect(
            x=x,
            y=-y - width,
            width=length,
            height=width,
            style=style,
            title=f"{wall.name or 'Wall'} - {wall.fire_rating or 'Standard'}",
        )
        group.add(rect)

    def _add_door(
        self,
        group: SVGGroup,
        door: BuildingElement,
        config: FireEscapePlanConfig,
    ) -> None:
        """Add door to floor plan."""
        if door.position_x is None or door.position_y is None:
            return

        x = float(door.position_x)
        y = float(door.position_y)
        width = float(door.width_m) if door.width_m else 0.9
        depth = 0.1

        has_fire_rating = door.fire_rating is not None
        style = STYLE_DOOR_FIRE if has_fire_rating else STYLE_DOOR

        rect = SVGRect(
            x=x,
            y=-y - depth,
            width=width,
            height=depth,
            style=style,
            title=f"{door.name or 'Door'} - {door.fire_rating or 'Standard'}",
        )
        group.add(rect)

    async def _add_escape_routes(
        self,
        group: SVGGroup,
        elements: list[BuildingElement],
        spaces: list[Space],
        bbox: BoundingBox,
        config: FireEscapePlanConfig,
    ) -> int:
        """Add escape routes to plan.

        In a real implementation, escape routes would be:
        1. Calculated using pathfinding from each space to exits
        2. Stored as IfcPath or custom properties
        3. Retrieved from IFC model

        For now, we generate indicative routes based on door positions.
        """
        route_count = 0

        # Find exit doors (doors with certain properties or at building perimeter)
        doors = [e for e in elements if e.category == ElementCategory.DOOR]
        exit_doors = [d for d in doors if self._is_exit_door(d)]

        if not exit_doors:
            # If no exit doors identified, use all exterior-facing doors
            exit_doors = doors[:3]  # Fallback

        # Create escape route indicators from center to each exit
        center = bbox.center

        for i, exit_door in enumerate(exit_doors):
            if exit_door.position_x is None or exit_door.position_y is None:
                continue

            exit_x = float(exit_door.position_x)
            exit_y = float(exit_door.position_y)

            # Create escape route path
            route_path = self._create_escape_route_path(
                Point2D(center.x, center.y),
                Point2D(exit_x, exit_y),
            )

            path = SVGPath(
                d=route_path,
                style=STYLE_ESCAPE_ROUTE,
                element_id=f"escape_route_{i}",
                title=f"Fluchtweg {i + 1}",
            )
            group.add(path)

            # Add exit symbol at door
            group.add(SVGText(
                x=exit_x,
                y=-exit_y - 2,
                text="",  # Will use symbol instead
                style=SVGStyle(font_size=8),
            ))

            # Add exit arrow symbol
            symbol_use = use_symbol(
                "E002" if exit_x > center.x else "E001",
                exit_x - 20,
                -exit_y - 50,
                40,
                40,
            )
            # Parse and add as raw SVG
            group.children.append(_RawSVG(symbol_use))

            route_count += 1

        return route_count

    def _is_exit_door(self, door: BuildingElement) -> bool:
        """Check if door is an exit door."""
        # Check common indicators
        name_lower = (door.name or "").lower()
        exit_indicators = ["exit", "ausgang", "notausgang", "flucht", "emergency"]
        return any(ind in name_lower for ind in exit_indicators)

    def _create_escape_route_path(self, start: Point2D, end: Point2D) -> str:
        """Create SVG path for escape route."""
        # Simple direct path (in real implementation, use A* pathfinding)
        # Flip Y coordinates for SVG
        return f"M {start.x:.2f} {-start.y:.2f} L {end.x:.2f} {-end.y:.2f}"

    async def _add_safety_equipment(
        self,
        group: SVGGroup,
        elements: list[BuildingElement],
        bbox: BoundingBox,
        config: FireEscapePlanConfig,
    ) -> int:
        """Add safety equipment symbols."""
        equipment_count = 0

        # In a real implementation, safety equipment would be:
        # 1. Stored as IfcDistributionElement or similar
        # 2. Have classification (Uniclass, OmniClass) for type
        # 3. Retrieved from IFC model

        # For demonstration, place equipment at strategic positions
        positions = [
            (bbox.min_x + 2, bbox.center.y, "F001", "Feuerl\u00f6scher"),
            (bbox.max_x - 2, bbox.center.y, "F001", "Feuerl\u00f6scher"),
            (bbox.center.x, bbox.min_y + 2, "F004", "Brandmelder"),
            (bbox.center.x, bbox.max_y - 2, "E003", "Erste Hilfe"),
        ]

        if config.show_fire_extinguishers:
            for x, y, symbol_id, label in positions[:2]:
                symbol_svg = use_symbol(symbol_id, x - 20, -y - 20, 40, 40)
                group.children.append(_RawSVG(symbol_svg))
                equipment_count += 1

        if config.show_fire_alarms:
            x, y, symbol_id, label = positions[2]
            symbol_svg = use_symbol(symbol_id, x - 20, -y - 20, 40, 40)
            group.children.append(_RawSVG(symbol_svg))
            equipment_count += 1

        if config.show_first_aid:
            x, y, symbol_id, label = positions[3]
            symbol_svg = use_symbol(symbol_id, x - 20, -y - 20, 40, 40)
            group.children.append(_RawSVG(symbol_svg))
            equipment_count += 1

        return equipment_count

    def _add_you_are_here_marker(
        self,
        svg: SVGDocument,
        bbox: BoundingBox,
        config: FireEscapePlanConfig,
    ) -> None:
        """Add 'You are here' marker."""
        x = config.you_are_here_x if config.you_are_here_x else bbox.center.x
        y = config.you_are_here_y if config.you_are_here_y else bbox.center.y

        marker_group = SVGGroup(element_id="you_are_here")

        # Blue circle with pulsing effect
        marker_group.add(SVGCircle(
            cx=x,
            cy=-y,
            r=3,
            style=SVGStyle(fill=COLOR_INFO_BLUE, stroke="#FFFFFF", stroke_width=1),
        ))

        # Outer ring
        marker_group.add(SVGCircle(
            cx=x,
            cy=-y,
            r=5,
            style=SVGStyle(fill="none", stroke=COLOR_INFO_BLUE, stroke_width=0.5),
        ))

        # Label
        marker_group.add(SVGText(
            x=x,
            y=-y + 10,
            text="Sie sind hier",
            anchor="middle",
            style=SVGStyle(font_size=6, fill=COLOR_INFO_BLUE),
        ))

        svg.add(marker_group)

    def _add_title_block(self, svg: SVGDocument, config: FireEscapePlanConfig) -> None:
        """Add title block according to DIN ISO 23601."""
        # Title block in top area
        title_group = SVGGroup(
            element_id="title_block",
            transform="translate(20, 20)",
        )

        # Green header bar
        title_group.add(SVGRect(
            x=0, y=0, width=400, height=40,
            style=SVGStyle(fill=COLOR_ESCAPE_GREEN, stroke="none"),
        ))

        # Main title
        title_group.add(SVGText(
            x=200, y=25,
            text=config.title,
            anchor="middle",
            style=SVGStyle(font_size=18, fill="#FFFFFF", font_family="Arial Black, sans-serif"),
        ))

        # Subtitle / Building info
        if config.building_name or config.floor_name:
            subtitle = f"{config.building_name} - {config.floor_name}".strip(" - ")
            title_group.add(SVGText(
                x=200, y=55,
                text=subtitle,
                anchor="middle",
                style=SVGStyle(font_size=12, fill="#333333"),
            ))

        svg.add(title_group)

    def _add_escape_plan_legend(
        self,
        svg: SVGDocument,
        config: FireEscapePlanConfig,
    ) -> None:
        """Add legend for escape plan symbols."""
        legend_group = SVGGroup(
            element_id="legend",
            transform=f"translate({config.width - 200}, 20)",
        )

        # Background
        legend_group.add(SVGRect(
            x=0, y=0, width=180, height=200,
            style=SVGStyle(fill="#FFFFFF", stroke="#000000", stroke_width=0.5),
        ))

        # Title
        legend_group.add(SVGText(
            x=90, y=20,
            text="Legende",
            anchor="middle",
            style=SVGStyle(font_size=12, fill="#000000"),
        ))

        # Legend items
        items = [
            ("E001", "Notausgang"),
            ("F001", "Feuerl\u00f6scher"),
            ("F004", "Brandmelder"),
            ("E003", "Erste Hilfe"),
            ("E004", "Sammelstelle"),
        ]

        y_offset = 40
        for symbol_id, label in items:
            # Symbol
            symbol_svg = use_symbol(symbol_id, 10, y_offset - 15, 30, 30)
            legend_group.children.append(_RawSVG(symbol_svg))

            # Label
            legend_group.add(SVGText(
                x=50, y=y_offset + 5,
                text=label,
                anchor="start",
                style=SVGStyle(font_size=9, fill="#000000"),
            ))
            y_offset += 35

        svg.add(legend_group)

    def _add_behavior_instructions(
        self,
        svg: SVGDocument,
        config: FireEscapePlanConfig,
    ) -> None:
        """Add behavior instructions panel."""
        instructions_group = SVGGroup(
            element_id="instructions",
            transform=f"translate(20, {config.height - 120})",
        )

        # Background
        instructions_group.add(SVGRect(
            x=0, y=0, width=350, height=100,
            style=SVGStyle(fill="#FFF9E6", stroke="#FFB800", stroke_width=1),
        ))

        # Title
        instructions_group.add(SVGText(
            x=175, y=20,
            text="Verhalten im Brandfall",
            anchor="middle",
            style=SVGStyle(font_size=11, fill="#000000"),
        ))

        # Instructions
        instructions = [
            "1. Ruhe bewahren",
            "2. Brand melden (Notruf 112)",
            "3. In Sicherheit bringen",
            "4. L\u00f6schversuch unternehmen",
            "5. Auf Anweisungen achten",
        ]

        y_offset = 35
        for instruction in instructions:
            instructions_group.add(SVGText(
                x=15, y=y_offset,
                text=instruction,
                anchor="start",
                style=SVGStyle(font_size=8, fill="#333333"),
            ))
            y_offset += 12

        svg.add(instructions_group)


class _RawSVG:
    """Helper class for raw SVG content."""

    def __init__(self, content: str) -> None:
        self.content = content

    def render(self) -> str:
        return self.content
