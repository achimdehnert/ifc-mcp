"""Project Repository Implementation.

SQLAlchemy-based implementation of IProjectRepository.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ifc_mcp.domain import (
    EntityNotFoundError,
    IfcSchemaVersion,
    Project,
    Storey,
)
from ifc_mcp.infrastructure.database.models import ProjectORM, StoreyORM


class ProjectRepository:
    """SQLAlchemy implementation of project repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session.

        Args:
            session: AsyncSession instance
        """
        self._session = session

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_by_id(self, project_id: UUID) -> Project | None:
        """Get project by ID with storeys loaded.

        Args:
            project_id: Project UUID

        Returns:
            Project or None
        """
        stmt = (
            select(ProjectORM)
            .options(selectinload(ProjectORM.storeys))
            .where(ProjectORM.id == project_id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain(orm)

    async def get_by_file_hash(self, file_hash: str) -> Project | None:
        """Get project by file hash for deduplication.

        Args:
            file_hash: SHA-256 hash

        Returns:
            Project or None
        """
        stmt = (
            select(ProjectORM)
            .where(
                and_(
                    ProjectORM.original_file_hash == file_hash,
                    ProjectORM.deleted_at.is_(None),
                )
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain(orm)

    async def list_all(
        self,
        *,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """List all projects.

        Args:
            include_deleted: Include soft-deleted projects
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of projects
        """
        stmt = select(ProjectORM).options(selectinload(ProjectORM.storeys))

        if not include_deleted:
            stmt = stmt.where(ProjectORM.deleted_at.is_(None))

        stmt = stmt.order_by(ProjectORM.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count(self, *, include_deleted: bool = False) -> int:
        """Count projects.

        Args:
            include_deleted: Include soft-deleted

        Returns:
            Total count
        """
        stmt = select(func.count(ProjectORM.id))

        if not include_deleted:
            stmt = stmt.where(ProjectORM.deleted_at.is_(None))

        result = await self._session.execute(stmt)
        return result.scalar_one()

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def add(self, project: Project) -> Project:
        """Add a new project.

        Args:
            project: Project to add

        Returns:
            Added project
        """
        orm = self._to_orm(project)
        self._session.add(orm)
        await self._session.flush()

        # Add storeys if present
        for storey in project.storeys:
            storey_orm = StoreyORM(
                id=storey.id,
                project_id=project.id,
                global_id=storey.global_id,
                name=storey.name,
                long_name=storey.long_name,
                elevation=storey.elevation,
            )
            self._session.add(storey_orm)

        await self._session.flush()
        return project

    async def update(self, project: Project) -> Project:
        """Update existing project.

        Args:
            project: Project to update

        Returns:
            Updated project
        """
        stmt = (
            update(ProjectORM)
            .where(ProjectORM.id == project.id)
            .values(
                name=project.name,
                description=project.description,
                updated_at=datetime.utcnow(),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return project

    async def delete(self, project_id: UUID, *, hard: bool = False) -> bool:
        """Delete a project.

        Args:
            project_id: Project UUID
            hard: Permanently delete if True

        Returns:
            True if deleted
        """
        if hard:
            stmt = delete(ProjectORM).where(ProjectORM.id == project_id)
        else:
            stmt = (
                update(ProjectORM)
                .where(ProjectORM.id == project_id)
                .values(deleted_at=datetime.utcnow())
            )

        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    # =========================================================================
    # Mapping
    # =========================================================================

    def _to_domain(self, orm: ProjectORM) -> Project:
        """Map ORM to domain model.

        Args:
            orm: ProjectORM instance

        Returns:
            Project domain model
        """
        project = Project(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            schema_version=IfcSchemaVersion.from_string(orm.schema_version),
            original_file_path=orm.original_file_path,
            original_file_hash=orm.original_file_hash,
            authoring_app=orm.authoring_app,
            author=orm.author,
            organization=orm.organization,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            imported_at=orm.imported_at,
            deleted_at=orm.deleted_at,
        )

        # Map storeys if loaded
        if orm.storeys:
            project.storeys = [
                Storey(
                    id=s.id,
                    project_id=s.project_id,
                    global_id=s.global_id,
                    name=s.name,
                    long_name=s.long_name,
                    elevation=float(s.elevation) if s.elevation else None,
                    created_at=s.created_at,
                )
                for s in sorted(orm.storeys, key=lambda x: x.elevation or 0)
            ]

        return project

    def _to_orm(self, project: Project) -> ProjectORM:
        """Map domain model to ORM.

        Args:
            project: Project domain model

        Returns:
            ProjectORM instance
        """
        return ProjectORM(
            id=project.id,
            name=project.name,
            description=project.description,
            schema_version=project.schema_version.value,
            original_file_path=project.original_file_path,
            original_file_hash=project.original_file_hash,
            authoring_app=project.authoring_app,
            author=project.author,
            organization=project.organization,
            created_at=project.created_at,
            updated_at=project.updated_at,
            imported_at=project.imported_at,
            deleted_at=project.deleted_at,
        )
