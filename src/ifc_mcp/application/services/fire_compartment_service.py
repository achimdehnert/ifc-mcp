"""Fire Compartment Map Service.

Generates fire compartment maps (Brandabschnittspl\u00e4ne) showing fire-rated 
walls, doors, and compartment boundaries.
"""
from __future__ import annotations

import colorsys
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
    STYLE_FIRE_COMPARTMENT,
)
from ifc_mcp.domain import BuildingElement, ElementCategory, Space
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Fire Rating Color Coding
# =============================================================================

FIRE_RATING_COLORS: dict[str, str] = {
    # German fire ratings (DIN 4102)
    "F30": "#FFFF00",   # Yellow - 30 min
    "F60": "#FFA500",   # Orange - 60 min
    "F90": "#FF4500",   # Red-Orange - 90 min
    "F120": "#FF0000",  # Red - 120 min
    "F180": "#8B0000",  # Dark Red - 180 min
    # European fire ratings (EN 13501)
    "EI30": "#FFFF00",
    "EI60": "#FFA500",
    "EI90": "#FF4500",
    "EI120": "#FF0000",
    "REI30": "#FFFF00",
    "REI60": "#FFA500",
    "REI90": "#FF4500",
    "REI120": "#FF0000",
    # T-ratings for doors
    "T30": "#90EE90",   # Light Green - 30 min
    "T60": "#32CD32",   # Green - 60 min
    "T90": "#228B22",   # Forest Green - 90 min
    "T120": "#006400",  # Dark Green - 120 min
    # Default
    "UNKNOWN": "#CCCCCC",
}

COMPARTMENT_COLORS = [
    "#E3F2FD",  # Light Blue
    "#F3E5F5",  # Light Purple
    "#E8F5E9",  # Light Green
    "#FFF3E0",  # Light Orange
    "#FCE4EC",  # Light Pink
    "#E0F7FA",  # Light Cyan
    "#FFF8E1",  # Light Amber
    "#F1F8E9",  # Light Lime
]


@dataclass
class FireCompartment:
    """Fire compartment definition."""

    id: str
    name: str
    boundary_elements: list[str]  # Element IDs forming the boundary
    area_m2: float | None = None
    fire_load_mj_m2: float | None = None  # Brandlast
    required_rating: str | None = None  # e.g., "F90"


@dataclass
class FireCompartmentMapConfig:
    """Configuration for fire compartment map generation."""

    # Output size
    width: float = 1200
    height: float = 900

    # Scale
    scale: float = 50.0

    # Margins
    margin: float = 60.0

    # Display options
    show_fire_walls: bool = True
    show_fire_doors: bool = True
    show_compartment_fill: bool = True
    show_fire_ratings: bool = True
    show_compartment_labels: bool = True
    show_penetrations: bool = True  # Durchf\u00fchrungen

    # Highlighting
    highlight_critical: bool = True  # Highlight F90+ elements

    # Labels
    title: str = "Brandabschnittsplan"
    building_name: str = ""
    floor_name: str = ""


@dataclass
class FireCompartmentMapResult:
    """Result of fire compartment map generation."""

    svg_content: str
    file_path: Path | None = None
    storey_name: str | None = None
    compartment_count: int = 0
    fire_wall_count: int = 0
    fire_door_count: int = 0


