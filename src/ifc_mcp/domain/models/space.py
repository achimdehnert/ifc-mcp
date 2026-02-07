"""Space Domain Entity.

Represents a room/space from IFC with specialized attributes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from ifc_mcp.domain.value_objects import ExZone, ExZoneType, GlobalId


@dataclass
class SpaceBoundary:
    """Space boundary - element that bounds a space."""
    element_id: UUID
    element_name: str | None = None
    element_class: str | None = None
    boundary_type: str | None = None
    physical_or_virtual: str | None = None
    internal_or_external: str | None = None


@dataclass
class Space:
    """Space/Room Domain Entity."""

    id: UUID
    project_id: UUID
    element_id: UUID
    global_id: GlobalId

    name: str | None = None
    long_name: str | None = None
    space_number: str | None = None

    storey_id: UUID | None = None
    storey_name: str | None = None

    net_floor_area: Decimal | None = None
    gross_floor_area: Decimal | None = None
    net_volume: Decimal | None = None
    gross_volume: Decimal | None = None
    net_height: Decimal | None = None

    occupancy_type: str | None = None

    ex_zone: ExZone = field(default_factory=ExZone.none)
    hazardous_area: bool = False

    fire_compartment: str | None = None

    finish_floor: str | None = None
    finish_wall: str | None = None
    finish_ceiling: str | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    _boundaries: list[SpaceBoundary] = field(default_factory=list, repr=False)
    _adjacent_spaces: list[UUID] = field(default_factory=list, repr=False)

    @classmethod
    def create(
        cls,
        project_id: UUID,
        element_id: UUID,
        global_id: str | GlobalId,
        *,
        name: str | None = None,
        long_name: str | None = None,
        space_number: str | None = None,
        storey_id: UUID | None = None,
    ) -> Space:
        """Factory method to create a Space."""
        if isinstance(global_id, str):
            global_id = GlobalId(global_id)

        return cls(
            id=uuid4(),
            project_id=project_id,
            element_id=element_id,
            global_id=global_id,
            name=name,
            long_name=long_name,
            space_number=space_number,
            storey_id=storey_id,
        )

    @property
    def display_name(self) -> str:
        """Get display name."""
        if self.space_number and self.name:
            return f"{self.space_number} - {self.name}"
        return self.space_number or self.name or str(self.global_id)

    @property
    def area(self) -> Decimal | None:
        """Get primary area (net preferred)."""
        return self.net_floor_area or self.gross_floor_area

    @property
    def volume(self) -> Decimal | None:
        """Get primary volume (net preferred)."""
        return self.net_volume or self.gross_volume

    @property
    def boundaries(self) -> list[SpaceBoundary]:
        """Get space boundaries."""
        return self._boundaries

    @boundaries.setter
    def boundaries(self, value: list[SpaceBoundary]) -> None:
        """Set space boundaries."""
        self._boundaries = value

    @property
    def adjacent_spaces(self) -> list[UUID]:
        """Get adjacent space IDs."""
        return self._adjacent_spaces

    @adjacent_spaces.setter
    def adjacent_spaces(self, value: list[UUID]) -> None:
        """Set adjacent space IDs."""
        self._adjacent_spaces = value

    def set_ex_zone(self, zone: ExZone | str | None) -> None:
        """Set explosion zone classification."""
        if zone is None:
            self.ex_zone = ExZone.none()
        elif isinstance(zone, str):
            parsed = ExZone.parse(zone)
            self.ex_zone = parsed if parsed else ExZone.none()
        else:
            self.ex_zone = zone

        self.hazardous_area = self.ex_zone.is_hazardous

    @property
    def is_hazardous(self) -> bool:
        """Check if space is in an explosion hazardous area."""
        return self.ex_zone.is_hazardous or self.hazardous_area

    @property
    def required_equipment_category(self) -> int | None:
        """Get required ATEX equipment category for this space."""
        return self.ex_zone.required_equipment_category

    def add_boundary(
        self,
        element_id: UUID,
        element_name: str | None = None,
        element_class: str | None = None,
        boundary_type: str | None = None,
        physical_or_virtual: str | None = None,
        internal_or_external: str | None = None,
    ) -> None:
        """Add a boundary element."""
        self._boundaries.append(
            SpaceBoundary(
                element_id=element_id,
                element_name=element_name,
                element_class=element_class,
                boundary_type=boundary_type,
                physical_or_virtual=physical_or_virtual,
                internal_or_external=internal_or_external,
            )
        )

    def get_boundary_walls(self) -> list[SpaceBoundary]:
        """Get wall boundaries."""
        return [
            b for b in self._boundaries
            if b.element_class and "Wall" in b.element_class
        ]

    def get_boundary_doors(self) -> list[SpaceBoundary]:
        """Get door boundaries."""
        return [
            b for b in self._boundaries
            if b.element_class and "Door" in b.element_class
        ]

    def get_boundary_windows(self) -> list[SpaceBoundary]:
        """Get window boundaries."""
        return [
            b for b in self._boundaries
            if b.element_class and "Window" in b.element_class
        ]

    @property
    def external_boundary_count(self) -> int:
        """Count external boundaries."""
        return sum(
            1 for b in self._boundaries
            if b.internal_or_external == "EXTERNAL"
        )

    @property
    def has_external_boundaries(self) -> bool:
        """Check if space has external boundaries."""
        return self.external_boundary_count > 0

    def calculate_ventilation_ratio(
        self, opening_area_m2: Decimal
    ) -> Decimal | None:
        """Calculate opening area to floor area ratio."""
        if self.net_floor_area and self.net_floor_area > 0:
            return opening_area_m2 / self.net_floor_area
        return None

    def estimate_air_changes_per_hour(
        self,
        ventilation_rate_m3_per_hour: Decimal,
    ) -> Decimal | None:
        """Estimate air changes per hour."""
        if self.net_volume and self.net_volume > 0:
            return ventilation_rate_m3_per_hour / self.net_volume
        return None

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on ID."""
        if isinstance(other, Space):
            return self.id == other.id
        return False
