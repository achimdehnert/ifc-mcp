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
    boundary_type: str | None = None  # "1stLevel", "2ndLevel"
    physical_or_virtual: str | None = None  # "PHYSICAL", "VIRTUAL"
    internal_or_external: str | None = None  # "INTERNAL", "EXTERNAL"


@dataclass
class Space:
    """Space/Room Domain Entity.

    Represents a room or space from an IFC model with specialized
    attributes for construction and explosion protection use cases.

    Attributes:
        id: Unique identifier
        project_id: Parent project ID
        element_id: Link to base building_element
        global_id: IFC GlobalId
        name: Space name
        long_name: Long/descriptive name
        space_number: Room number
    """

    id: UUID
    project_id: UUID
    element_id: UUID  # Link to building_elements table
    global_id: GlobalId

    name: str | None = None
    long_name: str | None = None
    space_number: str | None = None

    # Spatial reference
    storey_id: UUID | None = None
    storey_name: str | None = None

    # Geometry / Quantities
    net_floor_area: Decimal | None = None
    gross_floor_area: Decimal | None = None
    net_volume: Decimal | None = None
    gross_volume: Decimal | None = None
    net_height: Decimal | None = None

    # Usage
    occupancy_type: str | None = None

    # Explosion Protection
    ex_zone: ExZone = field(default_factory=ExZone.none)
    hazardous_area: bool = False

    # Fire Safety
    fire_compartment: str | None = None

    # Finishes
    finish_floor: str | None = None
    finish_wall: str | None = None
    finish_ceiling: str | None = None

    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Relationships (lazy loaded)
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
        """Factory method to create a Space.

        Args:
            project_id: Parent project UUID
            element_id: Linked building element UUID
            global_id: IFC GlobalId
            name: Space name
            long_name: Long name
            space_number: Room number
            storey_id: Storey UUID

        Returns:
            New Space instance
        """
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

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def display_name(self) -> str:
        """Get display name (number + name or just name)."""
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

    # =========================================================================
    # Ex-Zone Methods
    # =========================================================================

    def set_ex_zone(self, zone: ExZone | str | None) -> None:
        """Set explosion zone classification.

        Args:
            zone: ExZone, zone string, or None
        """
        if zone is None:
            self.ex_zone = ExZone.none()
        elif isinstance(zone, str):
            parsed = ExZone.parse(zone)
            self.ex_zone = parsed if parsed else ExZone.none()
        else:
            self.ex_zone = zone

        # Update hazardous flag
        self.hazardous_area = self.ex_zone.is_hazardous

    @property
    def is_hazardous(self) -> bool:
        """Check if space is in an explosion hazardous area."""
        return self.ex_zone.is_hazardous or self.hazardous_area

    @property
    def required_equipment_category(self) -> int | None:
        """Get required ATEX equipment category for this space."""
        return self.ex_zone.required_equipment_category

    # =========================================================================
    # Boundary Analysis
    # =========================================================================

    def add_boundary(
        self,
        element_id: UUID,
        element_name: str | None = None,
        element_class: str | None = None,
        boundary_type: str | None = None,
        physical_or_virtual: str | None = None,
        internal_or_external: str | None = None,
    ) -> None:
        """Add a boundary element.

        Args:
            element_id: Boundary element UUID
            element_name: Element name
            element_class: IFC class
            boundary_type: Boundary type
            physical_or_virtual: Physical or virtual boundary
            internal_or_external: Internal or external boundary
        """
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
        """Get wall boundaries.

        Returns:
            List of wall boundaries
        """
        return [
            b for b in self._boundaries
            if b.element_class and "Wall" in b.element_class
        ]

    def get_boundary_doors(self) -> list[SpaceBoundary]:
        """Get door boundaries.

        Returns:
            List of door boundaries
        """
        return [
            b for b in self._boundaries
            if b.element_class and "Door" in b.element_class
        ]

    def get_boundary_windows(self) -> list[SpaceBoundary]:
        """Get window boundaries.

        Returns:
            List of window boundaries
        """
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

    # =========================================================================
    # Volume Analysis (for Ex-Protection)
    # =========================================================================

    def calculate_ventilation_ratio(
        self, opening_area_m2: Decimal
    ) -> Decimal | None:
        """Calculate opening area to floor area ratio.

        Important for explosion protection ventilation requirements.

        Args:
            opening_area_m2: Total opening area in m\u00b2

        Returns:
            Ratio (opening_area / floor_area) or None
        """
        if self.net_floor_area and self.net_floor_area > 0:
            return opening_area_m2 / self.net_floor_area
        return None

    def estimate_air_changes_per_hour(
        self,
        ventilation_rate_m3_per_hour: Decimal,
    ) -> Decimal | None:
        """Estimate air changes per hour.

        Args:
            ventilation_rate_m3_per_hour: Ventilation rate

        Returns:
            Air changes per hour or None
        """
        if self.net_volume and self.net_volume > 0:
            return ventilation_rate_m3_per_hour / self.net_volume
        return None

    # =========================================================================
    # Equality
    # =========================================================================

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on ID."""
        if isinstance(other, Space):
            return self.id == other.id
        return False
