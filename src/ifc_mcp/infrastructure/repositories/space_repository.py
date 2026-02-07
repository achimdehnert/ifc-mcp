"""Space Repository Implementation.

SQLAlchemy-based implementation of ISpaceRepository.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ifc_mcp.domain import ExZone, ExZoneType, GlobalId, Space, SpaceBoundary
from ifc_mcp.infrastructure.database.models import (
    BuildingElementORM,
    SpaceBoundaryORM,
    SpaceORM,
)


class SpaceRepository:
    """SQLAlchemy implementation of space repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session."""
        self._session = session

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_by_id(self, space_id: UUID) -> Space | None:
        """Get space by ID with boundaries loaded."""
        stmt = (
            select(SpaceORM)
            .options(
                selectinload(SpaceORM.boundaries),
                selectinload(SpaceORM.storey),
            )
            .where(SpaceORM.id == space_id)
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
    ) -> Space | None:
        """Get space by IFC GlobalId."""
        stmt = (
            select(SpaceORM)
            .options(
                selectinload(SpaceORM.boundaries),
                selectinload(SpaceORM.storey),
            )
            .where(
                SpaceORM.project_id == project_id,
                SpaceORM.global_id == global_id,
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
        storey_id: UUID | None = None,
        ex_zone_only: bool = False,
        hazardous_only: bool = False,
        fire_compartment: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Space]:
        """Find spaces by criteria."""
        conditions = [SpaceORM.project_id == project_id]

        if storey_id:
            conditions.append(SpaceORM.storey_id == storey_id)
        if ex_zone_only:
            conditions.append(SpaceORM.ex_zone != "none")
        if hazardous_only:
            conditions.append(SpaceORM.hazardous_area == True)  # noqa: E712
        if fire_compartment:
            conditions.append(SpaceORM.fire_compartment == fire_compartment)

        stmt = (
            select(SpaceORM)
            .options(selectinload(SpaceORM.storey))
            .where(and_(*conditions))
            .order_by(SpaceORM.space_number, SpaceORM.name)
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        return [self._to_domain_basic(orm) for orm in result.scalars().all()]

    async def find_by_ex_zone(
        self,
        project_id: UUID,
        zone_types: list[str] | None = None,
    ) -> list[Space]:
        """Find spaces by Ex-Zone classification."""
        conditions = [
            SpaceORM.project_id == project_id,
            SpaceORM.ex_zone != "none",
        ]

        if zone_types:
            conditions.append(SpaceORM.ex_zone.in_(zone_types))

        stmt = (
            select(SpaceORM)
            .options(
                selectinload(SpaceORM.boundaries),
                selectinload(SpaceORM.storey),
            )
            .where(and_(*conditions))
            .order_by(SpaceORM.ex_zone, SpaceORM.space_number)
        )

        result = await self._session.execute(stmt)
        return [self._to_domain_full(orm) for orm in result.scalars().all()]

    async def find_by_fire_compartment(
        self,
        project_id: UUID,
        fire_compartment: str | None = None,
    ) -> list[Space]:
        """Find spaces by fire compartment."""
        conditions = [SpaceORM.project_id == project_id]

        if fire_compartment:
            conditions.append(SpaceORM.fire_compartment == fire_compartment)
        else:
            conditions.append(SpaceORM.fire_compartment.isnot(None))

        stmt = (
            select(SpaceORM)
            .options(selectinload(SpaceORM.storey))
            .where(and_(*conditions))
            .order_by(SpaceORM.fire_compartment, SpaceORM.space_number)
        )

        result = await self._session.execute(stmt)
        return [self._to_domain_basic(orm) for orm in result.scalars().all()]

    async def get_volume_summary(
        self,
        project_id: UUID,
        *,
        storey_id: UUID | None = None,
        ex_zone_only: bool = False,
    ) -> dict[str, Any]:
        """Get volume summary for spaces.

        Returns:
            Dict with total_volume, total_area, space_count, by_storey breakdown
        """
        conditions = [SpaceORM.project_id == project_id]

        if storey_id:
            conditions.append(SpaceORM.storey_id == storey_id)
        if ex_zone_only:
            conditions.append(SpaceORM.ex_zone != "none")

        stmt = select(
            func.count(SpaceORM.id).label("count"),
            func.sum(SpaceORM.net_volume).label("total_volume"),
            func.sum(SpaceORM.net_floor_area).label("total_area"),
        ).where(and_(*conditions))

        result = await self._session.execute(stmt)
        row = result.one()

        return {
            "space_count": row.count or 0,
            "total_volume_m3": float(row.total_volume) if row.total_volume else 0.0,
            "total_area_m2": float(row.total_area) if row.total_area else 0.0,
        }

    async def count_by_project(
        self,
        project_id: UUID,
        *,
        ex_zone_only: bool = False,
    ) -> int:
        """Count spaces."""
        conditions = [SpaceORM.project_id == project_id]

        if ex_zone_only:
            conditions.append(SpaceORM.ex_zone != "none")

        stmt = select(func.count(SpaceORM.id)).where(and_(*conditions))

        result = await self._session.execute(stmt)
        return result.scalar_one()

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def add(self, space: Space) -> Space:
        """Add a space."""
        orm = self._to_orm(space)
        self._session.add(orm)
        await self._session.flush()
        return space

    async def add_batch(self, spaces: list[Space]) -> int:
        """Batch add spaces."""
        if not spaces:
            return 0

        orm_objects = [self._to_orm(s) for s in spaces]
        self._session.add_all(orm_objects)
        await self._session.flush()
        return len(orm_objects)

    async def add_boundaries_batch(
        self,
        boundaries: list[dict[str, Any]],
    ) -> int:
        """Batch add space boundaries.

        Args:
            boundaries: List of boundary dicts with keys:
                - space_id
                - element_id
                - boundary_type
                - physical_or_virtual
                - internal_or_external

        Returns:
            Count of added boundaries
        """
        if not boundaries:
            return 0

        orm_objects = [
            SpaceBoundaryORM(
                id=uuid4(),
                space_id=b["space_id"],
                element_id=b["element_id"],
                boundary_type=b.get("boundary_type"),
                physical_or_virtual=b.get("physical_or_virtual"),
                internal_or_external=b.get("internal_or_external"),
            )
            for b in boundaries
        ]
        self._session.add_all(orm_objects)
        await self._session.flush()
        return len(orm_objects)

    async def update(self, space: Space) -> Space:
        """Update a space."""
        stmt = (
            select(SpaceORM)
            .where(SpaceORM.id == space.id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = space.name
            orm.long_name = space.long_name
            orm.space_number = space.space_number
            orm.ex_zone = space.ex_zone.zone_type.value
            orm.hazardous_area = space.hazardous_area
            orm.fire_compartment = space.fire_compartment
            orm.finish_floor = space.finish_floor
            orm.finish_wall = space.finish_wall
            orm.finish_ceiling = space.finish_ceiling
            await self._session.flush()

        return space

    # =========================================================================
    # Mapping
    # =========================================================================

    def _to_domain_basic(self, orm: SpaceORM) -> Space:
        """Map ORM to domain model (basic fields only)."""
        space = Space(
            id=orm.id,
            project_id=orm.project_id,
            element_id=orm.element_id,
            global_id=GlobalId(orm.global_id),
            name=orm.name,
            long_name=orm.long_name,
            space_number=orm.space_number,
            storey_id=orm.storey_id,
            net_floor_area=orm.net_floor_area,
            gross_floor_area=orm.gross_floor_area,
            net_volume=orm.net_volume,
            gross_volume=orm.gross_volume,
            net_height=orm.net_height,
            occupancy_type=orm.occupancy_type,
            hazardous_area=orm.hazardous_area,
            fire_compartment=orm.fire_compartment,
            finish_floor=orm.finish_floor,
            finish_wall=orm.finish_wall,
            finish_ceiling=orm.finish_ceiling,
            created_at=orm.created_at,
        )

        # Parse ex_zone
        space.set_ex_zone(orm.ex_zone)

        # Add storey name if loaded
        if orm.storey:
            space.storey_name = orm.storey.name

        return space

    def _to_domain_full(self, orm: SpaceORM) -> Space:
        """Map ORM to domain model with boundaries."""
        space = self._to_domain_basic(orm)

        # Map boundaries
        if orm.boundaries:
            for boundary in orm.boundaries:
                space.add_boundary(
                    element_id=boundary.element_id,
                    boundary_type=boundary.boundary_type,
                    physical_or_virtual=boundary.physical_or_virtual,
                    internal_or_external=boundary.internal_or_external,
                )

        return space

    def _to_orm(self, space: Space) -> SpaceORM:
        """Map domain model to ORM."""
        return SpaceORM(
            id=space.id,
            project_id=space.project_id,
            storey_id=space.storey_id,
            element_id=space.element_id,
            global_id=str(space.global_id),
            name=space.name,
            long_name=space.long_name,
            space_number=space.space_number,
            net_floor_area=space.net_floor_area,
            gross_floor_area=space.gross_floor_area,
            net_volume=space.net_volume,
            gross_volume=space.gross_volume,
            net_height=space.net_height,
            occupancy_type=space.occupancy_type,
            ex_zone=space.ex_zone.zone_type.value,
            hazardous_area=space.hazardous_area,
            fire_compartment=space.fire_compartment,
            finish_floor=space.finish_floor,
            finish_wall=space.finish_wall,
            finish_ceiling=space.finish_ceiling,
        )
