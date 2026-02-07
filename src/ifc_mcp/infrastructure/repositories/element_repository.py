"""Element Repository Implementation.

SQLAlchemy-based implementation of IElementRepository.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ifc_mcp.domain import (
    BuildingElement,
    ElementCategory,
    GlobalId,
    MaterialLayer,
    PropertyValue,
    QuantityValue,
)
from ifc_mcp.infrastructure.database.models import (
    BuildingElementORM,
    ElementMaterialORM,
    ElementPropertyORM,
    ElementQuantityORM,
    MaterialORM,
    PropertySetDefinitionORM,
)


class ElementRepository:
    """SQLAlchemy implementation of element repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session."""
        self._session = session

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_by_id(self, element_id: UUID) -> BuildingElement | None:
        """Get element by ID with properties loaded."""
        stmt = (
            select(BuildingElementORM)
            .options(
                selectinload(BuildingElementORM.properties).selectinload(
                    ElementPropertyORM.pset_definition
                ),
                selectinload(BuildingElementORM.quantities),
                selectinload(BuildingElementORM.materials).selectinload(
                    ElementMaterialORM.material
                ),
                selectinload(BuildingElementORM.storey),
                selectinload(BuildingElementORM.element_type),
            )
            .where(BuildingElementORM.id == element_id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain_full(orm)

    async def get_by_global_id(
        self,
        project_id: UUID,
        global_id: str,
    ) -> BuildingElement | None:
        """Get element by IFC GlobalId."""
        stmt = (
            select(BuildingElementORM)
            .options(
                selectinload(BuildingElementORM.properties).selectinload(
                    ElementPropertyORM.pset_definition
                ),
                selectinload(BuildingElementORM.quantities),
                selectinload(BuildingElementORM.materials).selectinload(
                    ElementMaterialORM.material
                ),
            )
            .where(
                BuildingElementORM.project_id == project_id,
                BuildingElementORM.global_id == global_id,
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain_full(orm)

    async def find_by_project(
        self,
        project_id: UUID,
        *,
        ifc_class: str | None = None,
        category: ElementCategory | None = None,
        storey_id: UUID | None = None,
        is_external: bool | None = None,
        is_load_bearing: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BuildingElement]:
        """Find elements by criteria."""
        conditions = [BuildingElementORM.project_id == project_id]

        if ifc_class:
            conditions.append(BuildingElementORM.ifc_class == ifc_class)
        if category:
            conditions.append(BuildingElementORM.category == category.value)
        if storey_id:
            conditions.append(BuildingElementORM.storey_id == storey_id)
        if is_external is not None:
            conditions.append(BuildingElementORM.is_external == is_external)
        if is_load_bearing is not None:
            conditions.append(BuildingElementORM.is_load_bearing == is_load_bearing)

        stmt = (
            select(BuildingElementORM)
            .options(
                selectinload(BuildingElementORM.storey),
                selectinload(BuildingElementORM.element_type),
            )
            .where(and_(*conditions))
            .order_by(BuildingElementORM.name)
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        return [self._to_domain_basic(orm) for orm in result.scalars().all()]

    async def find_by_property(
        self,
        project_id: UUID,
        pset_name: str,
        property_name: str,
        property_value: str,
    ) -> list[BuildingElement]:
        """Find elements by property value."""
        stmt = (
            select(BuildingElementORM)
            .join(BuildingElementORM.properties)
            .join(ElementPropertyORM.pset_definition)
            .where(
                BuildingElementORM.project_id == project_id,
                PropertySetDefinitionORM.name == pset_name,
                ElementPropertyORM.property_name == property_name,
                ElementPropertyORM.property_value == property_value,
            )
            .options(
                selectinload(BuildingElementORM.storey),
                selectinload(BuildingElementORM.element_type),
            )
        )

        result = await self._session.execute(stmt)
        return [self._to_domain_basic(orm) for orm in result.scalars().all()]

    async def find_by_material(
        self,
        project_id: UUID,
        material_keyword: str,
    ) -> list[BuildingElement]:
        """Find elements by material keyword (case-insensitive)."""
        keyword_pattern = f"%{material_keyword.lower()}%"

        stmt = (
            select(BuildingElementORM)
            .join(BuildingElementORM.materials)
            .join(ElementMaterialORM.material)
            .where(
                BuildingElementORM.project_id == project_id,
                func.lower(MaterialORM.name).like(keyword_pattern),
            )
            .options(
                selectinload(BuildingElementORM.storey),
                selectinload(BuildingElementORM.element_type),
                selectinload(BuildingElementORM.materials).selectinload(
                    ElementMaterialORM.material
                ),
            )
            .distinct()
        )

        result = await self._session.execute(stmt)
        return [self._to_domain_basic(orm) for orm in result.scalars().all()]

    async def find_with_fire_rating(
        self,
        project_id: UUID,
        min_minutes: int | None = None,
    ) -> list[BuildingElement]:
        """Find elements with fire rating property."""
        stmt = (
            select(BuildingElementORM)
            .join(BuildingElementORM.properties)
            .join(ElementPropertyORM.pset_definition)
            .where(
                BuildingElementORM.project_id == project_id,
                ElementPropertyORM.property_name == "FireRating",
                ElementPropertyORM.property_value.isnot(None),
            )
            .options(
                selectinload(BuildingElementORM.properties).selectinload(
                    ElementPropertyORM.pset_definition
                ),
                selectinload(BuildingElementORM.storey),
            )
            .distinct()
        )

        result = await self._session.execute(stmt)
        elements = [self._to_domain_full(orm) for orm in result.scalars().all()]

        # Filter by minimum fire rating if specified
        if min_minutes is not None:
            elements = [
                e for e in elements
                if e.fire_rating and e.fire_rating.minutes >= min_minutes
            ]

        return elements

    async def count_by_project(
        self,
        project_id: UUID,
        *,
        ifc_class: str | None = None,
        category: ElementCategory | None = None,
    ) -> int:
        """Count elements by criteria."""
        conditions = [BuildingElementORM.project_id == project_id]

        if ifc_class:
            conditions.append(BuildingElementORM.ifc_class == ifc_class)
        if category:
            conditions.append(BuildingElementORM.category == category.value)

        stmt = select(func.count(BuildingElementORM.id)).where(and_(*conditions))

        result = await self._session.execute(stmt)
        return result.scalar_one()

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def add(self, element: BuildingElement) -> BuildingElement:
        """Add an element."""
        orm = self._to_orm(element)
        self._session.add(orm)
        await self._session.flush()
        return element

    async def add_batch(self, elements: list[BuildingElement]) -> int:
        """Batch add elements for import performance.

        Args:
            elements: Elements to add

        Returns:
            Count of added elements
        """
        if not elements:
            return 0

        orm_objects = [self._to_orm(e) for e in elements]
        self._session.add_all(orm_objects)
        await self._session.flush()
        return len(orm_objects)

    async def add_properties_batch(
        self,
        properties: list[dict[str, Any]],
    ) -> int:
        """Batch add properties.

        Args:
            properties: List of property dicts with keys:
                - element_id
                - pset_definition_id
                - property_name
                - property_value
                - data_type
                - unit

        Returns:
            Count of added properties
        """
        if not properties:
            return 0

        orm_objects = [
            ElementPropertyORM(
                id=uuid4(),
                element_id=p["element_id"],
                pset_definition_id=p["pset_definition_id"],
                property_name=p["property_name"],
                property_value=p.get("property_value"),
                data_type=p.get("data_type", "string"),
                unit=p.get("unit"),
            )
            for p in properties
        ]
        self._session.add_all(orm_objects)
        await self._session.flush()
        return len(orm_objects)

    async def add_quantities_batch(
        self,
        quantities: list[dict[str, Any]],
    ) -> int:
        """Batch add quantities.

        Args:
            quantities: List of quantity dicts

        Returns:
            Count of added quantities
        """
        if not quantities:
            return 0

        orm_objects = [
            ElementQuantityORM(
                id=uuid4(),
                element_id=q["element_id"],
                qto_name=q["qto_name"],
                quantity_name=q["quantity_name"],
                quantity_value=q.get("quantity_value"),
                unit=q.get("unit"),
                formula=q.get("formula"),
            )
            for q in quantities
        ]
        self._session.add_all(orm_objects)
        await self._session.flush()
        return len(orm_objects)

    async def update(self, element: BuildingElement) -> BuildingElement:
        """Update an element."""
        stmt = (
            update(BuildingElementORM)
            .where(BuildingElementORM.id == element.id)
            .values(
                name=element.name,
                description=element.description,
                is_external=element.is_external,
                is_load_bearing=element.is_load_bearing,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return element

    async def delete(self, element_id: UUID) -> bool:
        """Delete an element."""
        stmt = delete(BuildingElementORM).where(BuildingElementORM.id == element_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    # =========================================================================
    # Mapping
    # =========================================================================

    def _to_domain_basic(self, orm: BuildingElementORM) -> BuildingElement:
        """Map ORM to domain model (basic fields only)."""
        element = BuildingElement(
            id=orm.id,
            project_id=orm.project_id,
            global_id=GlobalId(orm.global_id),
            ifc_class=orm.ifc_class,
            category=ElementCategory(orm.category),
            name=orm.name,
            description=orm.description,
            object_type=orm.object_type,
            tag=orm.tag,
            length_m=orm.length_m,
            width_m=orm.width_m,
            height_m=orm.height_m,
            area_m2=orm.area_m2,
            volume_m3=orm.volume_m3,
            position_x=orm.position_x,
            position_y=orm.position_y,
            position_z=orm.position_z,
            storey_id=orm.storey_id,
            type_id=orm.type_id,
            is_external=orm.is_external,
            is_load_bearing=orm.is_load_bearing,
            created_at=orm.created_at,
        )

        # Add storey/type names if loaded
        if orm.storey:
            element.storey_name = orm.storey.name
        if orm.element_type:
            element.type_name = orm.element_type.name

        return element

    def _to_domain_full(self, orm: BuildingElementORM) -> BuildingElement:
        """Map ORM to domain model with all relations."""
        element = self._to_domain_basic(orm)

        # Map properties
        if orm.properties:
            for prop in orm.properties:
                pset_name = prop.pset_definition.name if prop.pset_definition else "Unknown"
                element.set_property(
                    pset_name=pset_name,
                    property_name=prop.property_name,
                    value=prop.property_value,
                    data_type=prop.data_type,
                    unit=prop.unit,
                )

        # Map quantities
        if orm.quantities:
            for qty in orm.quantities:
                if qty.quantity_value is not None:
                    element.set_quantity(
                        qto_name=qty.qto_name,
                        quantity_name=qty.quantity_name,
                        value=qty.quantity_value,
                        unit=qty.unit,
                        formula=qty.formula,
                    )

        # Map materials
        if orm.materials:
            for em in sorted(orm.materials, key=lambda x: x.layer_order or 0):
                element.add_material(
                    material_name=em.material.name,
                    thickness=em.layer_thickness,
                    layer_order=em.layer_order or 0,
                    is_ventilated=em.is_ventilated,
                    category=em.material.category,
                )

        return element

    def _to_orm(self, element: BuildingElement) -> BuildingElementORM:
        """Map domain model to ORM."""
        return BuildingElementORM(
            id=element.id,
            project_id=element.project_id,
            storey_id=element.storey_id,
            type_id=element.type_id,
            global_id=str(element.global_id),
            ifc_class=element.ifc_class,
            category=element.category.value,
            name=element.name,
            description=element.description,
            object_type=element.object_type,
            tag=element.tag,
            length_m=element.length_m,
            width_m=element.width_m,
            height_m=element.height_m,
            area_m2=element.area_m2,
            volume_m3=element.volume_m3,
            position_x=element.position_x,
            position_y=element.position_y,
            position_z=element.position_z,
            is_external=element.is_external,
            is_load_bearing=element.is_load_bearing,
        )
