"""Storey Repository Implementation.

SQLAlchemy-based implementation of IStoreyRepository.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ifc_mcp.domain import Storey
from ifc_mcp.infrastructure.database.models import StoreyORM


class StoreyRepository:
    """SQLAlchemy implementation of storey repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session."""
        self._session = session

    async def get_by_id(self, storey_id: UUID) -> Storey | None:
        """Get storey by ID."""
        stmt = select(StoreyORM).where(StoreyORM.id == storey_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain(orm)

    async def get_by_project(self, project_id: UUID) -> list[Storey]:
        """Get all storeys for a project, ordered by elevation."""
        stmt = (
            select(StoreyORM)
            .where(StoreyORM.project_id == project_id)
            .order_by(StoreyORM.elevation.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_global_id(
        self,
        project_id: UUID,
        global_id: str,
    ) -> Storey | None:
        """Get storey by IFC GlobalId."""
        stmt = select(StoreyORM).where(
            StoreyORM.project_id == project_id,
            StoreyORM.global_id == global_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain(orm)

    async def add(self, storey: Storey) -> Storey:
        """Add a storey."""
        orm = self._to_orm(storey)
        self._session.add(orm)
        await self._session.flush()
        return storey

    async def add_batch(self, storeys: list[Storey]) -> int:
        """Batch add storeys.

        Args:
            storeys: List of storeys to add

        Returns:
            Count of added storeys
        """
        if not storeys:
            return 0

        orm_objects = [self._to_orm(s) for s in storeys]
        self._session.add_all(orm_objects)
        await self._session.flush()
        return len(orm_objects)

    def _to_domain(self, orm: StoreyORM) -> Storey:
        """Map ORM to domain model."""
        return Storey(
            id=orm.id,
            project_id=orm.project_id,
            global_id=orm.global_id,
            name=orm.name,
            long_name=orm.long_name,
            elevation=float(orm.elevation) if orm.elevation else None,
            created_at=orm.created_at,
        )

    def _to_orm(self, storey: Storey) -> StoreyORM:
        """Map domain model to ORM."""
        return StoreyORM(
            id=storey.id,
            project_id=storey.project_id,
            global_id=storey.global_id,
            name=storey.name,
            long_name=storey.long_name,
            elevation=Decimal(str(storey.elevation)) if storey.elevation else None,
        )
