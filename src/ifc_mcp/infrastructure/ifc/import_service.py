"""IFC Import Service.

Orchestrates IFC file import: parsing, mapping, and persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from ifc_mcp.domain import (
    BuildingElement,
    ElementCategory,
    EntityAlreadyExistsError,
    GlobalId,
    IfcSchemaVersion,
    Project,
    Space,
    Storey,
)
from ifc_mcp.infrastructure.database.models import (
    MaterialORM,
    PropertySetDefinitionORM,
)
from ifc_mcp.infrastructure.ifc.parser import (
    IfcParser,
    ParsedElement,
    ParsedProject,
    ParsedSpace,
    ParsedStorey,
    ParsedType,
)
from ifc_mcp.infrastructure.repositories import UnitOfWork
from ifc_mcp.shared.config import settings
from ifc_mcp.shared.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ImportResult:
    """Result of IFC import operation."""
    project_id: UUID
    project_name: str
    element_count: int
    space_count: int
    storey_count: int
    type_count: int
    material_count: int
    property_count: int
    quantity_count: int
    warnings: list[str]


class IfcImportService:
    """Service for importing IFC files into the database."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize import service."""
        self._uow = uow
        self._batch_size = settings.ifc_import_batch_size

        self._storey_map: dict[str, UUID] = {}
        self._type_map: dict[str, UUID] = {}
        self._element_map: dict[str, UUID] = {}
        self._material_map: dict[str, UUID] = {}
        self._pset_map: dict[str, UUID] = {}

    async def import_file(
        self,
        file_path: str | Path,
        *,
        skip_if_exists: bool = True,
    ) -> ImportResult:
        """Import IFC file into database."""
        logger.info("Starting IFC import", file_path=str(file_path))

        parser = IfcParser(file_path)
        parsed = parser.parse()

        if skip_if_exists and parsed.file_hash:
            existing = await self._uow.projects.get_by_file_hash(parsed.file_hash)
            if existing:
                raise EntityAlreadyExistsError(
                    "Project", parsed.file_hash,
                    {"existing_project_id": str(existing.id)},
                )

        project = self._create_project(parsed)
        await self._uow.projects.add(project)
        logger.info("Created project", project_id=str(project.id), name=project.name)

        storey_count = await self._import_storeys(project.id, parsed.storeys)
        logger.info("Imported storeys", count=storey_count)

        type_count = await self._import_types(project.id, parsed.types)
        logger.info("Imported types", count=type_count)

        material_count = await self._import_materials(project.id, parsed.materials)
        logger.info("Imported materials", count=material_count)

        await self._create_pset_definitions(project.id, parsed)

        element_count, property_count, quantity_count = await self._import_elements(
            project.id, parsed.elements
        )
        logger.info(
            "Imported elements",
            count=element_count, properties=property_count,
            quantities=quantity_count,
        )

        space_count = await self._import_spaces(project.id, parsed.spaces)
        logger.info("Imported spaces", count=space_count)

        await self._uow.commit()

        logger.info(
            "IFC import complete",
            project_id=str(project.id),
            elements=element_count, spaces=space_count,
        )

        return ImportResult(
            project_id=project.id,
            project_name=project.name,
            element_count=element_count,
            space_count=space_count,
            storey_count=storey_count,
            type_count=type_count,
            material_count=material_count,
            property_count=property_count,
            quantity_count=quantity_count,
            warnings=[],
        )

    def _create_project(self, parsed: ParsedProject) -> Project:
        """Create Project domain entity from parsed data."""
        return Project.create(
            name=parsed.name,
            schema_version=parsed.schema_version,
            description=parsed.description,
            original_file_path=parsed.file_path,
            original_file_hash=parsed.file_hash,
            authoring_app=parsed.authoring_app,
            author=parsed.author,
            organization=parsed.organization,
        )

    async def _import_storeys(
        self, project_id: UUID, storeys: list[ParsedStorey],
    ) -> int:
        """Import storeys and build lookup map."""
        domain_storeys = []

        for parsed in storeys:
            storey = Storey.create(
                project_id=project_id,
                global_id=parsed.global_id,
                name=parsed.name,
                long_name=parsed.long_name,
                elevation=parsed.elevation,
            )
            domain_storeys.append(storey)
            self._storey_map[parsed.global_id] = storey.id

        return await self._uow.storeys.add_batch(domain_storeys)

    async def _import_types(
        self, project_id: UUID, types: list[ParsedType],
    ) -> int:
        """Import element types and build lookup map."""
        from ifc_mcp.infrastructure.database.models import ElementTypeORM

        type_orms = []
        for parsed in types:
            type_id = uuid4()
            self._type_map[parsed.global_id] = type_id

            type_orms.append(
                ElementTypeORM(
                    id=type_id,
                    project_id=project_id,
                    global_id=parsed.global_id,
                    ifc_class=parsed.ifc_class,
                    name=parsed.name,
                    description=parsed.description,
                )
            )

        if type_orms:
            self._uow.session.add_all(type_orms)
            await self._uow.flush()

        return len(type_orms)

    async def _import_materials(
        self, project_id: UUID, material_names: set[str],
    ) -> int:
        """Import materials and build lookup map."""
        material_orms = []

        for name in material_names:
            mat_id = uuid4()
            self._material_map[name] = mat_id

            material_orms.append(
                MaterialORM(
                    id=mat_id,
                    project_id=project_id,
                    name=name,
                )
            )

        if material_orms:
            self._uow.session.add_all(material_orms)
            await self._uow.flush()

        return len(material_orms)

    async def _create_pset_definitions(
        self, project_id: UUID, parsed: ParsedProject,
    ) -> None:
        """Create property set definitions from all elements."""
        pset_names: set[str] = set()

        for element in parsed.elements:
            for prop in element.properties:
                pset_names.add(prop.pset_name)

        for space in parsed.spaces:
            for prop in space.properties:
                pset_names.add(prop.pset_name)

        for element_type in parsed.types:
            for prop in element_type.properties:
                pset_names.add(prop.pset_name)

        pset_orms = []
        for name in pset_names:
            pset_id = uuid4()
            self._pset_map[name] = pset_id

            pset_orms.append(
                PropertySetDefinitionORM(
                    id=pset_id,
                    project_id=project_id,
                    name=name,
                )
            )

        if pset_orms:
            self._uow.session.add_all(pset_orms)
            await self._uow.flush()

    async def _import_elements(
        self, project_id: UUID, elements: list[ParsedElement],
    ) -> tuple[int, int, int]:
        """Import elements in batches."""
        total_elements = 0
        total_properties = 0
        total_quantities = 0

        for i in range(0, len(elements), self._batch_size):
            batch = elements[i : i + self._batch_size]

            domain_elements = []
            properties_batch: list[dict[str, Any]] = []
            quantities_batch: list[dict[str, Any]] = []
            materials_batch: list[dict[str, Any]] = []

            for parsed in batch:
                element = self._map_element(project_id, parsed)
                domain_elements.append(element)
                self._element_map[parsed.global_id] = element.id

                for prop in parsed.properties:
                    pset_id = self._pset_map.get(prop.pset_name)
                    if pset_id:
                        properties_batch.append({
                            "element_id": element.id,
                            "pset_definition_id": pset_id,
                            "property_name": prop.name,
                            "property_value": str(prop.value) if prop.value is not None else None,
                            "data_type": prop.data_type,
                            "unit": prop.unit,
                        })

                for qty in parsed.quantities:
                    quantities_batch.append({
                        "element_id": element.id,
                        "qto_name": qty.qto_name,
                        "quantity_name": qty.name,
                        "quantity_value": qty.value,
                        "unit": qty.unit,
                        "formula": qty.formula,
                    })

                for mat in parsed.materials:
                    mat_id = self._material_map.get(mat.name)
                    if mat_id:
                        materials_batch.append({
                            "element_id": element.id,
                            "material_id": mat_id,
                            "layer_order": mat.layer_order,
                            "layer_thickness": mat.thickness,
                            "is_ventilated": mat.is_ventilated,
                        })

            count = await self._uow.elements.add_batch(domain_elements)
            total_elements += count

            prop_count = await self._uow.elements.add_properties_batch(properties_batch)
            total_properties += prop_count

            qty_count = await self._uow.elements.add_quantities_batch(quantities_batch)
            total_quantities += qty_count

            if materials_batch:
                from ifc_mcp.infrastructure.database.models import ElementMaterialORM

                mat_orms = [
                    ElementMaterialORM(
                        id=uuid4(),
                        element_id=m["element_id"],
                        material_id=m["material_id"],
                        layer_order=m["layer_order"],
                        layer_thickness=m["layer_thickness"],
                        is_ventilated=m["is_ventilated"],
                    )
                    for m in materials_batch
                ]
                self._uow.session.add_all(mat_orms)

            await self._uow.flush()
            logger.debug(
                "Processed element batch",
                batch_num=i // self._batch_size + 1,
                elements=count,
            )

        return total_elements, total_properties, total_quantities

    def _map_element(self, project_id: UUID, parsed: ParsedElement) -> BuildingElement:
        """Map parsed element to domain entity."""
        storey_id = None
        if parsed.storey_global_id:
            storey_id = self._storey_map.get(parsed.storey_global_id)

        type_id = None
        if parsed.type_global_id:
            type_id = self._type_map.get(parsed.type_global_id)

        element = BuildingElement.create(
            project_id=project_id,
            global_id=parsed.global_id,
            ifc_class=parsed.ifc_class,
            name=parsed.name,
            description=parsed.description,
            tag=parsed.tag,
            storey_id=storey_id,
            type_id=type_id,
        )

        element.object_type = parsed.object_type
        element.length_m = parsed.length_m
        element.width_m = parsed.width_m
        element.height_m = parsed.height_m
        element.area_m2 = parsed.area_m2
        element.volume_m3 = parsed.volume_m3
        element.position_x = parsed.position_x
        element.position_y = parsed.position_y
        element.position_z = parsed.position_z
        element.is_external = parsed.is_external
        element.is_load_bearing = parsed.is_load_bearing

        return element

    async def _import_spaces(
        self, project_id: UUID, spaces: list[ParsedSpace],
    ) -> int:
        """Import spaces."""
        space_elements: list[BuildingElement] = []
        domain_spaces: list[Space] = []
        boundaries_batch: list[dict[str, Any]] = []

        for parsed in spaces:
            storey_id = None
            if parsed.storey_global_id:
                storey_id = self._storey_map.get(parsed.storey_global_id)

            element = BuildingElement.create(
                project_id=project_id,
                global_id=parsed.global_id,
                ifc_class="IfcSpace",
                name=parsed.name,
                storey_id=storey_id,
            )
            element.volume_m3 = parsed.net_volume or parsed.gross_volume
            element.area_m2 = parsed.net_floor_area or parsed.gross_floor_area

            space_elements.append(element)
            self._element_map[parsed.global_id] = element.id

            space = Space.create(
                project_id=project_id,
                element_id=element.id,
                global_id=parsed.global_id,
                name=parsed.name,
                long_name=parsed.long_name,
                space_number=parsed.space_number,
                storey_id=storey_id,
            )

            space.net_floor_area = parsed.net_floor_area
            space.gross_floor_area = parsed.gross_floor_area
            space.net_volume = parsed.net_volume
            space.gross_volume = parsed.gross_volume
            space.net_height = parsed.net_height

            space.occupancy_type = parsed.occupancy_type
            space.set_ex_zone(parsed.ex_zone)
            space.fire_compartment = parsed.fire_compartment
            space.finish_floor = parsed.finish_floor
            space.finish_wall = parsed.finish_wall
            space.finish_ceiling = parsed.finish_ceiling

            domain_spaces.append(space)

            for boundary_gid in parsed.boundary_element_ids:
                boundary_element_id = self._element_map.get(boundary_gid)
                if boundary_element_id:
                    boundaries_batch.append({
                        "space_id": space.id,
                        "element_id": boundary_element_id,
                    })

        await self._uow.elements.add_batch(space_elements)
        count = await self._uow.spaces.add_batch(domain_spaces)
        await self._uow.spaces.add_boundaries_batch(boundaries_batch)

        return count


async def import_ifc_file(
    file_path: str | Path,
    *,
    skip_if_exists: bool = True,
) -> ImportResult:
    """Convenience function to import IFC file."""
    async with UnitOfWork() as uow:
        service = IfcImportService(uow)
        return await service.import_file(file_path, skip_if_exists=skip_if_exists)
