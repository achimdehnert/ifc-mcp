"""Material Takeoff Service.

Generates quantity takeoffs (Mengenermittlung) from IFC models
according to VOB and DIN 276 standards.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from ifc_mcp.domain import BuildingElement, ElementCategory, Space
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


class CostGroup(str, Enum):
    """DIN 276 cost groups."""

    KG_300 = "300"  # Bauwerk - Baukonstruktionen
    KG_310 = "310"  # Baugrube
    KG_320 = "320"  # Gründung
    KG_330 = "330"  # Außenwände
    KG_331 = "331"  # Tragende Außenwände
    KG_332 = "332"  # Nichttragende Außenwände
    KG_334 = "334"  # Außentüren und -fenster
    KG_340 = "340"  # Innenwände
    KG_341 = "341"  # Tragende Innenwände
    KG_342 = "342"  # Nichttragende Innenwände
    KG_343 = "343"  # Innentüren
    KG_344 = "344"  # Innenfenster
    KG_350 = "350"  # Decken
    KG_360 = "360"  # Dächer
    KG_370 = "370"  # Baukonstruktive Einbauten
    KG_390 = "390"  # Sonstige Maßnahmen
    KG_400 = "400"  # Bauwerk - Technische Anlagen


class MeasurementUnit(str, Enum):
    """Measurement units."""

    M = "m"           # Meter
    M2 = "m\u00b2"         # Square meter
    M3 = "m\u00b3"         # Cubic meter
    STK = "Stk"       # Piece
    KG = "kg"         # Kilogram
    T = "t"           # Ton
    LFM = "lfm"       # Running meter
    PAU = "psch"      # Lump sum


@dataclass
class QuantityItem:
    """Single quantity item."""

    position: str  # Position number (e.g., "01.01")
    description: str
    cost_group: CostGroup | None = None
    quantity: Decimal = Decimal("0")
    unit: MeasurementUnit = MeasurementUnit.M2
    element_count: int = 0
    element_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuantityCategory:
    """Category of quantities."""

    name: str
    cost_group: CostGroup | None = None
    items: list[QuantityItem] = field(default_factory=list)
    element_count: int = 0

    @property
    def total_quantity(self) -> Decimal:
        """Total quantity of all items."""
        return sum((item.quantity for item in self.items), Decimal("0"))


@dataclass
class MaterialTakeoffResult:
    """Result of material takeoff generation."""

    project_name: str
    categories: list[QuantityCategory] = field(default_factory=list)
    total_elements: int = 0
    total_positions: int = 0

    # Summary quantities
    total_wall_area_m2: Decimal = Decimal("0")
    total_floor_area_m2: Decimal = Decimal("0")
    total_window_area_m2: Decimal = Decimal("0")
    total_door_count: int = 0
    total_room_volume_m3: Decimal = Decimal("0")


class MaterialTakeoffService:
    """Service for generating material takeoffs."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service."""
        self._uow = uow

    async def generate_takeoff(
        self,
        project_id: UUID,
        storey_id: UUID | None = None,
        include_breakdown: bool = True,
    ) -> MaterialTakeoffResult:
        """Generate material takeoff for project.

        Args:
            project_id: Project UUID
            storey_id: Optional storey filter
            include_breakdown: Include detailed element breakdown

        Returns:
            MaterialTakeoffResult with quantities
        """
        # Get project
        project = await self._uow.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        result = MaterialTakeoffResult(project_name=project.name)

        # Get elements
        elements = await self._uow.elements.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=50000,
        )

        # Get spaces
        spaces = await self._uow.spaces.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=5000,
        )

        result.total_elements = len(elements) + len(spaces)

        # Generate takeoff by category
        wall_cat = await self._takeoff_walls(elements, include_breakdown)
        if wall_cat:
            result.categories.append(wall_cat)
            result.total_wall_area_m2 = wall_cat.total_quantity

        window_cat = await self._takeoff_windows(elements, include_breakdown)
        if window_cat:
            result.categories.append(window_cat)
            result.total_window_area_m2 = window_cat.total_quantity

        door_cat = await self._takeoff_doors(elements, include_breakdown)
        if door_cat:
            result.categories.append(door_cat)
            result.total_door_count = door_cat.element_count

        slab_cat = await self._takeoff_slabs(elements, include_breakdown)
        if slab_cat:
            result.categories.append(slab_cat)
            result.total_floor_area_m2 = slab_cat.total_quantity

        column_cat = await self._takeoff_columns(elements, include_breakdown)
        if column_cat:
            result.categories.append(column_cat)

        space_cat = await self._takeoff_spaces(spaces, include_breakdown)
        if space_cat:
            result.categories.append(space_cat)
            result.total_room_volume_m3 = sum(
                (item.details.get("volume_m3", Decimal("0"))
                 for item in space_cat.items),
                Decimal("0"),
            )

        # Calculate totals
        result.total_positions = sum(
            len(cat.items) for cat in result.categories
        )

        return result

    async def _takeoff_walls(
        self,
        elements: list[BuildingElement],
        include_breakdown: bool,
    ) -> QuantityCategory | None:
        """Generate wall takeoff."""
        walls = [e for e in elements if e.category in (
            ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE
        )]

        if not walls:
            return None

        cat = QuantityCategory(
            name="W\u00e4nde",
            cost_group=CostGroup.KG_330,
            element_count=len(walls),
        )

        # Group by type
        type_groups: dict[str, list[BuildingElement]] = {}
        for wall in walls:
            type_name = wall.type_name or wall.name or "Unbekannt"
            type_groups.setdefault(type_name, []).append(wall)

        for pos_idx, (type_name, group_walls) in enumerate(type_groups.items(), 1):
            total_area = sum(
                self._calculate_wall_area(w) for w in group_walls
            )

            # Determine cost group
            is_external = any(
                w.is_external for w in group_walls if w.is_external is not None
            )
            is_load_bearing = any(
                w.is_load_bearing for w in group_walls if w.is_load_bearing is not None
            )

            if is_external and is_load_bearing:
                cost_group = CostGroup.KG_331
            elif is_external:
                cost_group = CostGroup.KG_332
            elif is_load_bearing:
                cost_group = CostGroup.KG_341
            else:
                cost_group = CostGroup.KG_342

            item = QuantityItem(
                position=f"01.{pos_idx:02d}",
                description=type_name,
                cost_group=cost_group,
                quantity=total_area,
                unit=MeasurementUnit.M2,
                element_count=len(group_walls),
                element_ids=(
                    [str(w.id) for w in group_walls[:10]]
                    if include_breakdown else []
                ),
                details={
                    "avg_thickness_m": float(
                        sum(float(w.width_m or 0) for w in group_walls) / len(group_walls)
                    ),
                    "is_external": is_external,
                    "is_load_bearing": is_load_bearing,
                },
            )
            cat.items.append(item)

        return cat

    async def _takeoff_windows(
        self,
        elements: list[BuildingElement],
        include_breakdown: bool,
    ) -> QuantityCategory | None:
        """Generate window takeoff."""
        windows = [e for e in elements if e.category == ElementCategory.WINDOW]

        if not windows:
            return None

        cat = QuantityCategory(
            name="Fenster",
            cost_group=CostGroup.KG_334,
            element_count=len(windows),
        )

        # Group by type
        type_groups: dict[str, list[BuildingElement]] = {}
        for window in windows:
            type_name = window.type_name or window.name or "Unbekannt"
            type_groups.setdefault(type_name, []).append(window)

        for pos_idx, (type_name, group_windows) in enumerate(type_groups.items(), 1):
            total_area = sum(
                self._calculate_opening_area(w) for w in group_windows
            )

            item = QuantityItem(
                position=f"02.{pos_idx:02d}",
                description=type_name,
                cost_group=CostGroup.KG_334,
                quantity=total_area,
                unit=MeasurementUnit.M2,
                element_count=len(group_windows),
                element_ids=(
                    [str(w.id) for w in group_windows[:10]]
                    if include_breakdown else []
                ),
                details={
                    "piece_count": len(group_windows),
                },
            )
            cat.items.append(item)

        return cat

    async def _takeoff_doors(
        self,
        elements: list[BuildingElement],
        include_breakdown: bool,
    ) -> QuantityCategory | None:
        """Generate door takeoff."""
        doors = [e for e in elements if e.category == ElementCategory.DOOR]

        if not doors:
            return None

        cat = QuantityCategory(
            name="T\u00fcren",
            cost_group=CostGroup.KG_343,
            element_count=len(doors),
        )

        # Group by type
        type_groups: dict[str, list[BuildingElement]] = {}
        for door in doors:
            type_name = door.type_name or door.name or "Unbekannt"
            type_groups.setdefault(type_name, []).append(door)

        for pos_idx, (type_name, group_doors) in enumerate(type_groups.items(), 1):
            # Determine if interior or exterior
            is_exterior = any(
                d.is_external for d in group_doors if d.is_external is not None
            )
            cost_group = CostGroup.KG_334 if is_exterior else CostGroup.KG_343

            item = QuantityItem(
                position=f"03.{pos_idx:02d}",
                description=type_name,
                cost_group=cost_group,
                quantity=Decimal(str(len(group_doors))),
                unit=MeasurementUnit.STK,
                element_count=len(group_doors),
                element_ids=(
                    [str(d.id) for d in group_doors[:10]]
                    if include_breakdown else []
                ),
                details={
                    "has_fire_rating": any(
                        d.fire_rating is not None for d in group_doors
                    ),
                    "fire_ratings": list(set(
                        d.fire_rating for d in group_doors
                        if d.fire_rating is not None
                    )),
                },
            )
            cat.items.append(item)

        return cat

    async def _takeoff_slabs(
        self,
        elements: list[BuildingElement],
        include_breakdown: bool,
    ) -> QuantityCategory | None:
        """Generate slab/floor takeoff."""
        slabs = [e for e in elements if e.category == ElementCategory.SLAB]

        if not slabs:
            return None

        cat = QuantityCategory(
            name="Decken / B\u00f6den",
            cost_group=CostGroup.KG_350,
            element_count=len(slabs),
        )

        # Group by type
        type_groups: dict[str, list[BuildingElement]] = {}
        for slab in slabs:
            type_name = slab.type_name or slab.name or "Unbekannt"
            type_groups.setdefault(type_name, []).append(slab)

        for pos_idx, (type_name, group_slabs) in enumerate(type_groups.items(), 1):
            total_area = sum(
                self._calculate_slab_area(s) for s in group_slabs
            )

            item = QuantityItem(
                position=f"04.{pos_idx:02d}",
                description=type_name,
                cost_group=CostGroup.KG_350,
                quantity=total_area,
                unit=MeasurementUnit.M2,
                element_count=len(group_slabs),
                element_ids=(
                    [str(s.id) for s in group_slabs[:10]]
                    if include_breakdown else []
                ),
                details={
                    "avg_thickness_m": float(
                        sum(float(s.width_m or 0) for s in group_slabs)
                        / len(group_slabs)
                    ) if group_slabs else 0,
                },
            )
            cat.items.append(item)

        return cat

    async def _takeoff_columns(
        self,
        elements: list[BuildingElement],
        include_breakdown: bool,
    ) -> QuantityCategory | None:
        """Generate column takeoff."""
        columns = [e for e in elements if e.category == ElementCategory.COLUMN]

        if not columns:
            return None

        cat = QuantityCategory(
            name="St\u00fctzen",
            cost_group=CostGroup.KG_341,
            element_count=len(columns),
        )

        # Group by type
        type_groups: dict[str, list[BuildingElement]] = {}
        for col in columns:
            type_name = col.type_name or col.name or "Unbekannt"
            type_groups.setdefault(type_name, []).append(col)

        for pos_idx, (type_name, group_cols) in enumerate(type_groups.items(), 1):
            total_volume = sum(
                self._calculate_column_volume(c) for c in group_cols
            )

            item = QuantityItem(
                position=f"05.{pos_idx:02d}",
                description=type_name,
                cost_group=CostGroup.KG_341,
                quantity=total_volume,
                unit=MeasurementUnit.M3,
                element_count=len(group_cols),
                element_ids=(
                    [str(c.id) for c in group_cols[:10]]
                    if include_breakdown else []
                ),
            )
            cat.items.append(item)

        return cat

    async def _takeoff_spaces(
        self,
        spaces: list[Space],
        include_breakdown: bool,
    ) -> QuantityCategory | None:
        """Generate space/room takeoff."""
        if not spaces:
            return None

        cat = QuantityCategory(
            name="R\u00e4ume (NRF)",
            element_count=len(spaces),
        )

        for pos_idx, space in enumerate(spaces, 1):
            area = space.net_floor_area_m2 or Decimal("0")
            volume = space.net_volume_m3 or Decimal("0")

            item = QuantityItem(
                position=f"06.{pos_idx:02d}",
                description=f"{space.number or ''} {space.name or 'Raum'}".strip(),
                quantity=area,
                unit=MeasurementUnit.M2,
                element_count=1,
                element_ids=[str(space.id)] if include_breakdown else [],
                details={
                    "volume_m3": volume,
                    "height_m": float(space.net_height_m or 0),
                },
            )
            cat.items.append(item)

        return cat

    # =========================================================================
    # Calculation helpers
    # =========================================================================

    def _calculate_wall_area(self, wall: BuildingElement) -> Decimal:
        """Calculate wall area in m\u00b2."""
        length = wall.length_m or Decimal("0")
        height = wall.height_m or Decimal("2.80")  # Default storey height
        return length * height

    def _calculate_opening_area(self, element: BuildingElement) -> Decimal:
        """Calculate opening area (window/door) in m\u00b2."""
        width = element.width_m or Decimal("0")
        height = element.height_m or Decimal("0")
        return width * height

    def _calculate_slab_area(self, slab: BuildingElement) -> Decimal:
        """Calculate slab area in m\u00b2."""
        if slab.area_m2:
            return slab.area_m2
        length = slab.length_m or Decimal("0")
        width = slab.width_m or Decimal("0")
        return length * width

    def _calculate_column_volume(self, column: BuildingElement) -> Decimal:
        """Calculate column volume in m\u00b3."""
        if column.volume_m3:
            return column.volume_m3
        # Estimate from dimensions
        width = column.width_m or Decimal("0.3")
        height = column.height_m or Decimal("3.0")
        # Assume square cross-section
        return width * width * height
