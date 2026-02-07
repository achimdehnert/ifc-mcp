"""IFC Parser using IfcOpenShell.

Parses IFC files and extracts structural information.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit

from ifc_mcp.domain import (
    IfcFileNotFoundError,
    IfcParseError,
    IfcSchemaVersion,
    UnsupportedIfcSchemaError,
)
from ifc_mcp.shared.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ParsedProperty:
    """Parsed IFC property."""

    pset_name: str
    name: str
    value: Any
    data_type: str = "string"
    unit: str | None = None


@dataclass
class ParsedQuantity:
    """Parsed IFC quantity."""

    qto_name: str
    name: str
    value: Decimal | None
    unit: str | None = None
    formula: str | None = None


@dataclass
class ParsedMaterial:
    """Parsed IFC material layer."""

    name: str
    thickness: Decimal | None = None
    layer_order: int = 0
    is_ventilated: bool = False
    category: str | None = None


@dataclass
class ParsedElement:
    """Parsed IFC building element."""

    global_id: str
    ifc_class: str
    name: str | None = None
    description: str | None = None
    object_type: str | None = None
    tag: str | None = None

    # Spatial reference
    storey_global_id: str | None = None
    type_global_id: str | None = None

    # Geometry
    length_m: Decimal | None = None
    width_m: Decimal | None = None
    height_m: Decimal | None = None
    area_m2: Decimal | None = None
    volume_m3: Decimal | None = None

    # Position
    position_x: Decimal | None = None
    position_y: Decimal | None = None
    position_z: Decimal | None = None

    # Flags
    is_external: bool | None = None
    is_load_bearing: bool | None = None

    # Collections
    properties: list[ParsedProperty] = field(default_factory=list)
    quantities: list[ParsedQuantity] = field(default_factory=list)
    materials: list[ParsedMaterial] = field(default_factory=list)


@dataclass
class ParsedStorey:
    """Parsed IFC building storey."""

    global_id: str
    name: str | None = None
    long_name: str | None = None
    elevation: float | None = None


@dataclass
class ParsedType:
    """Parsed IFC element type."""

    global_id: str
    ifc_class: str
    name: str | None = None
    description: str | None = None
    properties: list[ParsedProperty] = field(default_factory=list)


@dataclass
class ParsedSpace:
    """Parsed IFC space (room)."""

    global_id: str
    name: str | None = None
    long_name: str | None = None
    space_number: str | None = None
    storey_global_id: str | None = None

    # Geometry
    net_floor_area: Decimal | None = None
    gross_floor_area: Decimal | None = None
    net_volume: Decimal | None = None
    gross_volume: Decimal | None = None
    net_height: Decimal | None = None

    # Usage
    occupancy_type: str | None = None

    # Ex-Zone (from properties)
    ex_zone: str | None = None

    # Fire
    fire_compartment: str | None = None

    # Finishes
    finish_floor: str | None = None
    finish_wall: str | None = None
    finish_ceiling: str | None = None

    # Boundaries
    boundary_element_ids: list[str] = field(default_factory=list)

    # Properties
    properties: list[ParsedProperty] = field(default_factory=list)


@dataclass
class ParsedProject:
    """Parsed IFC project with all data."""

    name: str
    description: str | None = None
    schema_version: IfcSchemaVersion = IfcSchemaVersion.IFC4
    file_path: str | None = None
    file_hash: str | None = None
    authoring_app: str | None = None
    author: str | None = None
    organization: str | None = None

    storeys: list[ParsedStorey] = field(default_factory=list)
    types: list[ParsedType] = field(default_factory=list)
    elements: list[ParsedElement] = field(default_factory=list)
    spaces: list[ParsedSpace] = field(default_factory=list)
    materials: set[str] = field(default_factory=set)


class IfcParser:
    """IFC file parser using IfcOpenShell."""

    # Supported IFC schemas
    SUPPORTED_SCHEMAS = {"IFC2X3", "IFC4", "IFC4X1", "IFC4X2", "IFC4X3"}

    # IFC classes to extract
    ELEMENT_CLASSES = {
        "IfcWall",
        "IfcWallStandardCase",
        "IfcDoor",
        "IfcWindow",
        "IfcSlab",
        "IfcRoof",
        "IfcColumn",
        "IfcBeam",
        "IfcStair",
        "IfcStairFlight",
        "IfcRamp",
        "IfcRampFlight",
        "IfcCurtainWall",
        "IfcCovering",
        "IfcRailing",
        "IfcFurniture",
        "IfcFurnishingElement",
        "IfcOpeningElement",
        # Distribution elements
        "IfcDistributionElement",
        "IfcFlowSegment",
        "IfcFlowFitting",
        "IfcFlowTerminal",
    }

    def __init__(self, file_path: str | Path) -> None:
        """Initialize parser with IFC file path.

        Args:
            file_path: Path to IFC file

        Raises:
            IfcFileNotFoundError: If file doesn't exist
        """
        self.file_path = Path(file_path)

        if not self.file_path.exists():
            raise IfcFileNotFoundError(str(self.file_path))

        self._ifc: ifcopenshell.file | None = None
        self._unit_scale: float = 1.0

    @property
    def ifc(self) -> ifcopenshell.file:
        """Get loaded IFC file."""
        if self._ifc is None:
            self._load_file()
        return self._ifc  # type: ignore

    def _load_file(self) -> None:
        """Load and validate IFC file."""
        try:
            self._ifc = ifcopenshell.open(str(self.file_path))
        except Exception as e:
            raise IfcParseError(str(self.file_path), str(e)) from e

        # Validate schema
        schema = self._ifc.schema
        if schema not in self.SUPPORTED_SCHEMAS:
            raise UnsupportedIfcSchemaError(schema, list(self.SUPPORTED_SCHEMAS))

        # Get unit scale factor (convert to meters)
        self._unit_scale = ifcopenshell.util.unit.calculate_unit_scale(self._ifc)

        logger.info(
            "IFC file loaded",
            schema=schema,
            path=str(self.file_path),
            unit_scale=self._unit_scale,
        )

    def calculate_file_hash(self) -> str:
        """Calculate SHA-256 hash of file.

        Returns:
            Hex-encoded hash string
        """
        sha256 = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def parse(self) -> ParsedProject:
        """Parse entire IFC file.

        Returns:
            ParsedProject with all extracted data
        """
        logger.info("Starting IFC parse", path=str(self.file_path))

        # Get project info
        project = self._parse_project_info()

        # Parse storeys
        project.storeys = list(self._parse_storeys())
        logger.info("Parsed storeys", count=len(project.storeys))

        # Parse element types
        project.types = list(self._parse_types())
        logger.info("Parsed types", count=len(project.types))

        # Parse elements
        project.elements = list(self._parse_elements())
        logger.info("Parsed elements", count=len(project.elements))

        # Parse spaces
        project.spaces = list(self._parse_spaces())
        logger.info("Parsed spaces", count=len(project.spaces))

        # Collect unique materials
        for element in project.elements:
            for material in element.materials:
                project.materials.add(material.name)

        logger.info(
            "IFC parse complete",
            elements=len(project.elements),
            spaces=len(project.spaces),
            storeys=len(project.storeys),
            types=len(project.types),
            materials=len(project.materials),
        )

        return project

    def _parse_project_info(self) -> ParsedProject:
        """Parse project-level information."""
        ifc_project = self.ifc.by_type("IfcProject")[0]

        # Get application info
        app_info = self._get_application_info()

        return ParsedProject(
            name=ifc_project.Name or "Unnamed Project",
            description=getattr(ifc_project, "Description", None),
            schema_version=IfcSchemaVersion.from_string(self.ifc.schema),
            file_path=str(self.file_path),
            file_hash=self.calculate_file_hash(),
            authoring_app=app_info.get("application"),
            author=app_info.get("author"),
            organization=app_info.get("organization"),
        )

    def _get_application_info(self) -> dict[str, str | None]:
        """Extract authoring application info."""
        result: dict[str, str | None] = {
            "application": None,
            "author": None,
            "organization": None,
        }

        try:
            # Try to get OwnerHistory
            histories = self.ifc.by_type("IfcOwnerHistory")
            if histories:
                history = histories[0]
                if history.OwningApplication:
                    app = history.OwningApplication
                    result["application"] = (
                        f"{app.ApplicationFullName} {app.Version}"
                        if app.Version
                        else app.ApplicationFullName
                    )
                if history.OwningUser:
                    user = history.OwningUser
                    if user.ThePerson:
                        names = [
                            user.ThePerson.GivenName,
                            user.ThePerson.FamilyName,
                        ]
                        result["author"] = " ".join(n for n in names if n)
                    if user.TheOrganization:
                        result["organization"] = user.TheOrganization.Name
        except Exception as e:
            logger.warning("Failed to extract application info", error=str(e))

        return result

    def _parse_storeys(self) -> Iterator[ParsedStorey]:
        """Parse building storeys."""
        for storey in self.ifc.by_type("IfcBuildingStorey"):
            elevation = None
            if storey.Elevation is not None:
                elevation = float(storey.Elevation) * self._unit_scale

            yield ParsedStorey(
                global_id=storey.GlobalId,
                name=storey.Name,
                long_name=getattr(storey, "LongName", None),
                elevation=elevation,
            )

    def _parse_types(self) -> Iterator[ParsedType]:
        """Parse element types."""
        type_classes = [
            "IfcWallType",
            "IfcDoorType",
            "IfcWindowType",
            "IfcSlabType",
            "IfcColumnType",
            "IfcBeamType",
            "IfcCoveringType",
            "IfcCurtainWallType",
            "IfcStairType",
            "IfcRampType",
            "IfcRailingType",
            "IfcFurnitureType",
        ]

        for type_class in type_classes:
            try:
                for element_type in self.ifc.by_type(type_class):
                    parsed = ParsedType(
                        global_id=element_type.GlobalId,
                        ifc_class=element_type.is_a(),
                        name=element_type.Name,
                        description=getattr(element_type, "Description", None),
                    )

                    # Extract type properties
                    parsed.properties = list(
                        self._extract_properties(element_type)
                    )

                    yield parsed
            except Exception:
                # Type class may not exist in schema
                pass

    def _parse_elements(self) -> Iterator[ParsedElement]:
        """Parse building elements."""
        for element_class in self.ELEMENT_CLASSES:
            try:
                for element in self.ifc.by_type(element_class):
                    yield self._parse_single_element(element)
            except Exception as e:
                logger.warning(
                    "Failed to parse element class",
                    element_class=element_class,
                    error=str(e),
                )

    def _parse_single_element(self, element: Any) -> ParsedElement:
        """Parse a single IFC element."""
        parsed = ParsedElement(
            global_id=element.GlobalId,
            ifc_class=element.is_a(),
            name=element.Name,
            description=getattr(element, "Description", None),
            object_type=getattr(element, "ObjectType", None),
            tag=getattr(element, "Tag", None),
        )

        # Get spatial container (storey)
        container = ifcopenshell.util.element.get_container(element)
        if container and container.is_a("IfcBuildingStorey"):
            parsed.storey_global_id = container.GlobalId

        # Get element type
        element_type = ifcopenshell.util.element.get_type(element)
        if element_type:
            parsed.type_global_id = element_type.GlobalId

        # Get placement/position
        try:
            placement = ifcopenshell.util.placement.get_local_placement(
                element.ObjectPlacement
            )
            if placement is not None:
                parsed.position_x = Decimal(str(placement[0][3] * self._unit_scale))
                parsed.position_y = Decimal(str(placement[1][3] * self._unit_scale))
                parsed.position_z = Decimal(str(placement[2][3] * self._unit_scale))
        except Exception:
            pass

        # Extract properties
        parsed.properties = list(self._extract_properties(element))

        # Extract common property flags
        for prop in parsed.properties:
            if prop.name == "IsExternal":
                parsed.is_external = self._parse_bool(prop.value)
            elif prop.name == "LoadBearing":
                parsed.is_load_bearing = self._parse_bool(prop.value)

        # Extract quantities
        parsed.quantities = list(self._extract_quantities(element))

        # Set geometry from quantities
        for qty in parsed.quantities:
            if qty.name in ("Length", "NetLength", "GrossLength"):
                parsed.length_m = qty.value
            elif qty.name in ("Width", "NetWidth", "GrossWidth"):
                parsed.width_m = qty.value
            elif qty.name in ("Height", "NetHeight", "GrossHeight"):
                parsed.height_m = qty.value
            elif qty.name in ("NetArea", "NetSideArea", "GrossArea", "GrossSideArea"):
                if parsed.area_m2 is None:
                    parsed.area_m2 = qty.value
            elif qty.name in ("NetVolume", "GrossVolume"):
                if parsed.volume_m3 is None:
                    parsed.volume_m3 = qty.value

        # Extract materials
        parsed.materials = list(self._extract_materials(element))

        return parsed

    def _parse_spaces(self) -> Iterator[ParsedSpace]:
        """Parse IFC spaces (rooms)."""
        for space in self.ifc.by_type("IfcSpace"):
            parsed = ParsedSpace(
                global_id=space.GlobalId,
                name=space.Name,
                long_name=getattr(space, "LongName", None),
            )

            # Get spatial container (storey)
            container = ifcopenshell.util.element.get_container(space)
            if container and container.is_a("IfcBuildingStorey"):
                parsed.storey_global_id = container.GlobalId

            # Extract properties
            parsed.properties = list(self._extract_properties(space))

            # Extract specific properties
            for prop in parsed.properties:
                if prop.pset_name == "Pset_SpaceCommon":
                    if prop.name == "Reference":
                        parsed.space_number = str(prop.value)
                    elif prop.name == "OccupancyType":
                        parsed.occupancy_type = str(prop.value)
                    elif prop.name == "NetPlannedArea":
                        parsed.net_floor_area = self._to_decimal(prop.value)
                    elif prop.name == "GrossPlannedArea":
                        parsed.gross_floor_area = self._to_decimal(prop.value)

                # Look for Ex-Zone in various property sets
                if prop.name in ("ExZone", "Ex-Zone", "ExplosionZone", "ATEXZone"):
                    parsed.ex_zone = str(prop.value)

                # Fire compartment
                if prop.name in ("FireCompartment", "Brandabschnitt"):
                    parsed.fire_compartment = str(prop.value)

                # Finishes
                if prop.name == "FinishFloor":
                    parsed.finish_floor = str(prop.value)
                elif prop.name == "FinishWall":
                    parsed.finish_wall = str(prop.value)
                elif prop.name == "FinishCeiling":
                    parsed.finish_ceiling = str(prop.value)

            # Extract quantities
            for qty in self._extract_quantities(space):
                if qty.name == "NetFloorArea":
                    parsed.net_floor_area = qty.value
                elif qty.name == "GrossFloorArea":
                    parsed.gross_floor_area = qty.value
                elif qty.name == "NetVolume":
                    parsed.net_volume = qty.value
                elif qty.name == "GrossVolume":
                    parsed.gross_volume = qty.value
                elif qty.name == "FinishCeilingHeight":
                    parsed.net_height = qty.value

            # Get space boundaries
            try:
                boundaries = getattr(space, "BoundedBy", []) or []
                for boundary in boundaries:
                    if hasattr(boundary, "RelatedBuildingElement"):
                        related = boundary.RelatedBuildingElement
                        if related:
                            parsed.boundary_element_ids.append(related.GlobalId)
            except Exception:
                pass

            yield parsed

    def _extract_properties(self, element: Any) -> Iterator[ParsedProperty]:
        """Extract all properties from an element."""
        try:
            psets = ifcopenshell.util.element.get_psets(element)
            for pset_name, properties in psets.items():
                if not isinstance(properties, dict):
                    continue
                for prop_name, prop_value in properties.items():
                    if prop_name == "id":  # Skip internal ID
                        continue
                    yield ParsedProperty(
                        pset_name=pset_name,
                        name=prop_name,
                        value=prop_value,
                        data_type=self._get_data_type(prop_value),
                    )
        except Exception as e:
            logger.debug("Failed to extract properties", error=str(e))

    def _extract_quantities(self, element: Any) -> Iterator[ParsedQuantity]:
        """Extract quantities from an element."""
        try:
            # Get quantity sets
            for rel in getattr(element, "IsDefinedBy", []) or []:
                if not rel.is_a("IfcRelDefinesByProperties"):
                    continue

                prop_def = rel.RelatingPropertyDefinition
                if not prop_def.is_a("IfcElementQuantity"):
                    continue

                qto_name = prop_def.Name or "Unknown"
                for quantity in prop_def.Quantities or []:
                    qty_name = quantity.Name
                    qty_value = None
                    unit = None

                    # Get value based on quantity type
                    if quantity.is_a("IfcQuantityLength"):
                        qty_value = quantity.LengthValue * self._unit_scale
                        unit = "m"
                    elif quantity.is_a("IfcQuantityArea"):
                        qty_value = quantity.AreaValue * (self._unit_scale ** 2)
                        unit = "m\u00b2"
                    elif quantity.is_a("IfcQuantityVolume"):
                        qty_value = quantity.VolumeValue * (self._unit_scale ** 3)
                        unit = "m\u00b3"
                    elif quantity.is_a("IfcQuantityCount"):
                        qty_value = quantity.CountValue
                    elif quantity.is_a("IfcQuantityWeight"):
                        qty_value = quantity.WeightValue
                        unit = "kg"
                    elif quantity.is_a("IfcQuantityTime"):
                        qty_value = quantity.TimeValue
                        unit = "s"

                    if qty_value is not None:
                        yield ParsedQuantity(
                            qto_name=qto_name,
                            name=qty_name,
                            value=Decimal(str(qty_value)),
                            unit=unit,
                            formula=getattr(quantity, "Formula", None),
                        )
        except Exception as e:
            logger.debug("Failed to extract quantities", error=str(e))

    def _extract_materials(self, element: Any) -> Iterator[ParsedMaterial]:
        """Extract materials from an element."""
        try:
            material = ifcopenshell.util.element.get_material(element)
            if material is None:
                return

            if material.is_a("IfcMaterial"):
                yield ParsedMaterial(
                    name=material.Name,
                    category=getattr(material, "Category", None),
                )

            elif material.is_a("IfcMaterialLayerSetUsage"):
                layer_set = material.ForLayerSet
                for i, layer in enumerate(layer_set.MaterialLayers or []):
                    thickness = None
                    if layer.LayerThickness:
                        thickness = Decimal(
                            str(layer.LayerThickness * self._unit_scale)
                        )
                    yield ParsedMaterial(
                        name=layer.Material.Name if layer.Material else "Unknown",
                        thickness=thickness,
                        layer_order=i,
                        is_ventilated=getattr(layer, "IsVentilated", False) or False,
                        category=(
                            getattr(layer.Material, "Category", None)
                            if layer.Material
                            else None
                        ),
                    )

            elif material.is_a("IfcMaterialLayerSet"):
                for i, layer in enumerate(material.MaterialLayers or []):
                    thickness = None
                    if layer.LayerThickness:
                        thickness = Decimal(
                            str(layer.LayerThickness * self._unit_scale)
                        )
                    yield ParsedMaterial(
                        name=layer.Material.Name if layer.Material else "Unknown",
                        thickness=thickness,
                        layer_order=i,
                        is_ventilated=getattr(layer, "IsVentilated", False) or False,
                    )

            elif material.is_a("IfcMaterialList"):
                for i, mat in enumerate(material.Materials or []):
                    yield ParsedMaterial(
                        name=mat.Name,
                        layer_order=i,
                        category=getattr(mat, "Category", None),
                    )

            elif material.is_a("IfcMaterialConstituentSet"):
                for i, constituent in enumerate(material.MaterialConstituents or []):
                    if constituent.Material:
                        yield ParsedMaterial(
                            name=constituent.Material.Name,
                            layer_order=i,
                            category=constituent.Category,
                        )

        except Exception as e:
            logger.debug("Failed to extract materials", error=str(e))

    @staticmethod
    def _get_data_type(value: Any) -> str:
        """Determine data type of property value."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "real"
        return "string"

    @staticmethod
    def _parse_bool(value: Any) -> bool | None:
        """Parse boolean from various formats."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", ".t.")
        return None

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        """Convert value to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