class FireCompartmentMapService:
    """Service for generating fire compartment maps."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service."""
        self._uow = uow

    async def generate_compartment_map(
        self,
        project_id: UUID,
        storey_id: UUID,
        config: FireCompartmentMapConfig | None = None,
        output_path: Path | None = None,
    ) -> FireCompartmentMapResult:
        """Generate fire compartment map for a storey.

        Args:
            project_id: Project UUID
            storey_id: Storey UUID
            config: Optional configuration
            output_path: Optional output file path

        Returns:
            FireCompartmentMapResult with SVG content
        """
        if config is None:
            config = FireCompartmentMapConfig()

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

        # Identify fire-rated elements
        fire_walls = [e for e in elements if self._is_fire_wall(e)]
        fire_doors = [e for e in elements if self._is_fire_door(e)]

        # Calculate bounding box
        bbox = self._calculate_bounding_box(elements)
        if not bbox:
            bbox = BoundingBox(0, 0, 30, 20)

        # Identify fire compartments
        compartments = self._identify_compartments(fire_walls, fire_doors, spaces, bbox)

        # Create SVG document
        svg = self._create_document(bbox, config)

        # 1. Add compartment fills (background)
        if config.show_compartment_fill:
            fills_group = SVGGroup(element_id="compartment_fills")
            self._add_compartment_fills(fills_group, compartments, bbox, config)
            svg.add(fills_group)

        # 2. Add base floor plan (walls in gray)
        base_group = SVGGroup(element_id="base_plan")
        self._add_base_floor_plan(base_group, elements, config)
        svg.add(base_group)

        # 3. Add fire-rated walls
        if config.show_fire_walls:
            walls_group = SVGGroup(element_id="fire_walls")
            self._add_fire_walls(walls_group, fire_walls, config)
            svg.add(walls_group)

        # 4. Add fire doors
        if config.show_fire_doors:
            doors_group = SVGGroup(element_id="fire_doors")
            self._add_fire_doors(doors_group, fire_doors, config)
            svg.add(doors_group)

        # 5. Add compartment labels
        if config.show_compartment_labels:
            labels_group = SVGGroup(element_id="compartment_labels")
            self._add_compartment_labels(labels_group, compartments, bbox, config)
            svg.add(labels_group)

        # 6. Add title block
        self._add_title_block(svg, config)

        # 7. Add legend
        self._add_legend(svg, config)

        # Render SVG
        svg_content = svg.render()

        # Save to file
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(svg_content, encoding="utf-8")

        return FireCompartmentMapResult(
            svg_content=svg_content,
            file_path=output_path,
            storey_name=storey_name,
            compartment_count=len(compartments),
            fire_wall_count=len(fire_walls),
            fire_door_count=len(fire_doors),
        )

    def _is_fire_wall(self, element: BuildingElement) -> bool:
        """Check if element is a fire-rated wall."""
        if element.category not in (ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE):
            return False
        return element.fire_rating is not None

    def _is_fire_door(self, element: BuildingElement) -> bool:
        """Check if element is a fire door."""
        if element.category != ElementCategory.DOOR:
            return False
        return element.fire_rating is not None

    def _calculate_bounding_box(self, elements: list[BuildingElement]) -> BoundingBox | None:
        """Calculate bounding box from elements."""
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

    def _identify_compartments(
        self,
        fire_walls: list[BuildingElement],
        fire_doors: list[BuildingElement],
        spaces: list[Space],
        bbox: BoundingBox,
    ) -> list[FireCompartment]:
        """Identify fire compartments from fire-rated elements.

        In a real implementation, this would:
        1. Use graph algorithms to find enclosed areas
        2. Parse IfcZone elements for defined compartments
        3. Calculate actual boundaries from wall geometry

        For demonstration, we create compartments based on spaces.
        """
        compartments = []

        # Group spaces into compartments
        # Simple heuristic: spaces separated by fire walls are different compartments
        compartment_id = 0
        used_space_ids: set[UUID] = set()

        for space in spaces:
            if space.id in used_space_ids:
                continue

            compartment_id += 1
            compartment = FireCompartment(
                id=f"BA-{compartment_id:02d}",
                name=f"Brandabschnitt {compartment_id}",
                boundary_elements=[str(space.id)],
                area_m2=float(space.net_floor_area) if space.net_floor_area else None,
            )
            compartments.append(compartment)
            used_space_ids.add(space.id)

        # If no spaces, create a single compartment
        if not compartments:
            compartments.append(FireCompartment(
                id="BA-01",
                name="Brandabschnitt 1",
                boundary_elements=[],
                area_m2=bbox.width * bbox.height,
            ))

        return compartments

    def _create_document(
        self,
        bbox: BoundingBox,
        config: FireCompartmentMapConfig,
    ) -> SVGDocument:
        """Create SVG document."""
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
            background_color="#FFFFFF",
        )

    def _add_compartment_fills(
        self,
        group: SVGGroup,
        compartments: list[FireCompartment],
        bbox: BoundingBox,
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add colored fills for compartments."""
        # Simple grid-based visualization
        num_compartments = len(compartments)
        if num_compartments == 0:
            return

        # Divide bbox into compartments
        cols = max(1, int(num_compartments ** 0.5))
        rows = (num_compartments + cols - 1) // cols

        cell_width = bbox.width / cols
        cell_height = bbox.height / rows

        for i, compartment in enumerate(compartments):
            col = i % cols
            row = i // cols

            x = bbox.min_x + col * cell_width
            y = bbox.min_y + row * cell_height

            color = COMPARTMENT_COLORS[i % len(COMPARTMENT_COLORS)]

            rect = SVGRect(
                x=x,
                y=-y - cell_height,
                width=cell_width,
                height=cell_height,
                style=SVGStyle(fill=color, stroke="none", opacity=0.5),
                element_id=f"fill_{compartment.id}",
                title=compartment.name,
            )
            group.add(rect)

    def _add_base_floor_plan(
        self,
        group: SVGGroup,
        elements: list[BuildingElement],
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add base floor plan (non-fire-rated walls in gray)."""
        walls = [e for e in elements if e.category in (
            ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE
        ) and not self._is_fire_wall(e)]

        for wall in walls:
            if wall.position_x is None or wall.position_y is None:
                continue

            x = float(wall.position_x)
            y = float(wall.position_y)
            length = float(wall.length_m) if wall.length_m else 1.0
            width = float(wall.width_m) if wall.width_m else 0.2

            rect = SVGRect(
                x=x,
                y=-y - width,
                width=length,
                height=width,
                style=SVGStyle(fill="#CCCCCC", stroke="#999999", stroke_width=0.3),
            )
            group.add(rect)

    def _add_fire_walls(
        self,
        group: SVGGroup,
        fire_walls: list[BuildingElement],
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add fire-rated walls with color coding."""
        for wall in fire_walls:
            if wall.position_x is None or wall.position_y is None:
                continue

            x = float(wall.position_x)
            y = float(wall.position_y)
            length = float(wall.length_m) if wall.length_m else 1.0
            width = float(wall.width_m) if wall.width_m else 0.25

            # Get color based on fire rating
            rating = wall.fire_rating or "UNKNOWN"
            color = self._get_fire_rating_color(rating)

            # Determine if critical (F90+)
            is_critical = self._is_critical_rating(rating)
            stroke_width = 1.5 if is_critical and config.highlight_critical else 0.5

            rect = SVGRect(
                x=x,
                y=-y - width,
                width=length,
                height=width,
                style=SVGStyle(fill=color, stroke="#000000", stroke_width=stroke_width),
                element_id=f"fire_wall_{wall.id}",
                title=f"{wall.name or 'Brandwand'} - {rating}",
            )
            group.add(rect)

            # Add rating label if enabled
            if config.show_fire_ratings and length > 1:
                label = SVGText(
                    x=x + length / 2,
                    y=-y - width / 2 + 0.1,
                    text=rating,
                    anchor="middle",
                    style=SVGStyle(font_size=0.3, fill="#000000"),
                )
                group.add(label)

    def _add_fire_doors(
        self,
        group: SVGGroup,
        fire_doors: list[BuildingElement],
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add fire doors with color coding."""
        for door in fire_doors:
            if door.position_x is None or door.position_y is None:
                continue

            x = float(door.position_x)
            y = float(door.position_y)
            width = float(door.width_m) if door.width_m else 0.9
            depth = 0.15

            # Get color based on fire rating (T-ratings for doors)
            rating = door.fire_rating or "UNKNOWN"
            color = self._get_fire_rating_color(rating)

            rect = SVGRect(
                x=x,
                y=-y - depth,
                width=width,
                height=depth,
                style=SVGStyle(fill=color, stroke="#000000", stroke_width=0.8),
                element_id=f"fire_door_{door.id}",
                title=f"{door.name or 'Brandschutzt\u00fcr'} - {rating}",
            )
            group.add(rect)

            # Door symbol (T with rating)
            symbol_text = SVGText(
                x=x + width / 2,
                y=-y + 0.5,
                text=f"T{rating[-2:] if rating != 'UNKNOWN' else '?'}",
                anchor="middle",
                style=SVGStyle(font_size=0.4, fill="#000000"),
            )
            group.add(symbol_text)

    def _add_compartment_labels(
        self,
        group: SVGGroup,
        compartments: list[FireCompartment],
        bbox: BoundingBox,
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add labels for fire compartments."""
        num_compartments = len(compartments)
        if num_compartments == 0:
            return

        cols = max(1, int(num_compartments ** 0.5))
        rows = (num_compartments + cols - 1) // cols

        cell_width = bbox.width / cols
        cell_height = bbox.height / rows

        for i, compartment in enumerate(compartments):
            col = i % cols
            row = i // cols

            center_x = bbox.min_x + (col + 0.5) * cell_width
            center_y = bbox.min_y + (row + 0.5) * cell_height

            # Compartment ID
            id_text = SVGText(
                x=center_x,
                y=-center_y,
                text=compartment.id,
                anchor="middle",
                style=SVGStyle(font_size=1.0, fill="#333333"),
            )
            group.add(id_text)

            # Area info
            if compartment.area_m2:
                area_text = SVGText(
                    x=center_x,
                    y=-center_y + 1.2,
                    text=f"{compartment.area_m2:.0f} m\u00b2",
                    anchor="middle",
                    style=SVGStyle(font_size=0.6, fill="#666666"),
                )
                group.add(area_text)

    def _add_title_block(
        self,
        svg: SVGDocument,
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add title block."""
        title_group = SVGGroup(
            element_id="title_block",
            transform="translate(20, 20)",
        )

        # Red header bar
        title_group.add(SVGRect(
            x=0, y=0, width=350, height=35,
            style=SVGStyle(fill="#CC0000", stroke="none"),
        ))

        # Title
        title_group.add(SVGText(
            x=175, y=23,
            text=config.title,
            anchor="middle",
            style=SVGStyle(font_size=16, fill="#FFFFFF"),
        ))

        # Building/Floor info
        if config.building_name or config.floor_name:
            subtitle = f"{config.building_name} - {config.floor_name}".strip(" - ")
            title_group.add(SVGText(
                x=175, y=50,
                text=subtitle,
                anchor="middle",
                style=SVGStyle(font_size=11, fill="#333333"),
            ))

        svg.add(title_group)

    def _add_legend(
        self,
        svg: SVGDocument,
        config: FireCompartmentMapConfig,
    ) -> None:
        """Add fire rating legend."""
        legend_group = SVGGroup(
            element_id="legend",
            transform=f"translate({config.width - 180}, 20)",
        )

        # Background
        legend_group.add(SVGRect(
            x=0, y=0, width=160, height=220,
            style=SVGStyle(fill="#FFFFFF", stroke="#000000", stroke_width=0.5),
        ))

        # Title
        legend_group.add(SVGText(
            x=80, y=18,
            text="Brandschutzklassen",
            anchor="middle",
            style=SVGStyle(font_size=10, fill="#000000"),
        ))

        # Wall ratings
        legend_group.add(SVGText(
            x=10, y=38,
            text="W\u00e4nde:",
            anchor="start",
            style=SVGStyle(font_size=8, fill="#333333"),
        ))

        wall_ratings = ["F30", "F60", "F90", "F120"]
        y_offset = 50
        for rating in wall_ratings:
            color = FIRE_RATING_COLORS.get(rating, "#CCCCCC")
            legend_group.add(SVGRect(
                x=10, y=y_offset - 8, width=30, height=12,
                style=SVGStyle(fill=color, stroke="#000000", stroke_width=0.5),
            ))
            legend_group.add(SVGText(
                x=50, y=y_offset,
                text=f"{rating} ({int(rating[1:])} min)",
                anchor="start",
                style=SVGStyle(font_size=8, fill="#000000"),
            ))
            y_offset += 18

        # Door ratings
        legend_group.add(SVGText(
            x=10, y=y_offset + 10,
            text="T\u00fcren:",
            anchor="start",
            style=SVGStyle(font_size=8, fill="#333333"),
        ))

        y_offset += 22
        door_ratings = ["T30", "T60", "T90"]
        for rating in door_ratings:
            color = FIRE_RATING_COLORS.get(rating, "#CCCCCC")
            legend_group.add(SVGRect(
                x=10, y=y_offset - 8, width=30, height=12,
                style=SVGStyle(fill=color, stroke="#000000", stroke_width=0.5),
            ))
            legend_group.add(SVGText(
                x=50, y=y_offset,
                text=f"{rating} ({int(rating[1:])} min)",
                anchor="start",
                style=SVGStyle(font_size=8, fill="#000000"),
            ))
            y_offset += 18

        svg.add(legend_group)

    def _get_fire_rating_color(self, rating: str) -> str:
        """Get color for fire rating."""
        # Normalize rating
        rating_upper = rating.upper().strip()

        # Direct match
        if rating_upper in FIRE_RATING_COLORS:
            return FIRE_RATING_COLORS[rating_upper]

        # Try to extract base rating
        for key in FIRE_RATING_COLORS:
            if key in rating_upper:
                return FIRE_RATING_COLORS[key]

        return FIRE_RATING_COLORS["UNKNOWN"]

    def _is_critical_rating(self, rating: str) -> bool:
        """Check if rating is critical (90+ minutes)."""
        try:
            # Extract minutes from rating
            import re
            match = re.search(r"(\d+)", rating)
            if match:
                minutes = int(match.group(1))
                return minutes >= 90
        except (ValueError, AttributeError):
            pass
        return False
