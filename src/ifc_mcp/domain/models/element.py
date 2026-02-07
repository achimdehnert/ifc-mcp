"""Building Element Domain Entity.

Represents a building element (wall, door, window, etc.) from IFC.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from ifc_mcp.domain.value_objects import FireRating, GlobalId


class ElementCategory(str, Enum):
    """Building element category classification."""

    WALL = "wall"
    WALL_STANDARD_CASE = "wall_standard_case"
    DOOR = "door"
    WINDOW = "window"
    SLAB = "slab"
    ROOF_SLAB = "roof_slab"
    COLUMN = "column"
    BEAM = "beam"
    STAIR = "stair"
    RAMP = "ramp"
    CURTAIN_WALL = "curtain_wall"
    COVERING = "covering"
    SPACE = "space"
    OPENING = "opening"
    RAILING = "railing"
    FURNITURE = "furniture"
    EQUIPMENT = "equipment"
    DISTRIBUTION_ELEMENT = "distribution_element"
    OTHER = "other"

    @classmethod
    def from_ifc_class(cls, ifc_class: str) -> ElementCategory:
        """Map IFC class to category."""
        mapping = {
            "IfcWall": cls.WALL,
            "IfcWallStandardCase": cls.WALL_STANDARD_CASE,
            "IfcDoor": cls.DOOR,
            "IfcWindow": cls.WINDOW,
            "IfcSlab": cls.SLAB,
            "IfcRoof": cls.ROOF_SLAB,
            "IfcColumn": cls.COLUMN,
            "IfcBeam": cls.BEAM,
            "IfcStair": cls.STAIR,
            "IfcStairFlight": cls.STAIR,
            "IfcRamp": cls.RAMP,
            "IfcRampFlight": cls.RAMP,
            "IfcCurtainWall": cls.CURTAIN_WALL,
            "IfcCovering": cls.COVERING,
            "IfcSpace": cls.SPACE,
            "IfcOpeningElement": cls.OPENING,
            "IfcRailing": cls.RAILING,
            "IfcFurniture": cls.FURNITURE,
            "IfcFurnishingElement": cls.FURNITURE,
            "IfcDistributionElement": cls.DISTRIBUTION_ELEMENT,
            "IfcFlowSegment": cls.DISTRIBUTION_ELEMENT,
            "IfcFlowFitting": cls.DISTRIBUTION_ELEMENT,
            "IfcFlowTerminal": cls.DISTRIBUTION_ELEMENT,
        }
        return mapping.get(ifc_class, cls.OTHER)


@dataclass
class PropertyValue:
    """Property value with metadata."""
    name: str
    value: Any
    data_type: str = "string"
    unit: str | None = None


@dataclass
class QuantityValue:
    """Quantity value with unit."""
    name: str
    value: Decimal
    unit: str | None = None
    formula: str | None = None


@dataclass
class MaterialLayer:
    """Material layer in a layered structure."""
    material_name: str
    thickness: Decimal | None = None
    layer_order: int = 0
    is_ventilated: bool = False
    category: str | None = None


@dataclass
class BuildingElement:
    """Building Element Domain Entity."""

    id: UUID
    project_id: UUID
    global_id: GlobalId
    ifc_class: str
    category: ElementCategory

    name: str | None = None
    description: str | None = None
    object_type: str | None = None
    tag: str | None = None

    length_m: Decimal | None = None
    width_m: Decimal | None = None
    height_m: Decimal | None = None
    area_m2: Decimal | None = None
    volume_m3: Decimal | None = None

    position_x: Decimal | None = None
    position_y: Decimal | None = None
    position_z: Decimal | None = None

    storey_id: UUID | None = None
    storey_name: str | None = None
    type_id: UUID | None = None
    type_name: str | None = None

    is_external: bool | None = None
    is_load_bearing: bool | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    _properties: dict[str, dict[str, PropertyValue]] = field(
        default_factory=dict, repr=False
    )
    _quantities: dict[str, dict[str, QuantityValue]] = field(
        default_factory=dict, repr=False
    )
    _materials: list[MaterialLayer] = field(default_factory=list, repr=False)

    @classmethod
    def create(
        cls,
        project_id: UUID,
        global_id: str | GlobalId,
        ifc_class: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tag: str | None = None,
        storey_id: UUID | None = None,
        type_id: UUID | None = None,
    ) -> BuildingElement:
        """Factory method to create a BuildingElement."""
        if isinstance(global_id, str):
            global_id = GlobalId(global_id)

        return cls(
            id=uuid4(),
            project_id=project_id,
            global_id=global_id,
            ifc_class=ifc_class,
            category=ElementCategory.from_ifc_class(ifc_class),
            name=name,
            description=description,
            tag=tag,
            storey_id=storey_id,
            type_id=type_id,
        )

    @property
    def properties(self) -> dict[str, dict[str, PropertyValue]]:
        """Get all property sets."""
        return self._properties

    def get_property(
        self, pset_name: str, property_name: str
    ) -> PropertyValue | None:
        """Get a specific property value."""
        pset = self._properties.get(pset_name)
        if pset:
            return pset.get(property_name)
        return None

    def get_property_value(
        self, pset_name: str, property_name: str
    ) -> Any | None:
        """Get raw property value."""
        prop = self.get_property(pset_name, property_name)
        return prop.value if prop else None

    def set_property(
        self,
        pset_name: str,
        property_name: str,
        value: Any,
        data_type: str = "string",
        unit: str | None = None,
    ) -> None:
        """Set a property value."""
        if pset_name not in self._properties:
            self._properties[pset_name] = {}

        self._properties[pset_name][property_name] = PropertyValue(
            name=property_name,
            value=value,
            data_type=data_type,
            unit=unit,
        )

    @property
    def quantities(self) -> dict[str, dict[str, QuantityValue]]:
        """Get all quantity sets."""
        return self._quantities

    def get_quantity(
        self, qto_name: str, quantity_name: str
    ) -> QuantityValue | None:
        """Get a specific quantity."""
        qto = self._quantities.get(qto_name)
        if qto:
            return qto.get(quantity_name)
        return None

    def get_quantity_value(
        self, qto_name: str, quantity_name: str
    ) -> Decimal | None:
        """Get raw quantity value."""
        qty = self.get_quantity(qto_name, quantity_name)
        return qty.value if qty else None

    def set_quantity(
        self,
        qto_name: str,
        quantity_name: str,
        value: Decimal | float,
        unit: str | None = None,
        formula: str | None = None,
    ) -> None:
        """Set a quantity value."""
        if qto_name not in self._quantities:
            self._quantities[qto_name] = {}

        if isinstance(value, float):
            value = Decimal(str(value))

        self._quantities[qto_name][quantity_name] = QuantityValue(
            name=quantity_name,
            value=value,
            unit=unit,
            formula=formula,
        )

    @property
    def materials(self) -> list[MaterialLayer]:
        """Get material layers."""
        return self._materials

    def add_material(
        self,
        material_name: str,
        thickness: Decimal | float | None = None,
        layer_order: int = 0,
        is_ventilated: bool = False,
        category: str | None = None,
    ) -> None:
        """Add a material layer."""
        if isinstance(thickness, float):
            thickness = Decimal(str(thickness))

        self._materials.append(
            MaterialLayer(
                material_name=material_name,
                thickness=thickness,
                layer_order=layer_order,
                is_ventilated=is_ventilated,
                category=category,
            )
        )

    @property
    def primary_material(self) -> str | None:
        """Get primary (first) material name."""
        if self._materials:
            sorted_materials = sorted(self._materials, key=lambda m: m.layer_order)
            return sorted_materials[0].material_name
        return None

    @property
    def fire_rating(self) -> FireRating | None:
        """Get fire rating from properties."""
        pset_names = [
            "Pset_WallCommon",
            "Pset_DoorCommon",
            "Pset_WindowCommon",
            "Pset_SlabCommon",
            "Pset_CurtainWallCommon",
        ]

        for pset_name in pset_names:
            value = self.get_property_value(pset_name, "FireRating")
            if value:
                return FireRating.parse(str(value))

        return None

    @property
    def acoustic_rating(self) -> str | None:
        """Get acoustic rating from properties."""
        pset_names = [
            "Pset_WallCommon",
            "Pset_DoorCommon",
            "Pset_WindowCommon",
        ]

        for pset_name in pset_names:
            value = self.get_property_value(pset_name, "AcousticRating")
            if value:
                return str(value)

        return None

    @property
    def u_value(self) -> Decimal | None:
        """Get thermal transmittance (U-value) from properties."""
        pset_names = [
            "Pset_WallCommon",
            "Pset_DoorCommon",
            "Pset_WindowCommon",
            "Pset_SlabCommon",
        ]

        for pset_name in pset_names:
            value = self.get_property_value(pset_name, "ThermalTransmittance")
            if value:
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass

        return None

    @property
    def is_drywall(self) -> bool:
        """Check if element is likely a drywall/partition."""
        drywall_keywords = [
            "gips", "gypsum", "drywall", "rigips", "knauf",
            "fermacell", "plasterboard", "trockenbau",
        ]

        for material in self._materials:
            material_lower = material.material_name.lower()
            if any(kw in material_lower for kw in drywall_keywords):
                return True

        if self.type_name:
            type_lower = self.type_name.lower()
            if any(kw in type_lower for kw in drywall_keywords):
                return True

        if self.category in (ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE):
            if self.is_load_bearing is False:
                return True

        return False

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on ID."""
        if isinstance(other, BuildingElement):
            return self.id == other.id
        return False
